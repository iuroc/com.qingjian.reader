# 交付与打包边界

版本前提：iApp 5.0.1013、API 28。

## 默认交付：`.iApp` 备份包

导出位置：`iApp/iAppDir/<包名>.iApp`（ZIP）。

结构（✅ 实测）：**顶层直接是工程内容，没有包名目录**

```
.project
AndroidManifest.xml
build.xml
icon.png
apk/assets/…              # 工程 apk/assets 的内容（含 dex 与生成的 odex/vdex）
bin/<包名>.apk            # 已构建的 APK
bin/<包名>.apk.idsig
files/…
res/
sdk/iapp.sdk
src/*.iyu, *.mjava
```

导入：直接打开 `.iApp` 文件并选择 iApp 打开；**同包名工程已存在时会提示导入失败**，需先删除旧工程。

## APK 打包（仅用户点名时）

| 项 | 读数 |
|---|---|
| versionCode | `100000 + versionint`（versionint=1 → 100001）✅ |
| versionName | 工程设置的原值（1.0） |
| minSdkVersion | 21 |
| targetSdkVersion | 36 |
| platformBuildVersionName | 21 |
| `<sdk>21` | 未观察到对 minSdk 的额外影响（该版本两处都是 21）❓ |

## 打包环境的限制（✅ 实测）

- `ygs` 日志完全无输出（manifest 里 `i_app_logOutput=shi` 也无效）—— **但 `android.util.Log` 正常**：打包版实测 `android.util.Log` 有输出、`ygs` 0 行（2026-10-27）
  - 调试一律用 `android.util.Log.i("TAG", ...)`，`i.syso` 在打包后是死的
- `com.iapp.app.VisualDesigner` 被裁掉 → 不能靠工程根定位资源
- 工程 `files/` 不进 APK；`apk/assets/` 会原样进 APK 的 `assets/`
- 外部库要在打包前转成 dex，并放到 `apk/assets/`
- 打包版 `getFilesDir()` 是打包应用自己的私有目录；开发期写在宿主 `com.iapp.app` 下的存档不会自动带过去

## 外部同步的边界

- 通过共享目录/同步盘改工程时，可能同步出**截断文件**：设备端字节数不足，iApp 报 `Parse error ... Encountered: <EOF>`。改完先核字节数/md5，不一致就重新复制或改用 `adb push`
- 工程在 iApp 里打开期间可能读到旧缓存；改完让用户关闭并重开工程，再核 md5
- 同一轮改多个文件时，可能只有部分文件同步过去；不要只看一个文件就认为整批已生效

## 边界

- 默认交付 `.iApp`
- 只有用户明确点名 APK 时，才由用户在 iApp 内手动打包
