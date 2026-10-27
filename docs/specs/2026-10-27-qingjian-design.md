# 青简 · 书刊阅读器重做 — 设计

- 日期：2026-10-27
- 状态：待批准
- 前身：`com.oyp.pytx`（鹏阅天下，2021-07，纯 iyu）
- 证据：`docs/evidence.md` 批次 `API-A1`（接口普查）、`M3-D1`（M3 组件样张实机）

## 1. 意图

把五年前的旧工程重做成一个能真机演示的作品：去掉全部个人姓名痕迹，界面与交互按 Material 3 重做，
后端沿用歌德电子书借阅机的公开接口（`gede.5read.com`，`gedeid=84751638`）。

旧版的问题：纯 iyu 实现、写死作者署名与个人域名、界面是色块堆叠、期刊阅读接口已换代导致不可读。
新版只复用后端数据，不复制旧界面与旧交互。

## 2. 目标 / 非目标 / 反目标

**目标**

- 真机上从打开 App 到读完一本书、一期期刊的完整链路可用
- 界面与交互完全重做：Material 3 组件 + 青简的墨绿/宣纸气质，深浅色都成立
- 工程结构符合工作区规范：`.iyu` 声明布局，`.mjava` 写逻辑与样式
- 作为作品集可以演示：断网、接口失效时仍有明确状态，不白屏

**非目标**

- 不与旧版功能 1:1；旧版的密码页、下载成 txt、封面弹窗不保留
- 不做账号、云同步、整本离线下载
- 不重做后端，不自建代理服务

**反目标**（技术上成立也算失败）

- 依赖个人姓名、个人域名、个人缩写
- 期刊能点开却读不出内容
- 用了 iApp 不支持的组件导致整页初始化静默失败

## 3. 约束

- iApp 5.0.1013，API 34（LDPlayer Android 14）；内置 material 1.13.0
- 投递走共享目录 `android-sync/ProjectApp/<包名>/` ↔ `/sdcard/Pictures/ProjectApp/<包名>/`
- 后端是第三方公共服务，无 SLA，字段与路径随时可能变
- 交付物：iApp 工程 + 可安装 APK
- 包名 `com.qingjian.reader`（本设计的裁决）

## 4. 后端事实（2026-10-27 实测）

所有接口返回 UTF-8 JSON，`Content-Type` 是 `text/html`。

### 4.1 列表与搜索

| 用途 | 请求 | 关键返回字段 |
|---|---|---|
| 图书分类 | `GET /apis/touchBook/books.jspx?cataid=<id>&page=<n>&pageSize=<n>&gedeid=84751638` | `msg.page/pageCount/allCount/list[]`；item：`title, author, summary, bookNum, cover, bcover, isbn, publish, pageNum, newbook, hotbook, surl, urlid, type` |
| 期刊分类 | `GET /apis/magazine/magazines.jspx?cataid=<id>&page=<n>&pageSize=<n>&gedeid=84751638` | item：`name, id(数字), magazineNum, coverPath, summary, ISSN, CN, surl, urlid` |
| 图书搜索 | `GET /apis/touchBook/books.jspx?keyword=<utf8 编码>&page=<n>&pageSize=<n>&gedeid=84751638` | 同上；可叠加 `cataid` 限定分类 |
| 期刊期次 | `GET /apis/magazine/magazineItems.jspx?magazineid=<数字 id>` | `msg.magazine`、`msg.itemList[]`：`magazineItemNum, issue, name, coverPath, id, sort, surl` |

- 分页两个列表都实测可用（`page` + `pageSize`，`pageSize=-1` 返回全部）
- 期刊**没有** keyword 搜索：`magazines.jspx?keyword=` 返回“未获取到数据”
- 期刊期次只认数字 `id`；传 `MZ...` 编号报“magazineid 不能为空或参数不正确”
- 失败的统一形态：`{"result":0,"errorMsg":"…"}`

### 4.2 分类表

图书：124 诗歌散文、125 小说传记、126 科学技术、127 国学经典、128 历史文化、129 社会科学、
130 心理成长、131 艺术审美、132 哲学宗教、140 教育研究、141 家长尊享。
**123「精品推荐」已无数据**（`没有获取到数据`），旧版精选页的图书半边因此是空的。

期刊：6 精品推荐、3 时政军事、4 文学艺术、5 时尚生活、8 财经管理、9 文化综合、10 其它。

### 4.3 阅读（图书与期刊统一走新接口）

旧接口 `/other/epub_epubRead_read.jspx` 对期刊返回 HTTP 500，已废弃。新流程：

1. `GET https://gede.5read.com/o/a.h?a=GEDE:<URL 编码后的 surl>`
   → HTML 内 `InitData`：`sid`、`from`、`detailUrl`（约 144–160 字符密文 token）
   - 该入口会 **301 到另一个主机**（实测 `gdread.sslibrary.com`），跟随跳转，不要写死域名
   - `surl` 可能是无协议头的 `gede.5read.com/g/….h`（图书）或带 `https://` 的完整 URL（期刊），拼接前统一补协议
2. `GET https://gede.5read.com/other/epub_epubRead_readNew.jspx`
   `?psize=10000&sid=<sid>&ucatalog=true&ctype=3&fsize=20&from=<from>&detailUrl=<token>`
   → `msg.contents[]`（逐页 HTML，含 `<img>`）、`msg.catalogs[]`（`title/page/contentIndex`）、`msg.pageAll`

- 不需要 cookie，token 自带授权
- 实测：图书 333 页 / 9 个目录项；期刊 218 页 / 30 个目录项

### 4.4 失效与替代

- `http://ouyangpeng.top/urls.json`（旧搜索配置源）已 302 到无关站点 → 彻底不用，搜索改走 `books.jspx?keyword=`
- 期刊 `magazineItems` 的 `magazineNum` 参数失效 → 用数字 `id`

## 5. 产品结构

### 5.1 页面

| 页面 | 内容 |
|---|---|
| 首页 `mian.iyu` | 底部导航三个：精选 / 书刊 / 足迹 |
| 精选 | 有阅读历史时顶部先插「继续阅读」横卡；品牌区；期刊精选大卡横滑；图书新书竖卡双列；每块有「查看全部」 |
| 书刊 | 顶部 Tab：期刊 / 图书；下方横向分类 Chip；列表分页加载，底部「加载更多」 |
| 足迹 | 本机阅读历史：封面、书名、读到第几页、进度条；顶部「清空」 |
| 详情 `detail.iyu` | 封面、标题、作者/期次、简介；「开始阅读」固定底部整宽按钮（拇指区）；期刊先弹期次选择 |
| 阅读器 `reader.iyu` | 顶部栏（返回 / 目录）、正文 WebView（左右点击区翻页 + 横滑）、底部页码条与字号三档 |
| 搜索 `search.iyu` | 输入框 + 最近搜索 + 分类快捷 Chip + 结果列表；图书在线搜索，期刊本地索引过滤 |

导航：`uigo` 压栈；返回用 mjava `activity.finish()`（绑了 `downkey` 会吞返回键，需自行补）。

### 5.2 关键交互

- 列表点卡片 → 详情；「开始阅读」→ 阅读器
- 期刊详情 → 期次列表（底部抽屉）→ 选一期 → 阅读器
- 详情页主按钮固定在底部安全区，内容滚动时不动（拇指区可达）
- 阅读器：左右各 1/3 透明点击区 + 横向滑动翻页，底部按钮保留作可见提示；
  目录抽屉跳章；字号小/中/大三档；退出自动记忆页码
- 读到最后一页显示克制的「已读完」态，足迹里进度满格（不做庆祝动画）
- 足迹点条目 → 直接回到上次页码；首页有历史时展示「继续阅读」
- 所有空态、加载态、失败态都有明确文案与重试

## 6. 数据流

```
分类列表 ──► books/magazines.jspx?cataid&page&pageSize ──► 卡片列表
                                        │
                          期刊 ──► magazineItems.jspx?magazineid ──► 期次
                                        │
                              surl ──► /o/a.h（取 token）
                                        │
                          readNew.jspx ──► contents / catalogs / pageAll
                                        │
                                    WebView 渲染单页
```

- 列表与阅读内容按「最后一次成功」落盘缓存（iApp 工程 `files/` 下），断网时读缓存并标注「离线」
- 阅读历史一行一个 JSON 对象（JSONL），按 **item key 去重就地更新**，不是每次阅读追加一条：

  ```json
  {"key":"HYB11735982","type":"ebook","title":"…","author":"…","cover":"https://…",
   "surl":"gede.5read.com/g/….h","magazineId":25,"issueNum":"MZ12038766","issueLabel":"2023 第 23 期",
   "page":42,"updatedAt":1793102000}
  ```

  - 图书 key = `bookNum`；期刊 key = 期次的 `magazineItemNum`
  - 期刊也进足迹；`surl` 必须存，否则无法重建阅读流程
- 搜索：图书在线分页；期刊索引在**搜索页首次打开时**后台拉全 7 个分类（`pageSize=-1`，约 495 条）
  并落盘缓存，按名称 / 简介 / ISSN / CN 本地过滤；拉取期间展示「正在建立期刊索引」

## 7. 技术方案

### 7.1 工程与模块

```
com.qingjian.reader/
├── src/
│   ├── mian.iyu            首页（精选 / 书刊 / 足迹）
│   ├── detail.iyu          书刊详情 + 期次抽屉
│   ├── reader.iyu          阅读器
│   ├── search.iyu          搜索
│   ├── qj_core.mjava       HTTP、JSON 解析、token 提取、缓存
│   ├── qj_ui.mjava         颜色 token、组件封装、图标绘制
│   ├── qj_reader.mjava     HTML 包装、CSS 注入、翻页与进度
│   └── qj_store.mjava      历史与缓存的读写
├── files/  res/  icon.png
├── AndroidManifest.xml  build.xml  .project
```

- 多模块用 `i.fn("qj_core")` 加载；子模块方法统一前缀
- `i.sss` 跨页面传参：传 **item 快照 JSON 字符串**（title / author / cover / summary / bookNum / type /
  surl / magazineId / issueNum / issueLabel）+ 目标页码，而不是只传 `bookNum`。
  阅读器必须拿到 `surl` 才能换 `detailUrl` token；只给 `bookNum` 打不开内容。
  返回结果同样走 `i.sss` + `finish()`

### 7.2 布局与组件

- 布局与静态文字写在 `.iyu`；颜色、圆角、运行期内容在 mjava 补
- Material 组件一律 ppt 全类名 + `build.xml` 登记；每个组件在 `qj_ui` 里有一个封装方法
  （如 `qj_filledButton(id)`），重载与 Context 的坑只踩一次
- `TextInputLayout` 固定走 ppt 声明 + `loading` 修复配方（`fixField()`），不在页面里重复写
- 已验证的 API 坑：`MaterialButton.setStrokeColor` 只收 `ColorStateList`；
  `setIndicatorColor` 必须传 `int[]`；方法不存在会中断整个 `loading` 事件，`try/catch` 接不住
- 图标用 Canvas 现画（返回、搜索、目录、书脊），不用 emoji/文字符号

### 7.3 阅读器

- `contents[page-1]` 取出 HTML 片段，包进完整文档：
  `<meta name="viewport" content="width=device-width, initial-scale=1">`
- 注入 CSS：正文字号 18sp 基准、行高 1.75、左右 24dp、`img{max-width:100%;height:auto;display:block;margin:0 auto}`、
  深色模式背景 `#121511`、文字 `#E3E3DA`，图片 `filter:brightness(.86)`
- 翻页手势：WebView 外层覆盖左右各 1/3 的透明点击区；WebView 内注入触摸监听做横滑，
  与点击区互斥（滑动优先，位移超过阈值才算翻页）
- 字号三档改 CSS `font-size`，不重新拉接口
- 目录项按 `contentIndex` 跳页；`pageAll` 作为总页数
- 加载失败显示重试按钮，保留上一页内容不白屏

### 7.4 缓存与错误

- 目录缓存：每个分类第一页 + 上次成功页，文件存储，带时间戳
- 失败统一：Snackbar 一句 + 列表保留缓存内容 + 「重试」按钮
- 首次无网：精选页显示引导态，不显示假数据

## 8. 视觉

### 8.1 色板

| Token | 浅色 | 深色 |
|---|---|---|
| surface | `#FBF8F1` | `#121511` |
| surfaceContainer | `#F5F2EA` | `#1E211D` |
| onSurface | `#1B1C18` | `#E3E3DA` |
| onSurfaceVariant | `#414944` | `#C0C9C1` |
| primary | `#3F6459` | `#A9CDC1` |
| onPrimary | `#FFFFFF` | `#12332C` |
| primaryContainer | `#C3E9DC` | `#2A4A42` |
| tertiary（赭石） | `#79582B` | `#E4C28C` |
| outline | `#717973` | `#8A938C` |

### 8.2 字体与形状

- **只保留四级**，不临时加级差：32sp 展示（serif）/ 20sp 标题（serif）/ 16sp 正文（sans）/ 13sp 辅助（sans）
- 权重只用两级：Regular + Bold；标题字距略放开，正文不动
- 阅读正文 18sp / 行高 1.75 是唯一例外（用户可调三档 16 / 18 / 21）
- 间距取 4 的倍数，常用 8 / 12 / 16 / 24 / 32；页边距 16dp（列表）/ 24dp（详情与阅读）；分区间距 24 / 32dp
- 卡片 12dp 圆角，卡片内封面 8dp；按钮胶囊；Chip 视觉高 32dp、**触控目标 ≥44dp**
- 所有可点元素触控区不小于 44×44dp（图标按钮、Chip、足迹条目）
- 图标：竹简母题（竖条 + 墨色），Canvas 绘制，自适应深浅色

### 8.3 动效

- 页面切换用 `i.lan(...)` 或 `overridePendingTransition`，克制为主
- 阅读翻页仅滚动回顶 + 内容替换，不做花哨转场

### 8.4 深色模式

跟随系统，**不做 App 内开关**。每页在 `loading` 读
`activity.getResources().getConfiguration().uiMode` 选色板；系统切换会重建 Activity，颜色重新应用。
阅读器重建后从 `i.sss` 恢复页码与阅读位置；WebView 的正文 CSS 与 chrome 同步换色。

## 9. 明确砍掉

- `mima.iyu` 密码页（无入口的死代码）
- 「下载本书」txt 导出与 `down.iyu` 进度弹窗
- 正文水印 `[鹏阅天下 欧阳鹏作品]`、作者署名、个人域名、个人缩写包名
- 通用封面弹窗 `img.iyu`（详情页已能看封面，不做二次弹窗）

## 10. 设计裁决（builder 可直接执行）

- 包名 `com.qingjian.reader`；App 名「青简」
- 精选页图书半边取 124/125 中 `newbook=1` 的条目（**客户端过滤**；接口的 `newbook` 参数无效），
  不足 6 本时补该分类前几本
- 底部导航 3 项：精选 / 书刊 / 足迹；搜索是首页右上角入口
- 详情页主操作固定在底部整宽；阅读器左右 1/3 点击区 + 横滑翻页
- 首页有历史时展示「继续阅读」；读到最后一页给「已读完」态
- 搜索页未输入时展示最近搜索 + 分类快捷，不出现空白页
- 视觉级差 4 级（32 / 20 / 16 / 13），阅读正文 18 为用户可调例外
- 页间传**完整 item 快照 + surl**，不只传 bookNum；足迹按 item key 去重就地更新，期刊也进足迹
- 深色模式跟随系统，无 App 内开关
- 期刊搜索：搜索页首次打开时拉全 7 分类建索引并落盘，过滤名称 / 简介 / ISSN / CN
- 读取用 WebView，外层 chrome 全自制
- 列表分页 `pageSize=30`，底部「加载更多」
- 离线只做「上一次成功缓存」，不内置示例书库
- 字号三档 16 / 18 / 21sp，默认中

## 11. 风险

| 风险 | 应对 |
|---|---|
| 借阅机接口下线或 `gedeid` 失效 | 缓存 + 明确错误态；接口集中在 `qj_core`，替换成本低 |
| `/o/a.h` 页面结构变更导致 token 提取失败 | 提取失败给可读提示；解析用一个函数集中处理 |
| 843 / 546 条大分类首屏慢 | 分页 30 条；失败可重试 |
| M3 组件在 iApp 里某属性静默无效 | 每个组件先在 `com.demo.m3demo` 验证，再进正式页 |
| iApp 打包后行为差异 | 里程碑里安排一次 APK 打包回归 |

## 12. 验收标准

1. 真机打开 App，3 秒内看到精选内容（或明确的加载/失败态）
2. 期刊：分类 → 选刊 → 选期 → 读到最后一页，出现「已读完」，正文图片正常显示
3. 图书：搜索 → 详情 → 阅读 → 退出后足迹出现、首页出现「继续阅读」，点击回到原页码
4. 深浅色切换后，所有页面文字与背景对比度正常
5. 断网启动不白屏，缓存内容可读，有「重试」
6. 阅读器左右点击区与横滑都能翻页，底部按钮同样可用；详情页主按钮始终在底部拇指区
7. 打包 APK 安装后上述 1–6 仍成立
