# 模拟器环境搭建参考（iApp）

> **读法**：这是参考，不是强制规范。用户问“模拟器怎么配 / Windows 工作区怎么同步进 iApp / 多开怎么弄”时，按这里的原则映射到用户自己的模拟器；雷电 9/14 是常见环境，路径按其默认值写，装在别处按实际替换。工程根以 iApp 设置里显示的“存储路径 / 工程路径”为准；下面是雷电 9 的实测参考。

示例值：

| 占位 | 示例 |
|---|---|
| 宿主工作区 | `D:\iAppWorkspace\sync` |
| 设备共享存储 | `/sdcard/Pictures`（= `/storage/emulated/0/Pictures`） |
| iApp 包名 | `com.iapp.app` |
| 工程 ID | `<项目ID>`（如 `com.demo.xxx`） |
| 模拟器安装目录 | `C:\LDPlayer\LDPlayer9`（雷电默认；装在别处按实际） |
| adb 序列号 | `<serial>`（如 `127.0.0.1:5557`） |
| VM UUID | `<VM-UUID>` |

## 0. 一句话模型

宿主工作区目录 ↔ 模拟器共享目录 ↔ 设备 `Pictures`；iApp 工程是 `Pictures/ProjectApp/<项目ID>` 的子目录。

- 安卓 9（雷电 9 实测，仅供参考）：常见工程根是 `/data/media/0/iApp/ProjectApp`（日常视图 `/sdcard/iApp/ProjectApp`），可以直接改到 `/sdcard/Pictures/ProjectApp`。不同模拟器/真机的路径可能不同，以 iApp 设置里显示的路径为准。
- 安卓 14：工程根固定在 iApp 自己的 `Android/data` 里，改不出去，只能在那里建软链转到 Pictures（**需要 ROOT**，见 §4）。

## 1. 目标形态

```
Windows 工作区                        模拟器共享目录                 设备
D:\iAppWorkspace\sync          <──────────────────────>        /sdcard/Pictures
D:\iAppWorkspace\sync\ProjectApp        ≡                       /sdcard/Pictures/ProjectApp
                                                                  └─ <项目ID>/src/mian.iyu
```

安卓 14 额外一层软链：

```
/storage/emulated/0/Android/data/com.iapp.app/files/iApp/ProjectApp
  -> /storage/emulated/0/Pictures/ProjectApp
```

注意：同步的是目录本身——宿主 `sync` ↔ 设备 `Pictures`，`ProjectApp` 只是两边各自的子目录。

## 2. 共用原则

1. **宿主工作区是唯一源**；模拟器共享目录是双向映射（vboxsf 通常 `ttl=0`，实时）。
2. **iApp 以内存为准**：外部改文件前先关工程（或 `am force-stop`），改完重开工程；共享目录里直接编辑也遵守这条，避免旧内存覆盖磁盘。
3. **软链/挂载只能建在设备侧 ext4/FUSE 路径**；共享目录（vboxsf）不支持 `ln -s`，会报 `Function not implemented`。
4. **不要用 `mount --bind`** 把 Pictures 挂到 Android/data：应用有独立 mount namespace，init 命名空间里的挂载对 app 不可见（实测）。
5. **多设备一律 `adb -s <serial>`**；投递前 `getprop ro.build.version.sdk` 核对，别信 `emulator-5554` 这个名字。
6. 权限：安卓 9 用 `READ/WRITE_EXTERNAL_STORAGE` 运行时权限；安卓 11+ 广域文件用 `MANAGE_EXTERNAL_STORAGE`（appop）；`READ/WRITE_EXTERNAL_STORAGE` 在 13+ 不再给广域访问，媒体用 `READ_MEDIA_*`；app 私有目录不需要这些权限。
7. 安卓 14 的 `Android/data/<包名>` 只有该 app 自己的 mount namespace 能访问；普通 `adb shell` 会被 FUSE 拒绝，建链接必须 `su`。

## 3. 安卓 9 环境（API 28，sdcardfs）

适用：雷电 9 / Android 9；其它 Android 9~10 模拟器可参考同样思路，但工程根和共享目录路径以各自实际配置为准。

1. **先看 iApp 设置**：打开“存储路径 / 工程路径”，那里显示的才是当前工程根，以它为准。
   雷电 9 上没改过设置时，实测常见位置是 `/data/media/0/iApp/ProjectApp/<项目ID>`，入口在 `src/mian.iyu`；
   日常视图是 `/sdcard/iApp/ProjectApp/<项目ID>`（在雷电 9 上 `/sdcard` = `/storage/emulated/0`，底层是 `/data/media/0`）。
   不同模拟器/真机可能不同；直接 `ls /data/media/0` 通常要先 `adb root`，投递和核对走 `/sdcard/...`。
2. 要跟宿主同步，再在 iApp 设置里把“存储路径 / 工程路径”改为 `/sdcard/Pictures/ProjectApp`，保存并重开工程。
3. 模拟器设置里把共享目录指到宿主工作区 `D:\iAppWorkspace\sync`。雷电的约定：共享目录在设备上显示为 `/sdcard/Pictures`，所以宿主 `sync\ProjectApp` ≡ 设备 `/sdcard/Pictures/ProjectApp`。
4. 验证：宿主新建 `ProjectApp\<项目ID>\src\mian.iyu` → `adb shell ls /sdcard/Pictures/ProjectApp` 可见 → iApp 打开工程能渲染。
5. 说明：Android 9 无分区存储；iApp 需要有存储权限。共享目录不可用时退回 `adb push`（先 `am force-stop`，push 后 `chown u0_a**:sdcard_rw` + `chmod 660`）。

## 4. 安卓 14 环境（API 34，FUSE + 分区存储）

适用：雷电 14 / Android 14，也适用于其它 Android 11+ 模拟器。

背景：iApp 在安卓 14 的工程根固定在
`/storage/emulated/0/Android/data/com.iapp.app/files/iApp/ProjectApp`，
不能在 iApp 内改到 Android/data 之外（实测）。共享存储是 FUSE + scoped storage。

1. 模拟器共享目录同样指到 `D:\iAppWorkspace\sync`；设备侧是 `/sdcard/Pictures`。
2. 先启动一次 iApp，让它生成 `files/iApp` 目录（父目录不要用 root 手建，否则属主不对，iApp 可能写不了）。
3. 用 root 建软链（必须 `su`；普通 `adb shell` 访问 Android/data 会 `Permission denied`）：

```sh
adb shell su -c 'ln -s /storage/emulated/0/Pictures/ProjectApp /storage/emulated/0/Android/data/com.iapp.app/files/iApp/ProjectApp'
```

   - 如果 `ProjectApp` 已存在且是非空目录：先确认没有要保留的数据，移走/合并后再建链接，不要直接覆盖。
   - 链接属主建议跟 app 一致：`chown -h u0_a**:ext_data_rw .../ProjectApp`（uid 用 `pm list packages -U` 查）。

4. 授予所有文件访问：

```sh
adb shell su -c 'appops set com.iapp.app MANAGE_EXTERNAL_STORAGE allow'
```

5. 验证：

```sh
adb shell su -c 'readlink /storage/emulated/0/Android/data/com.iapp.app/files/iApp/ProjectApp'
# -> /storage/emulated/0/Pictures/ProjectApp
adb shell su -c 'ls /storage/emulated/0/Android/data/com.iapp.app/files/iApp/ProjectApp'
# -> Pictures/ProjectApp 的内容
```

   写入回读：root 经链接写一个 probe 文件，宿主 `D:\iAppWorkspace\sync\ProjectApp` 应出现；删除同步。

6. 真实 app 验证：在 iApp 里打开工程 / 编辑保存，宿主侧能看到变化。**不要把 `su <uid>` 派生进程当作 app 访问测试**——FUSE 对非 app namespace 的 Android/data 一律拒绝（AOSP `FuseDaemon::is_app_accessible_path`）。

7. 失效条件：
   - 卸载 iApp / 清除数据 → Android/data 被删 → 链接消失，需重建。
   - 重装后 UID 可能变；`MANAGE_EXTERNAL_STORAGE` 和 root 授权可能重置。
   - 链接建在共享目录（Pictures）里会失败；只能在设备侧建。
   - 建链接后 iApp 需要刷新目录或重开工程。

## 5. 多开与 adb 端口冲突

**推荐一次开一台。** 需要同时开时，每台按自己的安卓版本配置（9 走第 3 节，14 走第 4 节），并先解决端口冲突。

原理：

- adb 通过扫描本机端口发现模拟器：`emulator-5554` ↔ 宿主 5555，`emulator-5556` ↔ 5557，依此类推（每台 +2）。
- 雷电的实例序号 = `vms\leidian0`、`vms\leidian1`…；宿主端口按序号走：0 → 5555，1 → 5557。
- 两套独立安装各自唯一的实例都叫 `leidian0` → 都要求宿主 5555 → 静默冲突；`adb devices` 里的名字可能指向另一台，模拟器重启后还可能 offline。

永久解法（2026-10-26 实测：安卓 9 一台 + 安卓 14 一台）：把第二套安装的实例改名成 `leidian1`。

```bat
C:\LDPlayer\LDPlayer9\ldconsole.exe quit --index 0
:: 等 10 秒，确认 VM 已退出
cd /d C:\LDPlayer\LDPlayer9\vms
ren leidian0 leidian1
cd config
ren leidian0.config leidian1.config
C:\LDPlayer\LDPlayer9\ldconsole.exe launch --index 1
```

验证：

```bat
"C:\Program Files\ldplayer9box\VBoxManage.exe" showvminfo <VM-UUID> --machinereadable | findstr /i forwarding
:: 期望 Forwarding(0)="adb,tcp,,5557,,5555"

adb connect 127.0.0.1:5557
adb -s 127.0.0.1:5557 shell getprop ro.build.version.sdk   :: 期望 34
```

回滚（数据不动）：

```bat
C:\LDPlayer\LDPlayer9\ldconsole.exe quit --index 1
cd /d C:\LDPlayer\LDPlayer9\vms
ren leidian1 leidian0
cd config
ren leidian1.config leidian0.config
```

注意：

- 上面的 `C:\LDPlayer\LDPlayer9` 与 `C:\Program Files\ldplayer9box` 是雷电默认安装位置；装在别的盘或目录时按实际替换。
- 改名必须在关机状态做；只改 `vms` 目录名和 `vms\config` 配置名，不动数据盘。
- 如果目标名 `leidian1` 已存在（之前试过/多开过），先确认它是不是空实例；是就删掉或临时改名，再执行 `ren`。
- 雷电 GUI 可能自动新建一个空的 `leidian0`（0 字节）；**不要启动它**，稳定后可删。
- 改完后不要再依赖 `emulator-5554` 这个名字；统一用 `127.0.0.1:5557`，或先 `getprop` 核对。
- 版本不支持改名时：运行时 `VBoxManage controlvm <UUID> natpf1 delete adb` + `natpf1 "adb,tcp,,5557,,5555"`（重启失效），或用两行 bat 每次开完执行。
- 改端口后 `adb kill-server` / `adb connect ...` 刷新。

## 6. 其他模拟器怎么套

先记住一条：**共享目录不一定映射到 `Pictures`**。雷电映射 `Pictures`；MuMu 映射 `MuMu12Shared` / `MuMuShared`；BlueStacks 映射 `BstSharedFolder`。第 3/4 节的思路不变，只把“目标路径”换成该模拟器的共享目录。

| 模拟器 | 共享目录（设备侧） | adb 定位 | 安卓 14 软链 |
|---|---|---|---|
| 雷电 9 / 14 | `Pictures`（宿主侧可改） | 端口 5555 / 5557；`adb devices -l` | 有 root 即可 |
| MuMu 12 | `/sdcard/MuMu12Shared` 或 `/sdcard/MuMuShared` | `adb devices -l` | 看是否 root |
| BlueStacks 5 | 常见 `/mnt/windows/BstSharedFolder`（版本差异大） | `adb devices -l` | 通常无 root |
| Android Studio AVD | 无内置共享目录 | `emulator-5554` / `5556`；`adb -s` | Google Play 镜像无 root；AOSP 镜像可 `adb root` |

### 6.1 MuMu 模拟器 12（Windows）

- 菜单：模拟器右上角 **菜单 → 更多工具 → 共享文件夹**
  - 「打开电脑端共享文件夹」/「打开安卓端共享文件夹」
  - 「更改共享文件夹路径」→ 选宿主目录 → 重启模拟器生效（自定义路径需 MuMu ≥ 3.8.9）
- 宿主默认：`C:\Users\<用户名>\Documents\MuMu共享文件夹`（官方文档写作 `C:\Users\Documents\...`，实际带用户名目录）
- 安卓端：`/sdcard/MuMu12Shared` 或 `/sdcard/MuMuShared`（版本不同；`adb shell ls /sdcard | grep -i mumu` 确认）
- iApp 接法：共享目录指到工作区后——
  - 安卓 9：工程根设为 `/sdcard/MuMu12Shared/ProjectApp`（或实际目录名）
  - 安卓 14：软链目标换成同一路径
- 来源：MuMu 官方帮助「共享文件夹功能教程」「如何自定义共享文件夹路径」（2026-10-26 抓取，⚠ 未实机）

### 6.2 BlueStacks 5（Windows）

- 没有像雷电/MuMu 那样的“改共享目录”设置页；共享目录由实例配置决定：
  - 关闭 BlueStacks，编辑实例的 `.bstk`（如 `...\Engine\Nougat32\Nougat32.bstk`）：
    `<SharedFolder name="BstSharedFolder" hostPath="C:\ProgramData\BlueStacks_nxt\Engine\UserData\SharedFolder" writable="true" autoMount="false"/>`
    把 `hostPath` 改成工作区目录；改完删 `.bstk-prev`，重启。多实例（Nougat32 / Nougat64 / Pie64）各改各的。
  - 安卓端常见 `/mnt/windows/BstSharedFolder`；旧版可能是 `/sdcard/windows/BstSharedFolder`、`/sdcard/bstfolder/`、`/sdcard/BlueStacksShared/`。**以 `adb shell ls` 实测为准。**
- 一次性导入：Settings → Import Windows Files，或把文件拖进模拟器窗口（不一定适合持续同步）。
- ⚠ 版本差异大，且共享目录不是 `Pictures`；iApp 路径按实际目录改。
- 来源：BlueStacks 官方支持（媒体导入 / 修改安装位置里的 `<SharedFolder>` 配置）+ 社区实测（`/mnt/windows/BstSharedFolder`）。

### 6.3 Android Studio AVD

- 没有内置共享目录；用 `adb push` / `adb pull`，或宿主侧文件监视脚本同步。
- Google Play 镜像无 root；AOSP 镜像可 `adb root`，安卓 14 的链接方案仍可用（目标换成要同步的目录）。

**套用原则**，先确认三件事：

1. 宿主目录映射到设备哪个路径（共享目录设置）；
2. adb 怎么唯一定位这台实例（`adb devices -l` + `getprop`）；
3. 有没有 root（安卓 14 建链接需要）。

没有共享目录就退回 `adb push` / `adb pull`，或宿主侧同步脚本；安卓 14 没有 root 也只能 push/pull。

## 7. 排障清单

| 现象 | 先查 | 处理 |
|---|---|---|
| 宿主改了 iApp 看不到 | 共享目录映射；iApp 是否还开着旧工程 | 重开工程；确认 `/sdcard/Pictures/ProjectApp` 内容 |
| 设备写了宿主没有 | 映射；文件权限 | 两侧 `ls`；确认没写到别的路径 |
| 安卓 14 链接不存在 | 是否卸载/清数据；是否重启后重建 | 重新 `ln -s` |
| 写 Pictures 被拒 | `MANAGE_EXTERNAL_STORAGE` appop | `appops set com.iapp.app MANAGE_EXTERNAL_STORAGE allow` |
| `ln -s` 在 Pictures 报 `Function not implemented` | vboxsf 不支持软链 | 链接建在设备 ext4/FUSE 侧 |
| `adb shell ls Android/data/...` 被拒 | FUSE 只允许 app 自身 namespace | 用 `su` 或真实 app 验证 |
| `emulator-5554` 指向错设备 / offline | 两实例同抢 5555 | `netstat -ano \| findstr :5555`；改名/改端口；`getprop` 核对 |
| bind mount 后 app 看不到 | app 独立 mount namespace | 用共享目录 + 软链，不用 bind |
| iApp 打不开工程 | 入口是否 `<项目ID>/src/mian.iyu`；工程 ID | 修正路径 / 重开工程 |

## 8. 验证清单

- [ ] 宿主 `sync\ProjectApp\<项目ID>` 与设备 `Pictures/ProjectApp/<项目ID>` 双向一致
- [ ] iApp 能打开工程，修改保存后宿主可见
- [ ] `adb -s <serial> shell getprop ro.build.version.sdk` 与目标系统一致
- [ ] 安卓 14：`readlink` 指向 Pictures；`MANAGE_EXTERNAL_STORAGE` 为 allow
- [ ] 多开时 `netstat` 只有一个 5555；第二台在 5557 且 sdk 正确
- [ ] 模拟器重启后链接、授权、端口仍有效（安卓 14 链接在 `/data`，重启保留；appop 持久；改名端口永久）
