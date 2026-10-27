# 应用图标

版本前提：iApp 5.0.1013、Android 9（API 28）。

## 图标是怎么定的

- 工程根目录的 `icon.png` 就是应用图标；`AndroidManifest.xml` 里 `<icon>icon.png</icon>` 指向它。
- 打包时 iApp 把它**原样**写进 APK 的 `res/mipmap-*/img_iapp.png`（各 density 同一份）。
  ✅ 实测：`aapt dump badging` 显示 `application-icon-*:'res/mipmap-*/img_iapp.png'`，
  解包后 `img_iapp.png` 与工程 `icon.png` 的 md5 完全一致。
- 在 iApp 里手动新建的工程，默认图标是 iApp 自带的 192×192 浅蓝底（`#50C4E5`）+ 白色标志。
- **没有多密度生成**：iApp 不会按 mipmap 目录切图，`icon.png` 一张图被所有 density 复用。

## 为什么以前全是蓝方块

`scripts/create_project.py` 早期版本写的是 70 字节的“1×1 占位图”，注释写“透明”，
实际解码出来是 **RGBA `00 00 FF 7F`**：一个半透明蓝色像素。启动器把它拉满整个图标，
所以每个脚本新建的工程都是纯蓝方块。

判据：`icon.png` 只有几十字节、尺寸 1×1，基本就是占位图，不是真图标。

## 推荐规格

| 项 | 建议 |
|---|---|
| 格式 | PNG，RGBA |
| 尺寸 | 512×512（192×192 也能用，但高分屏会糊） |
| 形状 | 满幅圆角方块，圆角约 22% |
| 安全区 | 关键内容放在中间 ~70%，别贴边（启动器可能裁成圆形/圆角） |
| 颜色 | 背景有足够对比；浅底配深字、深底配浅字 |
| 文件大小 | 20–40 KB 正常；别放照片 |

## 离线生成器（默认方案）

`scripts/make_icon.py`，纯 Python 标准库，**不联网、不依赖 Pillow**。

```bash
# 单张
python scripts/make_icon.py --out icon.png --title 2048 --package com.demo.game2048

# 按工程 manifest 自动读标题/包名，写回 icon.png
python scripts/make_icon.py --project-dir D:/iAppWorkspace/sync/ProjectApp/com.demo.game2048

# 批量补所有工程
python scripts/make_icon.py --all D:/iAppWorkspace/sync/ProjectApp
```

`create_project.py` 已经接入：不传 `--icon` 时自动生成，不再写 1×1 占位图。

### 风格

圆角渐变底 + **大字徽章**：

- 标题里有数字：取最长数字串（`经典 2048` → `2048`）
- 没有数字但有英文：取单词首字母（`File Manager` → `FM`），单词很短则整词（`Calc` → `CALC`）
- 中文标题没有 ASCII：按标题/包名匹配品类，画符号（计算器、文件夹、地球、笔记、聊天、相机、音乐、视频、天气、购物、健康、工具、九宫格）

可选参数：

| 参数 | 作用 |
|---|---|
| `--category auto\|game\|calc\|browser\|file\|note\|chat\|camera\|music\|video\|weather\|shop\|health\|tool\|default` | 强制品类 |
| `--text auto\|none\|2048` | 强制徽章文字；`none` 强制画符号 |
| `--color '#BBADA0'` | 自定义背景色（前景自动选黑/白） |
| `--size 512` | 边长 |

### 自定义图片

- `create_project.py --icon my.png`：直接拷贝
- 或手动替换工程根的 `icon.png`
- 生成器不处理照片；照片类图标请自己裁成正方形、圆角、512×512

## 验证图标有没有生效

```bash
# aapt 在 Android SDK 的 build-tools 目录里；版本按实际替换
AAPT="$HOME/Android/Sdk/build-tools/35.0.0/aapt"     # Windows: C:\Users\<用户名>\AppData\Local\Android\Sdk\build-tools\35.0.0\aapt.exe

# 1. 看打包后的图标声明
"$AAPT" dump badging <apk> | grep application-icon

# 2. 解包确认内容和工程 icon.png 一致
python - <<'PY'
import zipfile
z=zipfile.ZipFile('<apk>')
open('out.png','wb').write(z.read('res/mipmap-xxxhdpi-v4/img_iapp.png'))
PY
```

- 桌面图标有缓存：改完要**重新打包安装**（或卸载重装）才看得到
- iApp 工程列表里的缩略图也可能缓存，重新打开工程/重启 iApp 再看

## 实测记录

2026-10-26：

- 旧占位图解码：1×1，RGBA `00 00 FF 7F` → 启动器显示纯蓝
- 打包 APK 的 `res/mipmap-xxxhdpi-v4/img_iapp.png` 与工程 `icon.png` md5 相同
- 新生成器给 8 个现有工程补图标：2048（文字徽章）、黑金计算器（金色计算器）、
  文件管理器（文件夹）、浏览器（地球）、选择器/脚手架/测试项目（符号）
- 打包安装后桌面图标已目视确认：2048 米色大字、计算器黑金计算器（用户，2026-10-26）
