# 版本与历史读数

所有结论都带版本前提；换版本后数字与行为都要重测。

## iApp 5.0.1013（参考版本）

| 项 | 读数 |
|---|---|
| versionName / versionCode | 5.0.1013 / 127 |
| minSdk | 21 |
| targetSdk | 37（安装包声明；运行在 API 28 上按 28 走） |
| 工程 `.project` 的 toolversion | `iApp V5.0.1013`（IDE 版本） |
| 开发模式 | `AndroidManifest.xml` 的 `<yuv>3</yuv>`（裕 3） |
| 打包 versionCode | 100000 + versionint |
| 打包 APK targetSdk | 实测 36（与安装包声明 37 不同，以产物为准） |

## 已知会随版本变化的

- `i` 的方法数（本版 390 个公开方法 / 12 字段）
- 接口的 default 方法（决定匿名实现能否用）
- 打包产物的 targetSdk / versionCode 规则
