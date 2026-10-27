# 坑

## 1. 内存覆盖磁盘

iApp 编辑器以内存中的工程为准。点运行 / 保存 / 退出保存都会把旧内存写回磁盘。

**做法**：外部改源码前先 `am force-stop com.iapp.app`（或人在 iApp 里关掉工程），push 完再重新打开。

## 2. bind mount 对应用不可见（Android 9，sdcardfs）

- 挂到 `/data/media/0/...`：被 sdcardfs 挡住，`/storage/emulated/0/...` 视图是空的
- 挂到 `/storage/emulated/0/...`：shell 能看，**iApp 进程看不到**
  - 应用 namespace 由 zygote 派生，后加的挂载不传播
  - 验证方法：`grep <目标目录> /proc/<iApp pid>/mountinfo`；或 `cat /proc/<pid>/root/...`

**做法**：有共享目录/同步盘就改共享目录；没有或核不上 md5 时再用 `adb push`。不要用 bind mount。

## 3. Git Bash 改写路径

`adb shell ls /storage/...` 会被 MSYS 改写成 `C:/Program Files/Git/storage/...`（Git for Windows 的默认安装盘；装在别处按实际）。

**做法**：`export MSYS_NO_PATHCONV=1`。

## 4. su 参数被拆散

`adb shell su -c "ls -la /data"` 到了设备上引号丢失，`su` 把 `-la` 当自己的参数。

**做法**：整段用单引号包住 `adb shell 'su -c "ls -la /data"'`；或直接 `adb root`。

## 5. 入口名

入口固定 `src/mian.iyu`（min 不是 main）。任务书里偶尔写成 `main.iyu`，以实测为准。

## 6. 状态放错地方

- `i.ss` 的底层 HashMap 默认是 null，一读一写就 NPE——不要当存储用。
- `i.d`（BeanShell 解释器）**每次 call 都是新的**，不能拿来跨 call 存变量。
- `i.sss` 只在**同一次运行**内跨 call 有效；重新运行就清零（同进程也一样）。
- 要跨运行持久化，用文件（工程 `files/` 或外部存储），不要依赖内存对象。

## 7. 自定义类控件（Material / androidx）

- **依赖子控件 Context/背景的组件（典型是 `TextInputLayout`）在 ppt 里外观会退化**：子控件由 iApp 用 activity Context 构造，拿不到 `til.getContext()` 那层 Material 主题覆盖 → 输入框看起来是普通 EditText（API 34 实测，2026-10-27）。Button / Card / Chip 等不依赖子控件 Context 的组件不受影响
- ppt 建的实例本身**是真的**：`findViewById` 返回的就是屏幕上那个（hash 与视图树一致）、`attached=true`、`addView` 生效。API 28 的“影子实例”旧结论按版本差异对待 ⚠
- **TIL 盒子默认不画**：Material 1.13 把盒子贴成 EditText 的 background，ppt 子控件自带原生背景 → 被跳过（`boxBackgroundApplied=false`）。修复必须挂在 `loading`（`loadingComplete` 会让首帧先画出无盒子的页面）：从 `new TextInputEditText(til.getContext())` 抄回字号/内边距，再 `et.setBackground(null)` + `til.updateEditTextBoxBackgroundIfNeeded()`
- 修复后与 mjava 动态创建一致；完整配方见 `md-components-guide.md` 的「ppt 声明的 TIL：盒子默认不画（修复配方）」
- `TextInputLayout` 内部那层 `FrameLayout` 是它自己的 `inputFrame`（内含 `StartCompoundLayout`/`EndCompoundLayout`），**不是 iApp 套的**；旧记录归因错误
- 组合控件：**ppt 里声明父容器与子控件**（这是默认做法，实例真实可写）；TIL 按下面的 `loading` 配方修复，其它组件只补运行期内容。不要为了“保险”改成 mjava 整页动态创建
- **写完整类名（`type=` 含点号）的那一刻就登记**：`build.xml` 的 `<newControl>`，子项标签是 `itme`。设计器显示“未知”说明已经漏了；新建工程的登记不继承
- **设计器崩溃（根因：`SearchBar` + 序列化器空 tag）**：`SearchBar` 写进 ppt 后，点运行/保存/切代码页等**触发设计器自动保存**时抛 `NullPointerException: Attempt to read from null array`（`VisualDesigner.T0:54`，2026-10-27），iApp 进程被杀
  - 根因（R8 反编译）：`T0` 把 `view.getTag()` 当 `Object[]` 读（约定 `[type,ppt,event]`）；`id >= 1` 的控件**跳过 tag 空检查**，直接 `aget-object` → NPE。`SearchBar` 构造里 inflate `mtrl_search_bar`，内部子 View 带资源 id 但没有 tag → 递归到它时崩
  - 触发条件是**保存/序列化动作**（`S0`→`R0`→`T0`），不是“打开设计器”；`S0` 有 2 秒防抖（`D8` 在 Activity 构造时赋值），刚重开时第一次保存会被跳过，看起来像“第一次正常、之后崩”
  - 与 `build.xml` 登记无关：`type` 含点号时 `if0.q` 直接反射实例化；只登记不声明连续 3 次正常，不登记只声明仍崩
  - 做法：**不要 ppt 声明 `SearchBar`**，改 mjava 动态创建（运行期不经过序列化器）；动态创建的控件也不用登记
  - 原清单里的 `TabLayout`（短名/全类名/登记与否）、`ChipGroup`（含 `Chip` 子项）、`MaterialDivider` 已实测单独 ppt 声明**不崩**，全部排除
  - 未登记的完整类名一般只让组件树显示“未知”（`TabLayout` 探针工程能开、无报错）；`SearchBar` 显示“未知”也照样会崩
  - 泛化：任何“构造时自建带资源 id 子 View”的第三方控件都可能触发同一缺陷，不止 `SearchBar`

## 8. BeanShell 解析不到某些继承方法

`Error in method invocation: Method isSingleLine() not found in class 'com.google.android.material.textfield.TextInputEditText'`

- 该方法在 TextView 上是公开的，但 BeanShell 解析失败，**整个方法会中断**
- 处理：换等价属性（如读 inputType / lineCount），或用反射调用；不要把关键流程建立在这种调用上

### 8.1 重载解析失败会杀进程（API 28 实测）

`MotionEvent.getHistorySize(int)` / `getHistoricalX(int,int)` 这类带 pointerIndex 的重载在 BeanShell 里找不到；
无参 / 单参版本反而能用。在 `OnTouchListener` 回调里调用它时：

```
E/AndroidRuntime: FATAL EXCEPTION: main
java.lang.reflect.UndeclaredThrowableException
  at $Proxy3.onTouch(...)
Caused by: Error in method invocation: Method getHistorySize( int ) not found ...
W/System.err: call killProcess callstack! pid=3039
```

- **`catch (Throwable)` 接不住**，异常穿透匿名接口代理，iApp 直接 killProcess
- 同一回调里排在它前面的 `getActionMasked/getActionIndex/getPointerId/findPointerIndex/getX(int)` 都正常
- 做法：只用无参 `getHistorySize()`（对应 pointer 0）；要按指针取历史点就另想办法
- API 28 实测（2026-10-26）
- 同类签名：在匿名 `Runnable` / 接口回调里对 **null 数组取下标**（如 `((Object[]) view.getTag())[0]`），
  BeanShell 抛 `Typed variable declaration : Not an array`，穿成 `UndeclaredThrowableException` 并杀进程，
  `catch(Throwable)` 接不住（2026-10-27，API 34）

## 9. 把短类名当成“去包名”

`type="Switch"` 设计器显示“未知”——`Switch` 不在内置短名表里，运行时可能正常，但设计器不认识。

- 短名清单以 `builtin-controls.md` 为准，不要维护第二份
- 其它类写完整类名（如 `android.widget.Switch`）并在 `build.xml` 的 `<newControl>` 登记
- 判据：设计器显示“未知”就是短名不存在或未登记

## 10. 竖向布局“堆在顶部”，不铺满

根 `height=-1` 但子行都写 `height=-2` 时，内容只占顶部，底部留白。

要均分剩余高度：

```xml
<!-- 行 -->
<ppt>height=0
layout_weight=1</ppt>

<!-- 行内按钮 -->
<ppt>width=0
height=-1
layout_weight=1</ppt>
```

## 11. DrawerLayout 必须精确尺寸

`width=-2 height=-2` 会让整个页面闪退：

```
java.lang.IllegalArgumentException: DrawerLayout must be measured with MeasureSpec.EXACTLY.
```

给固定 dp（如 `300dp`）或精确的 match 尺寸，并单独隔离测试。

## 12. mjava 里按 `android.widget.*` 猜导入，类根本不存在

`SwipeRefreshLayout` 的正确类是 `androidx.swiperefreshlayout.widget.SwipeRefreshLayout`，写成 `android.widget.SwipeRefreshLayout` 直接：

```
Typed variable declaration : Class: SwipeRefreshLayout not found in namespace : at Line: 19
```

- 短名表里的“实际类”就是导入路径，照抄；GifView→`pl.droidsonroids.gif.GifImageView`、TabLayout/RoundImageView→`com.iapp.app.*` 同理
- 这类报错是**运行期**的：同一函数里它之后的代码全部不执行，但它之前的代码已经生效（`setProgress` 已经触发过回调）
- 所以初始化函数要**按块 try/catch**，一块写坏不能拖累其它控件

## 13. 绑了 `shouldoverrideurlloading`，WebView 链接就不跳了

`run/mian$i0.shouldOverrideUrlLoading` 的逻辑：

- **没绑**这个事件 → iApp 默认处理：`http/https/rtsp/ftp` 在 WebView 内 `loadUrl`，其它 scheme 走 `ACTION_VIEW`
- **绑了** → 执行完 yul 代码**直接 return true**，默认跳转被跳过，`ondownloadstart` 也等不到

所以“链接没反应”不是 HTML 的问题，是自己绑了事件却没写跳转。要跳就在事件里自己 `loadUrl`：

```xml
<eventItme type="shouldoverrideurlloading">call(null, "mjava", "br.override", st_url)</eventItme>
```

另外一个坑：参数变量必须写 `st_url`。写 `url` 会变成未定义变量，调用退化为零参：

```
JavaErr：Method override() not found in bsh scripted object: global
```

## 14. `i.call` 的三个坑

```java
i.call("mjava", "pick.show", new Object[]{…});
```

- **第一个参数是语言**，不是变量名：传 `null` → `NullPointerException: … String.equals`；传 `""` → 静默不执行、不报错
- **第二个参数必须带模块名**（`"pick.show"`），只写方法名会拼出 `.mjava`
- **目标是 void 方法时不要赋值**：`Object r = i.call(...)` → `Typed variable declaration : Void initializer.`，而且**整个方法立刻中止**，后面的语句全不执行

## 15. `String.valueOf(null)` 在 BeanShell 里会炸

```
NullPointerException: Attempt to get length of null array
    at java.lang.StringFactory.newStringFromChars
    at java.lang.String.valueOf(String.java:2912)
    at bsh.Reflect.invokeStaticMethod
```

BeanShell 解析 `String.valueOf(x)` 时，如果 `x` 是 `null`，会选到 `valueOf(char[])` 重载，对空数组取长度直接 NPE。

最常见的触发点：`String.valueOf(i.sss("key"))`，而该 key 还没赋值。

```java
// 错误
String v = String.valueOf(i.sss("pick.sel"));
// 正确
Object o = i.sss("pick.sel");
String v = (o == null) ? "" : String.valueOf(o);
```

建议每个模块都放一个 `str(Object)` 小工具，凡是可能为 null 的值都走它。

## 16. 日志过滤

只抓 `ygs` 与 `System.err`：

```
adb logcat -d -v time 'ygs:V' 'System.err:V' '*:S'
```

`System.err` 里的 `Toast callstack!` 是 iApp 自己打印提示用的，不是错误。

退出运行预览时还会出现一组：

```
java.lang.IllegalArgumentException: View=... not attached to window manager
  at com.iapp.app.VisualDesigner$i1.handleMessage
```

这是 iApp 拆预览悬浮窗的噪音，与本工程代码无关，不要当 crash 查。

## 17. `downkey` 不传 `st_kC` 就不知道按了哪个键

`downkey/upkey` 事件体有三个内置变量：`st_kC`（键码）、`st_eA`（动作）、`st_eR`（重复计数）。
只写 `call(null,"mjava","x.y")` 也会触发，但 mjava 拿不到键码。

```xml
<eventItme type="downkey">call(null, "mjava", "game.keyCode", st_kC)</eventItme>
```

同时挂 `setOnKeyListener` 会双触发，需要按 `(键码, 120ms)` 去抖。

## 18. 动画收尾不要用 `AnimatorListenerAdapter`

它是**抽象类**，BeanShell 只能匿名实现接口，写 `new AnimatorListenerAdapter(){...}` 会让模块失效。
用 `view.postDelayed(new Runnable(){ public void run(){ nextStep(); } }, 120)` 收尾。
详见 `animation-guide.md`。

## 19. 动态视图跨 `call` 会“丢”

模块变量在每次 `call` 都重置，`ArrayList<View>` 这类字段存不住。
动态加的视图用 `setTag("tile:"+idx)`，之后遍历 `getChildCount()/getChildAt(k)` 按 tag 找。

## 20. `getFilesDir()` 是多工程共用的

开发模式下它指向 iApp 宿主 `com.iapp.app` 的私有目录，不是当前工程目录；
打包后是打包应用自己的私有目录。
开发模式存档文件名要带工程前缀（如 `game2048.save`），否则不同工程会互相覆盖；
反例：把存档写成 `save.txt`，两个工程一起跑就串了。

## 21. 1×1 占位图 = 纯蓝方块

早期 `create_project.py` 写的 70 字节 `icon.png` 注释是“透明”，实际像素是
RGBA `00 00 FF 7F`（半透明蓝）。启动器把它拉满整个图标，所有工程都是蓝方块。

- 判据：`icon.png` 只有几十字节、尺寸 1×1
- 做法：用 `scripts/make_icon.py` 生成 512×512 真图标
- iApp 打包时把 `icon.png` 原样塞进 `res/mipmap-*/img_iapp.png`，没有多密度切图
- 桌面图标有缓存，换图后要重新打包安装才看得到

详见 `icon-guide.md`。

## 22. 跨模块调用前没 `i.fn`

新一次 `call` 是新的 BeanShell 解释器，上一次加载的模块**不在了**。
在 `importAll()` 之前调用 `u_st()` 这类子模块方法：

```
Command not found: u_st( java.lang.String ) : at Line: 60 ...
Called from method: layout
```

**整个方法中断，`catch(Throwable)` 接不住**，后面的渲染/逻辑都不执行。

做法：

- facade 的每个 public 入口**第一行** `importAll()`
- `importAll()` 里 `i.fn("模块名")`（不带 `.mjava`）
- 用模块级 `G_IMPORTED` 标记“本次 call 已加载”
- 不要先做 `if (u_st(...))` 再加载
- 详见 `modularization-guide.md`

## 23. `i.d.f` 只在开发模式可用，交付用 `i.fn`

开发模式 `i.d.f("x.mjava")` 能按文件名导入；打包 APK 后：

```
Method f( java.lang.String ) not found in class'xn0'
```

- `i.d` 变成混淆类 `xn0`，`f` 是 **Context 字段**，不是导入方法
- `i.call` 不是不能用：正确顺序是 `i.call("mjava","x.method",Object[])`；
  它每次新建解释器，跨模块加载优先 `i.fn`
- **正确做法**：`i.fn("x")`，源码直接打包，不合并

```java
i.fn("b");
b_hello();
```

- 详见 `modularization-guide.md`

## 24. 外部 AAR 的 R 全是 0，构造里就要资源 → 必须自己链资源

AAR 里的 `R.txt` 全是 `0x0`（真实 ID 在宿主 App 链接时才分配）。如果库在**构造期**
就用 `R.layout.*`（sora-editor 的 `CodeEditor` 构造 → `EditorTextActionWindow` →
`inflate(R.layout.text_compose_panel)`），不链资源直接 `new` 必崩：

```
Resources$NotFoundException: Resource ID #0x0
```

做法（完整脚本见 `scripts/build_sora_dex.py`）：

1. `aapt2 compile --dir res -o compiled.zip`
2. `aapt2 link -I <framework-res.apk> --package-id 0x80 --java gen …`
   - **包 ID 必须 ≥ 0x7f**（aapt2 拒绝 0x7e），宿主是 0x7f，所以用 0x80
   - 没有 `android.jar` 时，可以用设备上 pull 的
     `/system/framework/framework-res.apk` 当 `-I`（实测可用）
3. `javac --release 11` 编译生成的 `R.java`，打进 dex（**先剥掉 AAR 自带的 `R*.class`**）
4. 运行时 `activity.getAssets().addAssetPath(资源apk路径)`（反射，hidden API，实测可用）

## 25. `DexClassLoader` 父加载器：宿主自带同名库时给 `null`

```java
// ❌ 宿主 APK 里若自带同名类，父优先委派会先命中它
new DexClassLoader(dex, cacheDir, null, activity.getClassLoader());
// ✅ 只用 boot classpath + 自己的 dex
new DexClassLoader(dex, cacheDir, null, null);
```

反过来，编译类依赖 `androidx.*` 或宿主已有类型时，父加载器要给宿主 loader（见 `external-library-guide.md` 的「编译类进 dex」）。

实测：宿主 `com.iapp.app` 的 APK **自带一份混淆过的 sora-editor**
（`base.vdex` 里能看到 `io.github.rosemoe.sora.widget.CodeEditor.p3`）。
父加载器给宿主时，`loadClass("io.github.rosemoe.sora.widget.CodeEditor")` 拿到的是宿主那份：

| 现象 | 说明 |
|---|---|
| 方法表完整（共 953、声明 325），但按名字一个都查不到 | 自有方法名被混淆成 `A`/`A0`/`p3` 之类 |
| 继承自框架的方法名正常（`getTextDirection` 等） | 只有该类**声明**的方法被改名 |
| `Class.getMethod("getText")` → `NoSuchMethodException` | 同上 |
| 按签名能找到并调用，但行为怪（字号乱、语言没设上） | 命中的是混淆版同签名方法 |
| 编译进 dex 的桥接类直接 SIGSEGV | 方法 id 解析到语义不同的混淆方法 |

打包版没有宿主干扰，所以同一份 dex 一切正常——**排查时先比较「开发 vs 打包」**。
自检写法：`ce.getDeclaredMethod("setTextSizePx", new Class[]{Float.TYPE})` 能找到 = 用的是自己的。

## 26. 重载族不能只靠「参数类型 + 返回类型」定位

方法名不可信时（见 #23 之外的场景），按签名匹配看似可行，但对同签名族会错位：

- `(float) -> void`：`setTextSize` / `setTextSizePx` / `setTextScaleX` / `setDividerWidth` …
- `(boolean) -> void`：`setEditable` / `setWordwrap` / `setLineNumberEnabled` / 一堆 `set*Enabled`

命中哪个取决于方法表顺序，结果就是「文本进去了但字号失控、语言没设上」。
**正解：把 glue 编译成 dex 里的桥接类**，编译期解析方法引用；mjava 只跟桥接类打交道，
而且只用两种入口——构造函数（按参数类型取）和框架方法（`View.setTag` / `View.getTag`）。

## 27. Android 14+：动态加载的 dex 必须是只读文件

targetSdk ≥ 34 的应用在 Android 14（API 34）及以上，`DexClassLoader` 加载的
dex/jar/apk **必须是只读文件**，否则系统直接抛异常（行为变更「Safer dynamic code loading」）。
iApp 打包的 targetSdk 是 36，所以在 Android 14/15 实机上必踩；Android 9 上没这条限制，
**本地测不出来**。

典型触发：把 dex 复制到 `getCacheDir()`（默认可写）后直接加载。

```java
// ❌ 写完就加载：文件仍可写
FileOutputStream fo = new FileOutputStream(d);
fo.write(bytes); fo.close();
new DexClassLoader(d.getAbsolutePath(), …);

// ✅ 官方顺序：打开输出流 → setReadOnly() → 写 → 关闭 → 再设一次
if (d.exists()) { d.setWritable(true); d.delete(); }
FileOutputStream fo = new FileOutputStream(d);
d.setReadOnly();
fo.write(bytes); fo.close();
d.setReadOnly();
new DexClassLoader(d.getAbsolutePath(), …);
```

要点：

- 限制的是「文件可写」，**不是目录**；换 `getCodeCacheDir()` 不一定能绕过
- 已存在的只读文件必须先 `setWritable(true)` + `delete()` 再重建，否则写不进去
- 官方推荐「先设只读再写」，而不是写完再改权限（消除竞态）
- 同一个 dex 既要被开发模式又要被打包模式加载时，两条路都要经过这套流程

## 28. 多开模拟器：`emulator-5554` 会指向错误的设备

两套**独立安装**的雷电（如 `LDPlayer9` + `LDPlayer14`）各自只有 `index=0`，VM NAT 规则都是
`adb,tcp,,5555,,5555`，同时运行就抢宿主机 5555——**后启动的那台赢**。

实测（LDPlayer 9.5.42.0 / 14.0.32.1，2026-10-26）：

- LD14 启动前 `adb shell` 读到 Android 9；LD14 启动后，连 LDPlayer9 自带的 `ldconsole adb` 都读到 Android 14
- `adb devices` 里 `emulator-5554` 和 `127.0.0.1:5555` 可能是同一台 Android 14，名字却不提示
- 危险点：`adb push` / `pm install` 静默落到错版本上，以为是 API 28 其实是 API 34

**做法**：

- 每次投递前先核对：`adb -s <serial> shell getprop ro.build.version.sdk`
- 需要同时用两台：运行时 `VBoxManage controlvm <vm-uuid> natpf1 delete adb` 再用
  `natpf1 "adb,tcp,,5557,,5555"` 改宿主端口（重启失效，需重加）
- 两台同时开时不要依赖 `emulator-5554` 这个名字，统一用 `127.0.0.1:<端口>` 显式指定
- 只开一台时，先启动你要用的那台，再启动另一台就会把 5555 抢走
