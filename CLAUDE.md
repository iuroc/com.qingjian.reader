# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

「青简」是 iApp（Android 可视化 IDE）工程，不是 Gradle/Android Studio 工程：界面是 `src/*.iyu` 伪 XML，逻辑是 `src/*.mjava`（Java 语法，由 BeanShell 解释执行）。iApp 在设备上编译运行，仓库内没有 CLI 构建、lint 或测试命令。

- 包名 / 工程 ID：`com.qingjian.reader`；入口必须是 `src/mian.iyu`
- 后端：歌德电子书借阅机公开接口 `gede.5read.com`，`gedeid=84751638`
- 产品与视觉的唯一事实来源：`docs/specs/2026-10-27-qingjian-design.md`；任务拆分见 `docs/plans/2026-10-27-qingjian.md`
- 设计反目标：不得出现个人姓名、个人域名、个人缩写；期刊必须可读；不得用 iApp 不支持的组件导致整页初始化静默失败

## 修改前必读

先读 `.claude/skills/iapp-development/SKILL.md`，按需读其中 `references/` 的对应文档。最容易被忽略、且本项目已在遵守的硬规则：

- `.iyu` 事件体只允许 `call` / `addv`；其余逻辑全部下沉到 mjava
- `type=` 含点号（完整类名）必须在 `build.xml` 的 `<newControl>` 里登记；短名不用。新增 Material 控件时同步改 `build.xml`
- mjava 是 BeanShell：不能用 `final`、具名 class、`0xFF` 大十六进制字面量、可变参数；裸 `findViewById` 不存在，用 `activity.findViewById(id)`
- 模块级变量不跨 `call` 保留，跨页面/跨调用状态一律放 `i.sss`
- `i.sss` 每次运行重置，不能当持久化；持久化用 `qj_store`（写 `getFilesDir()/qingjian/`）
- `importAll()` 只用于 `i.fn` 子模块 facade 的第一行；本项目模块入口统一用 `i.fn("模块名")` 加载后直接调用
- iApp 以内存为准：外部改文件前先 `am force-stop com.iapp.app`，改完在 iApp 里关闭并重开工程；工程打开期间保存会用旧内存覆盖磁盘

## 常用命令

没有构建/测试命令。开发循环是「改宿主文件 → 同步到设备 → 在 iApp 打开工程运行 → 看日志」。

```sh
ADB=${ADB:-adb}          # 若 adb 不在 PATH，设为 platform-tools/adb.exe 的路径
SERIAL=${SERIAL:-emulator-5556}   # 以 `adb devices` + getprop 核对为准

"$ADB" -s "$SERIAL" shell getprop ro.build.version.sdk   # 目标 API 34
"$ADB" -s "$SERIAL" shell am force-stop com.iapp.app     # 改文件前
"$ADB" -s "$SERIAL" logcat -c
"$ADB" -s "$SERIAL" logcat -d -v time 'ygs:V' 'System.err:V' '*:S'
```

- 设备侧工程路径：`/sdcard/Pictures/ProjectApp/com.qingjian.reader`（安卓 14 上 iApp 的工程根是指向它的软链）；宿主与设备通过模拟器共享目录同步
- 日志 tag 是 `ygs`；`i.syso(...)` 只在开发模式有输出，打包 APK 后必须改用 `android.util.Log`
- 控制台报的行号不可信（常报第 0 行）；定位靠 `ygs` / `System.err` + 屏幕现象
- 没有自动化测试。验收标准是 spec §12 的 7 条，真机逐条执行；单点验证在 `loading` 里跑自检并用 `i.syso` 输出 PASS/FAIL
- APK 打包在 iApp 内手动完成，只在用户明确要求时做；versionCode = `100000 + versionint`，产物放 `docs/artifacts/`

## 架构

### 页面 → 入口 → 模块

| 页面 | iyu 入口 | 说明 |
|---|---|---|
| `mian.iyu` | `qj_pages.boot` → `tab(0)` | 首页三容器（精选 10 / 书刊 11 / 足迹 12）+ 自制底栏 20 |
| `detail.iyu` | `qj_pages.detail`（loading） | 详情 + 期次抽屉（id 20 scrim / 24 列表） |
| `reader.iyu` | `qj_reader.boot` | 顶栏 + WebView 7 + 左右点击区 9/11 + 底栏 14–20 |
| `search.iyu` | 尚无控制器 | 见「当前状态」 |

页面初始化入口（`boot` / `detail` / `action` / `tab` / `trail` / `more` 等）会在开头用 `i.fn(...)` 加载自己依赖的模块。模块加载进同一个解释器后方法直接可见，因此：

- 子模块方法加前缀：`core_` / `store_` / `ui_` / `list_` / `pages_` / `reader_`
- 短名（`boot` / `tab` / `more` / `detail` / `action` / `back` / `backKey` / `screen`）是 iyu 或跨模块入口
- `qj_pages` 和 `qj_reader` 都有 `boot` / `back` / `backKey`；同名方法后加载覆盖，**不要在同一页面同时加载这两个模块**

### 模块职责

- `qj_core.mjava` — 全部后端 HTTP、JSON 解析、阅读 token 提取。方法同步阻塞，调用方自己起线程
- `qj_store.mjava` — 阅读历史 `history.jsonl`（按 item key 去重、最多 50 条）与 `cache/<key>.json`
- `qj_ui.mjava` — 色板 token `ui_c()`、dp、深浅色判定、Canvas 图标、底栏状态、页面底色
- `qj_list.mjava` — 用 `ArrayList<HashMap>` 动态渲染列表/横卡/足迹行；点条目写 `i.sss("qj.item")` 后 `i.uigo(...)`
- `qj_pages.mjava` — 首页精选、书刊 Tab + 分类 Chip + 分页、详情、期次、足迹
- `qj_reader.mjava` — 阅读器：抓取、HTML 包装、翻页、字号、目录、进度写入

列表不用 RecyclerView，统一是 `ScrollView + LinearLayout.addView`；封面用 `i.us(imageView, "src", url)`；网络在 `new Thread(...)` 里，回主线程用 `activity.runOnUiThread(...)`。

### 数据模型与跨页状态

列表 item 统一是 `HashMap`，键：`key,type,title,author,summary,cover,surl,bookNum/magazineId/issueNum,newbook`。跳转时把整份 item 序列化成 JSON 放进 `i.sss("qj.item")`——阅读器需要 `surl` 才能打开内容，只传 `bookNum` 不够。

主要 `i.sss` 键：

- `qj.item` 当前书刊快照；`qj.page` 目标页码（同时也被书刊列表分页复用）
- `qj.font` 阅读字号；`qj.idx` 当前页索引；`qj.read.contents/catalogs/total` 本次阅读数据
- `qj.home.mags/books/loaded`；`qj.shelf.loaded`；`qj.kind`（`qikan`/`ebook`）、`qj.cat`、`qj.result`、`qj.issues`

### 阅读链路

```
surl（可能无协议头）→ core_fixSurl → GET /o/a.h?a=GEDE:<surl>
  → 正则取 sid / from / detailUrl(token)
  → GET readNew.jspx?psize=10000&ucatalog=true&ctype=3&fsize=&sid=&from=&detailUrl=
  → msg.contents[]（逐页 HTML）/ msg.catalogs[] / msg.pageAll
```

图书与期刊走同一链路；旧 `epub_epubRead_read.jspx` 对期刊返回 500，不要用。列表接口失败统一是 `{"result":0,"errorMsg":"…"}`，`qj_core` 用 `result != 1` 判定。

阅读器把 `contents[page-1]` 包进完整 HTML（viewport + CSS）后 `loadDataWithBaseURL("https://gede.5read.com/", ...)`；字号与深浅色通过改 CSS 实现，不重新拉接口。

### 视觉约束

颜色只从 `qj_ui.ui_c(token)` 取（surface / surfaceContainer / onSurface / onSurfaceVariant / primary / onPrimary / primaryContainer / onPrimaryContainer / tertiary / outline / divider）；深浅色跟随系统 `uiMode`，没有 App 内开关。字号四级：32 展示（serif）/ 20 标题（serif）/ 16 正文 / 13 辅助；阅读正文 18（可调 16/18/21）。间距取 4 的倍数，可点元素 ≥44×44dp。图标用 Canvas 现画，不用 emoji/文字符号。

## 当前状态（以代码为准，不要相信计划里的勾选框）

- `search.iyu` 只有界面，`qj_pages.search` / `editKey` / `doSearch` 尚不存在，首页也没有搜索入口；搜索功能不可用
- 阅读器只实现左右 1/3 点击区翻页，没有横滑；失败态只有静态「加载失败 / 返回后重试」，没有重试按钮；目录是 AlertDialog 不是抽屉
- 页面没有 `resume` 事件，深色切换依赖 Activity 重建后重跑 `loading`
- 计划里引用的 `docs/evidence.md` 不在仓库中
