# 随包脚本

这些是**可选**的辅助脚本，不是使用本技能的前提。主知识在 `references/`；脚本只负责重复性劳动。

| 脚本 | 用途 |
|---|---|
| `make_icon.py` | 离线生成 512×512 工程图标（纯标准库） |
| `create_project.py` | 新建最小 iApp 工程（默认调用 `make_icon.py`） |
| `material_scan.py` | 扫 iApp APK 里哪些 Material 类有 `(Context)` 构造 |
| `class_methods.py` | 列某个类自己声明的方法（核对 API 是否被裁剪） |
| `dex_classes.py` / `dex_api_dump.py` / `dex_body.py` / `dex_map_fields.py` | dexdump 分析小工具 |
| `build_class_dex.py` | 把 Java 源码编译成 iApp 可加载的 dex（继承类的场景） |
| `build_sora_dex.py` | 把 sora-editor AAR 转成 dex + 资源 apk |
| `build_aar_dex.py` | 通用版：多 AAR + 依赖资源 + 补桩 → dex + 资源 apk（XUI 1.1.9 实测） |
| `check_portable.py` | 分享前自检：禁止外部路径与作者机器路径 |

## 环境

- Python 3.10+
- `dexdump`：默认从 `PATH` 找；Android SDK 的 build-tools 目录里自带，也可设 `DEXDUMP=<dexdump 完整路径>`
- Android build-tools：`aapt2` / `d8` 默认从 `PATH` 找；也可设 `BUILD_TOOLS=<build-tools 目录>`
- JDK：`javac` 默认从 `PATH` 找；也可设 `JDK_BIN=<jdk bin 目录>`

```bash
# 例：Windows（Android Studio 默认 SDK + Oracle JDK 常见路径；版本号按实际替换）
set BUILD_TOOLS=%LOCALAPPDATA%\Android\Sdk\build-tools\35.0.0
set JDK_BIN=C:\Program Files\Java\jdk-21\bin
set DEXDUMP=%BUILD_TOOLS%\dexdump.exe

# 例：类 Unix
export BUILD_TOOLS=$HOME/Android/Sdk/build-tools/35.0.0
export JDK_BIN=/usr/lib/jvm/java-21-openjdk/bin
export DEXDUMP=$BUILD_TOOLS/dexdump
```

## 用法示例

```bash
# 图标
python scripts/make_icon.py --project-dir D:/iAppWorkspace/sync/ProjectApp/<项目ID>
python scripts/make_icon.py --all D:/iAppWorkspace/sync/ProjectApp

# 新建工程
python scripts/create_project.py --root D:/iAppWorkspace/sync/ProjectApp --package com.example.demo --title 演示

# 扫 APK
python scripts/material_scan.py <你的 iApp APK>
python scripts/class_methods.py <你的 iApp APK> com/google/android/material/slider/

# 编译类进 dex
python scripts/build_class_dex.py --src <java 源码目录> --out <输出.dex> --lib <android.jar>
```

## 分享前自检

```bash
python scripts/check_portable.py
```

零命中才适合把整个目录拷给别的 workspace。
