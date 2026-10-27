---
name: iapp-development
description: 开发、调试、打包 iApp（Android 可视化 IDE，显示名"测兆编程"）工程时使用。只要出现 .iyu 界面文件、.mjava 模块、裕语言语法、call 跨语言调用、iApp 工程结构、adb 投递调试、iApp 打包交付等需求，就先读本技能。里面有实测过的语法铁律、失败签名、投递链路和探针方法，能避免重复踩坑；不确定的行为按本技能的探针流程先测再写。
---

# iApp 开发知识库

iApp（显示名"测兆编程"）是 Android 上的可视化 IDE：工程是「界面文件 + 模块代码 + 资源」的目录，直接在设备上编译运行。

## 写什么 / 不写什么（本库的边界）

本库优先记录 **iApp 特有** 的行为，不重复通用 Android / Java 知识；通用知识只在它是“iApp 里可直接复制的完整配方”时收录（如 Canvas 卡面、外部库装载）。

- **不写**：与原生 Android / Java 完全一致的零散用法。例如 `Paint.setAntiAlias(true)`、`FileWriter` 读写文本、`AlertDialog.Builder` 的基本链式调用——凭通用知识就能写对，写进来只增加维护负担和过期风险。
- **必写**：在 iApp 里**不能照原生 / Java 的写法直接用**，需要转换、绕开或额外处理的。判据是"照通用知识写会失败或静默不生效"，包括：
  - 语言层限制：BeanShell 不支持 `final`、具名 class、`0xFF` 大十六进制字面量、可变参数；模块级变量跨 `call` 丢失
  - 能力缺失：不能继承类（自定义 View / Adapter 要走 dex）；裸 `findViewById` 不存在
  - 属性 / 事件名与原生不一致：ppt 用 `layout_weight` 而不是 `weight`；`alpha`、`weight` 在 ppt 里静默无效；事件名写错静默忽略
  - 宿主环境副作用：开发模式跑在 `com.iapp.app` 进程里，`getFilesDir()` 多工程共用、权限是宿主的、改系统 UI / 方向会影响宿主
  - 需要双证据才敢下结论的：行为与文档不一致、版本相关（API 28 vs 34）
- **写法**：先写"原生写法是什么 → 在 iApp 里会怎样 → 应该怎么写"三段式；结论带 ✅/⚠/❓ 与版本前提。
- **更新前自检**：新增内容如果删掉后，一个懂 Android / Java 的人照样能写对，就不该进来；除非它是 iApp 环境里必须原样复制的完整配方。

## 路径写法（写实还是占位）

本库要分享给别的 workspace，但不等于把路径全变成占位符。判据是**这个值对“大多数用这个环境的人”是否成立**：

- **写实**：常见环境/工具的默认路径，例如 `C:\Program Files`、`C:\LDPlayer\LDPlayer9`、`/sdcard/Pictures`、`/data/media/0`、`com.iapp.app`。这些是通用知识，写实才方便别人照着做。
- **占位或环境变量**：只对作者机器或本项目成立的，例如 `E:\...` 这种作者盘符路径；随实例/项目变化的，例如 `<serial>`、`<VM-UUID>`、`<项目ID>`；版本化工具目录用 `BUILD_TOOLS` / `JDK_BIN` / `DEXDUMP` 覆盖，文档同时给常见默认位置。
- **不要为了“可移植”把常见路径泛化成 `<目录>` 或 `%ENV%`**；只有确实没有共识默认值时才这么做。

## 五分钟模型

```
工程根/                       # 设备上的实际位置随环境不同（iApp 内设置或按环境文档）
├── src/
│   ├── mian.iyu              # 入口界面（必须叫 mian.iyu）
│   ├── *.iyu                 # 其它界面
│   └── *.mjava               # Java 模块（无 class 外壳，直接写方法）
├── files/                    # 运行期文件
├── res/  sdk/  icon.png
├── AndroidManifest.xml
└── .project                  # 工程元数据
```

界面文件是伪 XML：`<View id= did= type=>` + `<ppt>` 属性块 + `<event>` 事件块；
全局事件集中在文件末尾 `<UIEventset>`，事件项写成 `<eventItme type="loading">代码</eventItme>`。

代码分两种语言，可互相调用：
- `.iyu` 里只留 `call(...)` / `addv(...)` 做编排（日志、Toast、运行期改动都在 mjava 里；静态样式写 ppt）
- `.mjava` 里是 Java 语法，但**由 BeanShell 解释执行**，不是编译成 class（报错原文见 `references/mjava-guide.md`）

`call` 三要素：`call(接收返回值的变量, "mjava", "模块.方法", 参数…)`；无返回/无参用 `call(null, "mjava", "app.run")`。
传给模块的参数个数要与方法签名一致，返回值只对 mjava 有效。

## 控件类型：短名直接写，完整类名必须登记

> 术语：本库说的“自定义控件”= 在 ppt 里用 `type=` 声明的非短名控件（完整类名 + `build.xml` 登记），
> **不是** Java 里继承 View 写的新类——后者 BeanShell 写不了，必须编译进 dex（见 `external-library-guide.md`）。

**三条判据（按顺序问，止于第一条命中）**：

| 问 | 命中 → | 否则 |
|---|---|---|
| 控件本身能不能在 `.iyu` 里声明？ | ppt 用 `type=` 声明（默认做法，设计器可见可控） | → 问下一条 |
| 样式是不是静态、且 ppt 有对应键？ | 写 ppt 普通属性 | → mjava setter |
| 值是不是运行期才知道？ | mjava 填内容，声明方式不变 | 写死在 ppt |

- **mjava 动态创建只有两种情况**：① 整类无法 ppt 声明（必须带构造参数）；② ppt 路径实测不可用（设计器崩溃类）。
  **不要因为“保险”整页动态创建**；适配器也不构成理由（`RecyclerView` 在 ppt 声明、运行期 `setAdapter` 即可）
- **mjava 只补 ppt 表达不了的样式**：tint、描边、圆角、渐变、alpha、选中态、Ripple。
  **不要重复设置 ppt 已写的颜色/字号/尺寸**——画布不执行 mjava，重复设置 = 预览与真机不一致（`style-guide.md`）
- **ppt 管布局与静态内容**：`width/height/layout_margin*/layout_weight/orientation/gravity/text/textsize/textcolor/backgroundcolor/textstyle/maxlines/ellipsize/visibility/clickable/minheight/elevation`
- **运行期内容在 mjava**：文字、选项、tab、菜单、进度值、列表项、adapter
- **`padding` 例外**：ppt 的 `padding` 按 **px** 解释（不是 dp），要 dp 精确内边距就在 mjava 里 `setPadding`
- **全局统一色/字号**：可集中到 mjava 主题模块，代价是画布看不到真机配色（有意例外，见 `style-guide.md`）
- **设计器崩溃类**：`SearchBar` 写进 ppt 后，设计器**保存/序列化时**崩（`VisualDesigner.T0` NPE，与登记无关）：
  `T0` 把每个 View 的 `tag` 当 `Object[]` 读，`id >= 1` 时跳过 null 检查；`SearchBar` 构造自建的内部子 View
  带资源 id 但没有 tag → NPE。只能 mjava 动态创建、**不登记**。`TabLayout` / `ChipGroup` / `MaterialDivider`
  已实测排除（2026-10-27，`pitfalls.md` #7）
- **版本前提**：ppt 完整类名 = 真实实例是 API 34 实测；API 28 的旧结论是“影子实例”⚠

**选型规则：Material 组件一律优先写 `com.google.android.material.*` 完整类名**；
短名只在没有可靠 Material 映射时兜底——部分短名指向 iApp 封装或 androidx
（`TabLayout` → `com.iapp.app.TabLayout`、`CardView` → androidx、`SwitchCompat` → androidx、
`Toolbar` → androidx）。完整清单、支持矩阵与验证方法见 `references/material-components.md`。

`.iyu` 的 `type=` 只有两条来源，**写之前先看值里有没有点号**：

| `type` 写法 | 例子 | `build.xml` |
|---|---|---|
| 内置短名（无点号） | `TextView`、`LinearLayout`、`TextInputLayout` | 不用登记 |
| 完整类名（含 `.`） | `com.google.android.material.textfield.TextInputEditText` | **必须登记**，否则设计器显示“未知” |

登记格式（`build.xml` 里唯一允许手写的地方，子项标签原文就是 `itme`）：

```xml
<newControl><itme title="显示名" class="完整类名" info="说明"/></newControl>
```

- 判据是 **`type` 的语法**，不是“这个类算不算自定义 / 是不是 Material”
- **登记随工程走**：新建工程（含每轮探针工程）的 `build.xml` 是空模板，旧工程的登记不继承
- 登记只影响设计器；运行时渲染不依赖它，但“未知”控件展开组件树可能闪退
- 短名清单在 `references/builtin-controls.md`，**不要按“安卓类名去包名”猜**（`Switch` 就不是短名）
- 自查：`grep -n 'type="[^"]*\.' src/*.iyu` 列出全部完整类名，逐个回 `build.xml` 对 `class`

## iyu 白名单（只允许 `call` / `addv`）

`.iyu` 事件体**只允许 `call` / `addv`**。其它裕语言函数、Java 表达式（`activity.finish()`、`i.lan(...)`、`end()`、`ViewGroup.removeView(...)` 等）一律下沉到 mjava，用原生写法：

| 原函数 | 替代 |
|---|---|
| `us` / `ug` | 原生 setter / getter（mjava） |
| `gvs` | `activity.findViewById(id)` |
| `s` / `ss` / `sss` / `dim` | `i.sss` / 隐藏控件 / SharedPreferences |
| `syso` | `i.syso(...)` 或 `android.util.Log` |
| `tw` / `utw` | Toast / AlertDialog |
| `uigo` | `.uigo` 方式（见对应文档） |

返回、转场、删视图都写成 mjava 方法，再由事件体 `call` 进去。

## 多模块（加载另一个 mjava）

```java
i.fn("b");          // 实测加载，模块名不带扩展名
b_hello();          // 加载后直接调
```

- **`importAll()` 写在每个 public 入口的第一行、方法体内**（只用于 `i.fn` 子模块的 facade）；
  写在文件顶层会立即执行并报 `Command not found: importAll()`；
  加载前调用也会 `Command not found`，整个方法中断，`catch` 接不住
- 同名方法后加载覆盖；子模块方法统一加前缀（`core_` / `ui_` / …）
- 推荐 facade 模式：`game.mjava` 只暴露 `init/layout/...`，子模块私有
- 状态仍放 `i.sss`；模块级变量只在本次 `call` 内有效
- `i.d.f("b.mjava")` 只在开发模式可用；打包后 `i.d` 是 `xn0`，没有 `f(String)`。
  **交付用 `i.fn`，源码直接打包，不合并**
- `i.call("b.b_hello","mjava")` 会新建解释器且找不到当前工程模块（实测返回 null），
  跨模块加载不要用它
- 完整规范：`references/modularization-guide.md`

## 核心规则（iApp 硬约束 + 推荐做法）

【硬】= iApp 行为如此，不遵守会坏；【荐】= 本库推荐，按你的环境取舍。

1. 【硬】**入口必须是 `src/mian.iyu`**（不是 main.iyu）。
2. 【荐】**iApp 以内存为准**：外部改文件前先 `am force-stop`，或在 iApp 里关掉工程；否则保存/运行会用旧内存覆盖磁盘。
3. 【荐】**投递优先走你环境里最稳的同步方式**（共享目录/同步盘），工程打开期间可能有旧缓存，关/重开工程后刷新；无同步链路或 md5 核不上再用 `adb push`。不要用 bind mount（应用 namespace 看不到后加的挂载）。
4. 【荐】**双证据**：屏幕现象（screencap）+ 原文日志
   `adb logcat -d -v time 'ygs:V' 'System.err:V' '*:S'`
5. 【硬】日志 tag=`ygs`；mjava 里 `i.syso(...)` 的内容出现在这里（旧写法 `.iyu` 里的 `syso` 已按白名单禁用）。
6. 【硬】控制台行号不可信（常报第 0 行），定位靠日志与现象。
7. 【荐】结论标注：✅实测 / ⚠推测 / ❓未知。null/false/0 必须有对照锚点。
8. 【硬】**`type=` 含点号（完整类名）→ 必须写进 `build.xml` 的 `<newControl>`**；短名不用。新建工程的登记不继承（见上节）。
   **例外**：`SearchBar` 写进 ppt 后，设计器保存/序列化时会崩（登记与否都一样；`TabLayout`/`ChipGroup`/`MaterialDivider` 已排除），不要 ppt 声明，走 mjava 动态创建。

## 已验证

| 结论 | 级别 |
|---|---|
| 入口 `src/mian.iyu` 生效，载入事件触发 | ✅ |
| 雷电 9（Android 9 / API 28）实测工程根 `/data/media/0/iApp/ProjectApp/<项目ID>`（= `/sdcard/iApp/ProjectApp/<项目ID>`）；其它 Android 9 环境以 iApp 设置为准 | ✅（仅雷电 9，参考） |
| 载入事件格式 `<UIEventset><eventItme type="loading">…</eventItme></UIEventset>` | ✅ |
| `call(a, "mjava", "app.bind")` 能调起模块方法 | ✅ |
| `.mjava` 直接写方法（无 class），`syso()` 输出到 `ygs` | ✅ |
| 模块里 `activity` 与 `i` 是两个默认对象 | ✅ |
| `activity.findViewById(id)` 与 `i.gvs(id)` 返回同一实例 | ✅ |
| 裸 `findViewById(id)` 不存在，报 `Command not found: findViewById( int )` | ✅ |
| 模块级变量不跨 `call` 保留（两次调用都从初值开始） | ✅ |
| `call` 能传参并接收返回值 | ✅ |
| `did` 决定控件挂到哪个父容器；根子控件数/顺序与文件一致 | ✅ |
| push 改文件后重开工程，界面按新内容渲染 | ✅ |
| mjava 由 BeanShell 解释：`final`/具名 class/`0xFF`/可变参数/`bsh.*` 都会让模块失效 | ✅ |
| 匿名**类**失败并中断整个载入事件；匿名**接口实现**在 API 28 可用 | ✅ |
| `{...}` 数组字面量可用（与旧结论相反） | ✅ |
| 循环变量 `i` 不遮蔽 iApp 的 `i` 对象（API 28） | ✅ |
| `i` = `Aid_javaCode`：390 个公开方法、12 个公开字段 | ✅ |
| `i.d` 是 BeanShell 解释器，**每次 call 新建** | ✅ |
| `i.ss` 底层 HashMap 默认 null，读写直接 NPE | ✅ |
| `i.sss` 跨 call 保留，但**每次运行重置**（同 pid 也一样） | ✅ |
| `i.dim` 按前缀分派：`sss.` / `ss.` / 无前缀落 `i.a` | ✅ |
| 外部库：JAR→D8→dex、AAR 拆 classes.jar/res、DEX 直用；产物放 `apk/assets/` | ✅ |
| 开发用工程根 `/apk/assets/*.dex` 加载；打包用 assets→cache 或 `getExternalFilesDir` | ✅ |
| 带资源的 AAR：aapt2 链接用独立包 ID（≥0x7f，如 0x80）+ 生成真 R；运行时 `addAssetPath` 挂载 | ✅ |
| 资源**不自足**的 AAR（values 引用 appcompat/material 的 attr/style）：依赖的 `res/` 必须和库一起编进同一个资源包；`-I <宿主 APK>` 不能当资源依赖来源 | ✅（XUI 1.1.9，API 34） |
| 依赖资源版本要成代对齐：material 1.13 + appcompat 1.3.1 会撞 `styleable/SearchView`；`-R` overlay 链接依赖会连环失败 | ✅（XUI 1.1.9） |
| 运行时资源要挂**两个** AssetManager：Activity 的 + Application 的（库的静态 `ResUtils` 走后者），否则 `Resources$NotFoundException` | ✅（XUI 1.1.9，API 34） |
| 库的 `ContentProvider` 初始化不会进 iApp 的 manifest，要手动 `XxxLib.init(activity.getApplication())`；不初始化时 `getContext()` 抛 `ExceptionInInitializerError` | ✅（XUI 1.1.9） |
| UI 库的主题要用「屏幕型变体」（如 `XUITheme.Phone`），基类主题缺尺寸 attr，控件构造抛 `Failed to resolve attribute` | ✅（XUI 1.1.9，API 34） |
| 打包版要把 **dex 和资源包都**从 APK assets 释放到 `cacheDir`（只放 dex 会丢主题/资源）；dex 走只读流程，资源包普通文件即可 | ✅（XUI 1.1.9 打包，API 34） |
| 库的 setter 可能假设 AttributeSet 已初始化：`ButtonView.setSolidColor` 在 `(Context)` 构造后 NPE；`RippleView.setRippleColor` 吃的是颜色**资源 id** 不是 ARGB；先 `javap -c` 看字节码再调 | ✅（XUI 1.1.9） |
| `DexClassLoader` 父加载器：宿主可能自带同名库时给 `null`（iApp 自带混淆版 sora-editor）；编译类依赖 `androidx.*` 时给宿主 loader | ✅ |
| Android 14+/targetSdk≥34：动态加载的 dex 必须只读；先 `setReadOnly()` 再写，已有文件删了重建 | ✅（官方文档 + 实机） |
| 库 API 多时把 glue 编译进 dex 做桥接类，mjava 只用构造器 + `View.setTag/getTag` 交互 | ✅ |
| BeanShell 写不了「继承类」时：写 .java → javac → d8 成独立 dex，父加载器给宿主 | ✅ |
| ViewPager `onpageselected/onpagescrolled/onpagescrollstatechanged` 可用（适配器须编译类） | ✅ |
| AppBarLayout `onoffsetchanged` 可用；`st_vO` 是真实偏移量（px，负值） | ✅ |
| `i.loadjar` 只认 `apk/lib/`（VIP 付费入口），不要用 | ✅ |
| 新建工程最小集：`.project` + `AndroidManifest.xml` + `src/mian.iyu` + `icon.png`；`build.xml`/`sdk/` 由 iApp 首次打开生成 | ✅ |
| ppt 里写自定义类是真实实例（API 34：attached、hash 与视图树一致、`addView` 生效）；API 28 的“影子实例”旧结论按版本差异对待 ⚠ | ✅（API 34） |
| `type=` 写完整类名（含点号）必须在 `build.xml` 的 `<newControl>` 登记，否则设计器显示“未知”；短名不用 | ✅ |
| `TextInputLayout` 必须直接包含 `TextInputEditText`；子控件用 `til.getContext()`（ContextThemeWrapper），用 `activity` 会自绘成原生外观 | ✅（Context 对照） |
| ppt 建 `TextInputLayout` 实例是真的（attached / hash 与树一致 / addView 生效），但子控件固定 activity Context → 不修复时都是普通 EditText 外观；按 `md-components-guide.md` 的 `loading` 修复后可达到与 mjava 一致 | ✅（API 34，2026-10-27） |
| 短名 `TextInputLayout` 与全类名都解析为 `com.google.android.material.textfield.TextInputLayout`，不是 support 包 | ✅（API 34） |
| ppt 声明的 TIL 盒子默认不画：Material 把盒子贴成 EditText 的 background，ppt 子控件自带原生背景 → 跳过。修复挂 `loading`：从 `new TextInputEditText(til.getContext())` 抄字号/内边距，再 `setBackground(null)` + `updateEditTextBoxBackgroundIfNeeded()`；修完与 mjava 一致 | ✅（API 34，2026-10-27） |
| Material 1.13 内置 490 个类；常用 35 个控件 34 个可 `(Context)` 构造；20 个上屏验证全部成功（10 个空容器需内容），`Carousel` 被裁剪（无 `<init>`） | ✅（API 34，2026-10-27） |
| 独立探针页可新建任意 `.iyu` 作为开发入口；打包只认 `mian.iyu` | ✅ |
| 交互页状态放 `i.sss`（模块变量跨 call 必丢）；布局均分用 `height=0 + layout_weight=1` | ✅ |
| `.iApp` 备份：顶层直接是工程内容，无包名目录；同包名存在时导入失败 | ✅ |
| 打包 APK：versionCode = 100000 + versionint；打包后 `i.syso`(ygs) 无输出但 `android.util.Log` 正常、`VisualDesigner` 被裁 | ✅ |
| 界面事件 `downkey` 方向键可用（19/20/21/22）；`st_kC` 为键码，单条入口即可（已隔离验证） | ✅ |
| `i.fn("b")` 把模块加载进当前解释器；之后可直接调 `b_method()` | ✅ |
| 未加载先调用 → `Command not found`，**整个方法中断且 `catch` 不住** | ✅ |
| `i.d.f("b.mjava")` 仅开发模式可用；打包后 `i.d` 是 `xn0`，无 `f(String)` | ✅ |
| `i.call("mjava","b.method",Object[])` 可用；每次新建解释器；void 方法不要接返回值 | ✅ |
| 同名方法后加载覆盖；子模块方法应加前缀 | ✅ |
| `.iyu` 可以直接 `call` 任意模块，不必经过 facade | ✅ |
| 多模块源码可直接打包：交付用 `i.fn`，不合并 | ✅ |
| mjava `setOnTouchListener` 匿名接口可用，回调里能调同模块方法 | ✅ |
| `ObjectAnimator.ofFloat(view, prop, new float[]{…})` 可用；`postDelayed(匿名 Runnable)` 能收尾 | ✅ |
| `activity.getFilesDir()` + 文件读写持久化，杀进程后恢复 | ✅ |
| 动态视图用 `setTag("tile:"+idx)` 跨 `call` 找回；`bringToFront()` 管弹层层级 | ✅ |
| 应用内自检：`loading` 里跑纯逻辑用例，`i.syso` 输出 PASS/FAIL | ✅ |
| 事件参数统一以 `st_*` 注入（`st_vId`/`st_vW`/`st_pN`/`st_url`…）；写别的名字会退化成零参调用。`st_eX/st_eY` 仅在触摸类 DEX 里见到，运行期未验 ❓ | ✅/❓（DEX + 实测） |
| 绑 `shouldoverrideurlloading` 会跳过 iApp 默认跳转（内部 return true），要跳必须自己 `loadUrl` | ✅（DEX + 实测） |
| `i.call(语言, "模块.方法", Object[])`：首参是语言不是变量名；目标 void 时不能接返回值 | ✅（探针） |
| 行内水波纹要给 `RippleDrawable` 第三个参数传圆角遮罩，否则扩散成整圆 | ✅ |
| 图标用 `Canvas` + `Path` 现画（Bitmap → ImageView），不用 emoji/文字符号 | ✅ |
| 工程图标完全由根目录 `icon.png` 决定；打包为 `res/mipmap-*/img_iapp.png`（原样，无多密度切图） | ✅ |
| 1×1 半透明蓝像素占位图会被启动器拉成纯蓝方块；用 `scripts/make_icon.py` 生成真图标 | ✅ |
| 离线图标生成 `scripts/make_icon.py`：纯标准库，不联网、不依赖 Pillow | ✅ |
| 普通 View 的 `setRotationX/Y` + `setCameraDistance` 可做 3D 倾斜（无需自定义 View） | ✅（API 28） |
| 圆角 `GradientDrawable` 背景 + `setClipToOutline(true)` 会裁掉溢出的子 View | ✅ |
| `View.animate()`（ViewPropertyAnimator）可链式调用，`cancel()` 能打断 | ✅ |
| `View.setTag(int[]/float[])` 跨 call 存视图状态，强转能取回 | ✅ |
| 多个 `.iyu` 可各自作入口；`call(null,"mjava","mod.m","str")` 传字符串参数 | ✅ |
| Canvas 现画卡面（噪声、文字、金边）耗时随设备变化；绘制配方见 `references/recipes.md` | ✅（设备相关） |
| 两套独立雷电同跑会抢宿主机 5555，`emulator-5554` 可能静默指向后启动那台（投递前用 `getprop ro.build.version.sdk` 核对） | ✅ |
| Android 11+：`/sdcard/Android/data/<pkg>` 由 app 自身 mount namespace 的 bind mount 提供；FUSE 对其它进程一律拒绝（`is_app_accessible_path`），所以不能用 `su <uid>` 派生进程模拟 app 访问 | ✅（AOSP 源码 + API 34 实机） |
| Android 11+：可在 app 自己的 `Android/data/<pkg>` 下建指向共享存储（如 `Pictures`）的符号链接，app 自身可经链接读写；写入可经 vboxsf/共享目录落到宿主机（需相应存储权限，如 `MANAGE_EXTERNAL_STORAGE` appop） | ✅（API 34 + iApp 实机） |
| 共享目录（vboxsf）本身不支持符号链接：`ln -s` 报 `Function not implemented`，链接只能建在设备 ext4/FUSE 侧 | ✅（Android 14 模拟器） |
| 雷电实例序号 = `vms\leidianN`，宿主端口按序号走（0→5555，1→5557）；两套安装各自的 `leidian0` 会抢 5555，把第二套改名成 `leidian1` 可永久分开，无需脚本 | ✅（2026-10-26，安卓 9 + 安卓 14 各一台） |
| `MotionEvent` 的 `getActionMasked/getActionIndex/getPointerCount/getPointerId/findPointerIndex/getX(int)` 可用 | ✅（API 28） |
| `MotionEvent.getHistorySize(int)` 等带 pointerIndex 的重载**解析失败且杀进程**，`catch` 接不住；只用无参版本 | ✅（API 28） |
| 旋转屏幕会重建页面并重跑 `loading`；`loading` 里宽高=0，`loadingComplete` 有真实尺寸；`addOnLayoutChangeListener` 可用 | ✅（API 28） |
| `View.setTag(HashMap)` 跨 call 可取回，HashMap 里可装 Bitmap/Canvas/Paint | ✅（API 28） |
| `i.sss` 能存 `int[]` / `ArrayList`，跨 call 保持 | ✅（API 28） |
| 已上屏 Bitmap 改内容后 `invalidate()` 能刷新（`Bitmap + Canvas + ImageView` 路线成立）；具体耗时应按设备重测 | ✅（API 28） |
| 多 `.iyu` 用 `i.uigo("x.iyu")` 跳转：**每页一个 Activity 实例**（类名 `com.iapp.app.run.mian`，同进程同 task） | ✅（API 34） |
| 前进时序：旧页 `pause` → 新页 `loading → start → loadingComplete` → 旧页 `stop` | ✅（API 34） |
| 界面绑了 `downkey` 后**返回键被吞**：事件收到 `kc=4`，页面不弹出；要返回得在 mjava 里 `activity.finish()` | ✅（API 34） |
| 弹栈回旧页**复用原 Activity**：不重建、`loading` 不重跑，只走 `restart → start → resume`；被弹页 `stop → destroy` | ✅（API 34） |
| 未绑 `downkey` 时返回键走系统默认弹栈；绑了被吞后可在 mjava 里 `activity.finish()` 补回，效果与默认返回一致 | ✅（API 34） |
| `A→A` 自跳会再压一个同名 Activity 实例，旧实例状态原样保留（返回回到旧的那份） | ✅（API 34） |
| `uigo` flag 按 **Activity 组件** 匹配而非页面：`536870912` 是 no-op、`268435456` 与普通跳转无差异、`67108864` 只销毁当前页不清中间页；只有 `1073741824`（离开即销毁、返回跳过）真正可用 | ✅（API 34） |
| 页面传参用 `i.sss`；`uigo` 无参数通道。返回结果 = 子页写 `i.sss` + `finish()`，父页在 `resume` 读（无 ActivityResult 通道） | ✅（API 34） |
| mjava 里 `Class.forName("com.iapp.app.run.mian")` 抛 `ClassNotFoundException`（解释器看不见宿主类）；要 Class 只能用 `activity.getClass()` | ✅（API 34） |
| `uigo` 不设转场；`activity.overridePendingTransition(...)` 可接管动画 | ✅（API 34） |
| 打包 APK 里多页 `uigo` / `i.sss` 传参 / 返回结果 / 自建 Intent / 转场，与开发模式一致 | ✅（API 34） |
| 转场在 mjava 用 `i.lan(0~11)` 或 `activity.overridePendingTransition(...)`；`end()` 对应 mjava `activity.finish()`（0~11 为手册范围，已验 6） | ✅（API 34） |
| `addv` 是 yul 专属：`.iyu` 里 `addv(容器id,"x.iyu")` 可用；mjava `i.addv(...)` 返回 null；内嵌不触发目标页生命周期 | ✅（API 34） |
| 内嵌页 id 按"文件首次内嵌顺序"分 **10000 号段**（不是固定 +10000，不能硬编码）；内嵌页事件照常触发；要定位就原生遍历树 | ✅（API 34） |
| 多页 `addv` 只有 `DrawerLayout` 能用（第 2 个 child 改 gravity=START + 延后 400ms `openDrawer`）；`ViewPager`/`VerticalViewPager` 子控件进树但不渲染 | ✅（API 34） |
| yul 字面量 ≥2³⁰ 以 `Long` 传入 mjava：形参写 `int` 会 `Method … not found` 且**界面静默无反应**；数值形参用 `Object`+`Number` 接 | ✅（API 34） |

## 导航

- `references/methodology.md` — 探针方法与铁律
- `references/recipes.md` — 常用配方、持久化、自检、Canvas 卡面与 API 28 注意事项
- `references/animation-guide.md` — mjava 动画（ObjectAnimator / postDelayed / 3D 倾斜 / 输入锁）
- `scripts/` — 随包脚本（图标、建工程、APK/dex 扫描、编译类进 dex、AAR 转 dex：`build_aar_dex.py` 通用版 / `build_sora_dex.py` 专用版）
- `scripts/check_portable.py` — 分享前自检：禁止外部路径与作者机器路径
- `references/iapp-history.md` — 版本读数与已知会随版本变化项
- `references/iyu-whitelist.md` — iyu 只允许 call/addv
- `references/navigation-guide.md` — 多 `.iyu` 跳转 / 栈 / 返回（每页一个 Activity 实例、downkey 吞返回键、状态边界）
- `references/iyu-guide.md` — 界面文件结构
- `references/mjava-guide.md` — 模块写法与互调
- `references/modularization-guide.md` — 多模块拆分、`i.fn`、facade 规范
- `references/events-guide.md` — 事件类型与写法
- `references/iapp-i-reference.md` — `i` 对象成员与生命周期
- `references/external-library-guide.md` — JAR/AAR/DEX 装载、编译类进 dex、Android 14+ 只读要求
- `references/network-and-mirrors.md` — 国内网络抓文档/依赖：curl 落盘、可用镜像、离线转文本
- `references/iapp-internals.md` — 内部类、APK 结构、分析脚本
- `references/delivery-guide.md` — `.iApp` 备份、APK 打包、边界
- `references/project-structure.md` — 工程结构与新建工程
- `references/emulator-setup.md` — 模拟器环境参考：宿主工作区 ↔ Pictures 同步、雷电 9 实测工程根 `/data/media/0/iApp/ProjectApp`（仅供参考，以 iApp 设置为准）、安卓 14 软链、多开 adb 端口冲突
- `references/icon-guide.md` — 应用图标（来源、规格、离线生成）
- `references/builtin-controls.md` — 内置短名控件清单
- `references/style-guide.md` — ppt 与 mjava 的样式分层
- `references/md-components-guide.md` — Material 组件（ppt 声明 + TIL 修复配方 + 动态创建兜底）
- `references/material-components.md` — Material 组件选型规范与支持矩阵（优先全类名）
- `references/debugging.md` — 错误前缀与失败签名
- `references/pitfalls.md` — 踩过的坑
