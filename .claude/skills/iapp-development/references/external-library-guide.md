# 外部库（JAR / AAR / DEX）

版本前提：iApp 5.0.1013。基础装载结论在 API 28 实测；Android 14+ 的只读要求单独标注在各节。

## 基础结论

iApp **没有 Gradle、也没有内置 D8**，外部库必须在打包前自己转格式：

| 输入 | 处理 | 产物 |
|---|---|---|
| JAR | D8 转 dex | `xxx.dex` |
| AAR | 拆出 `classes.jar` 走 D8；`res/` 走 aapt2 | dex + resource apk |
| DEX | 直接用 | `xxx.dex` |

产物放 **`apk/assets/`**（`apk/lib/` 属 VIP/付费打包入口，不要用）。
运行时：`DexClassLoader` 加载代码，`AssetManager.addAssetPath` 挂资源，然后 import / 实例化。

## 目录

```
工程根/
└── apk/
    └── assets/
        ├── lib.dex          # D8 产物，直接放
        └── libres.apk       # aapt2 产物（可选，带资源时）
```

## 运行时加载

开发环境（工程在外部目录）可以直接按路径加载；打包后 assets 在 APK 内，需先释放到 `cacheDir`。两条路都写在下面。

```java
// 1) 开发环境：工程根 + apk/assets/lib.dex
java.lang.Class vd = activity.getClassLoader().loadClass("com.iapp.app.VisualDesigner");
String root = (String) vd.getField("a9").get(null);
String dex = root + "/apk/assets/lib.dex";

// 2) 打包环境：从 APK assets 释放到 cache
java.io.InputStream is = activity.getAssets().open("lib.dex");
java.io.File out = new java.io.File(activity.getCacheDir(), "lib.dex");
// 复制流到 out ...

dalvik.system.DexClassLoader dcl = new dalvik.system.DexClassLoader(
        dexOrOut, activity.getCacheDir().getAbsolutePath(), null, activity.getClassLoader());
java.lang.Class c = dcl.loadClass("com.example.Hello");
Object o = c.newInstance();
c.getMethod("inst", new java.lang.Class[]{}).invoke(o, new Object[]{});
c.getMethod("hi", new java.lang.Class[]{}).invoke(null, new Object[]{});
```

**父加载器二选一**：

- 库可能被宿主自带（编辑器、图片、图表、网络库等）→ 给 `null`，只用 boot classpath + 自己的 dex
- 库依赖 `androidx.*` 或宿主已有类型（编译类/适配器）→ 给 `activity.getClassLoader()`
- 不确定就先用 `dcl.loadClass(name)` 看 `sameClass` 和方法名是否正常，再决定

带资源时（✅ 实测，API 28）：

```java
// addAssetPath 是 hidden API，用反射；直接挂在宿主的 AssetManager 上即可，
// 不需要另建 Resources（资源包用独立包 ID，见下文「带资源的 AAR」）
Method add = android.content.res.AssetManager.class
        .getDeclaredMethod("addAssetPath", new Class[]{String.class});
add.setAccessible(true);
add.invoke(activity.getAssets(), new Object[]{resApkPath});
```

## 两条路径均已实测（✅）

| 环境 | dex 来源 | 结果 |
|---|---|---|
| 开发 | `<工程根>/apk/assets/b5lib.dex` | `cls=b5lib.Hello` / `jar-inst` / `jar-hit` |
| 打包 | `assets/b5lib.dex` → 释放到 cache → 加载 | 同上 |
| 打包（备选） | `getExternalFilesDir(null)/b5lib.jar` | 同上 |

打包产物里可见：

```
assets/lib.so
assets/b5lib.dex            (772 B)
assets/b5lib.dex.x86_64.flock
assets/oat/x86_64/b5lib.odex
assets/oat/x86_64/b5lib.vdex
assets/extra_conf1g.xml
```

说明 `apk/assets/` 下的文件会原样进入 APK 的 `assets/`，且 iApp 会顺带生成 odex/vdex。

## 打包环境（✅ 实测）

打包包会裁掉 `VisualDesigner`、也不包含工程 `files/`，所以打包后不能用工程根。已验证可用：

```java
java.io.File dir = activity.getExternalFilesDir(null);      // /sdcard/Android/data/<包名>/files
String dex = dir.getAbsolutePath() + "/b5lib.jar";         // dex 化后的 jar 或 dex 均可
dalvik.system.DexClassLoader dcl = new dalvik.system.DexClassLoader(
        dex, activity.getCacheDir().getAbsolutePath(), null, activity.getClassLoader());
```

屏幕读数：`exists=true`、`cls=b5lib.Hello`、`inst=jar-inst`、`hi=jar-hit`。

首发时把库释放到该目录（assets 复制或下载），再加载。

## 实测记录

- `i.loadjar` 只会去 `<工程根>/apk/lib/` 找，且要求 dex；该目录触发付费，弃用
- 纯 `.class` 的 jar 在 Android 上无法加载（DexPathList 为空）
- `Class.forName("com.iapp.app.VisualDesigner")` 在模块里不可用；要用 `activity.getClassLoader().loadClass(...)`
- 打包后 `VisualDesigner` 被裁掉、`files/` 不进 APK —— 打包环境必须走 assets 释放路径
- 用相对路径跳出工程根（如 `../../files/x.jar`）会被路径校验吃掉；库放 `files/` 时从工程根拼绝对路径

### 排查：库方法名像被混淆

先比“开发 vs 打包”；再用 `dcl.loadClass(name)` 看 `sameClass`、方法总数、类来自哪个 vdex。
如果方法名是 `A`/`A0`/`p3` 这种，多半是父加载器拿到了宿主自带的同名库（见 pitfalls #25）。

## 带资源的 AAR（✅ 已实测：sora-editor 0.21.1）

AAR 比 JAR 多两件事：`res/` 和「R 是 0」。两个都得处理，否则库在构造期就会崩。

### 为什么 R 是 0 会崩

AAR 的 `R.txt` 全是 `0x0`，真实 ID 由宿主 App 链接时才分配。库如果在**构造期**就用
`R.layout.*`，直接 `new` 会 `Resources$NotFoundException: Resource ID #0x0`。
sora-editor 就是这种：`new CodeEditor(ctx)` → `EditorTextActionPanel` → `inflate(layout)`。

### 处理链路

```
AAR ──classes.jar（剥掉自带 R*.class）──► d8 ──┐
    └─ res/ ──aapt2 compile──► compiled.zip     │
              ──aapt2 link -I <framework> ──► 资源apk + gen/R.java
                                              └─ javac R.java ──► r.jar ──► d8（同一个 dex）
```

| 步骤 | 坑 |
|---|---|
| `aapt2 link` | 需要 `-I` 框架资源。没有 android.jar 时可用设备上的 `/system/framework/framework-res.apk` |
| `--package-id` | **必须 ≥ 0x7f**；宿主占 0x7f，所以用 `0x80`，避免 ID 冲突 |
| `javac R.java` | JDK 25 默认产 class 69，d8 不认 → `--release 11` |
| `d8` | 不接受目录输入，`rclasses/` 先打成 jar；多输入文件可一次进同一个 dex |

产物两份，都放 `apk/assets/`：`xxx.dex`（代码）+ `xxx-res.apk`（资源）。

### 运行时

```java
// 1) 挂资源（hidden API，反射可用）
AssetManager am = activity.getAssets();
Method add = AssetManager.class.getDeclaredMethod("addAssetPath", new Class[]{String.class});
add.setAccessible(true);
add.invoke(am, new Object[]{resApkPath});

// 2) 加载代码：宿主可能自带同名库时给 null（见 pitfalls #25）
DexClassLoader dcl = new DexClassLoader(dexPath, cacheDir, null, null);
```

- 资源 ID 在 `0x80xxxxxx`，与宿主 `0x7fxxxxxx` 不冲突；`addAssetPath` 之后宿主
  `Resources` 就能解析这些 ID（不需要另建 `Resources` 对象）
- 库若强转 `ContextThemeWrapper`（sora 的 `CodeEditor` 会），要把
  `new ContextThemeWrapper(activity, android.R.style.Theme_DeviceDefault_Light)` 传给它
- 开发模式路径：`VisualDesigner` 字段 `a9` + `/apk/assets/`；打包后从 assets 复制到
  `cacheDir` 再加载（两条路都要，靠 try 兜底）

### 桥接类：库 API 多时不要从 mjava 反射调

mjava 是 BeanShell，按名字调库方法在「名字可信」时才成立；遇到重载族（`(float)->void`
有十来个）连按签名都不保险。做法是把 glue **编译进 dex**：

```java
// iappbridge.SoraHost（javac 编译，和库一起 d8）
public SoraHost(Context ctx, ViewGroup parent, String text) { … }  // 建 + 挂 + 设文本
public SoraHost(String text) { … }                                  // 换文本
public SoraHost(View sink, String op) { sink.setTag(compute(op)); } // 读数据走 tag
```

mjava 只用两种入口，都不受改名影响：

- **构造函数**：`cls.getConstructor(new Class[]{Context.class, ViewGroup.class, String.class})`
- **框架方法**：`sink.getTag()` / `sink.setTag(...)`（`View` 是框架类）

### 实例

`sora-editor 0.21.1` + `language-java` + `kotlin-stdlib 1.8.10` →
`sora.dex` 约 2.8 MB（1383 个类）+ `sora-res.apk` 约 18 KB。完整脚本见
`scripts/build_sora_dex.py`。

## 带资源的 AAR（二）：资源不自足、依赖 appcompat 的库（✅ XUI 1.1.9）

sora-editor 那种库的资源是**自足**的：`aapt2 link` 只喂它自己的 `res/` 就能过。
UI 库（XUI、各类 Widget 库）往往不是——它们的 `values.xml` 会引用宿主依赖的
`attr` 和 `style`，链接期就会整包失败。判据是链接报错里出现**别的库**的符号：

```
error: resource attr/colorAccent (aka com.xuexiang.xui:attr/colorAccent) not found.
error: resource style/Theme.AppCompat.Light.Dialog.Alert (...) not found.
error: resource style/Widget.AppCompat.Spinner (...) not found.
```

### 处理链路

| 输入 | 处理 |
|---|---|
| 库 AAR | `classes.jar` → d8；`res/` → aapt2 compile |
| 依赖 AAR（appcompat 等） | **只取 `res/`**，和库的 res 编进**同一个资源包** |
| 链接缺口 | 极少数符号确实没人提供 → `--stub-res` 补桩（见下） |
| 产物 | `xxx.dex` + `xxx-res.apk`（`--package-id 0x80`） |

依赖的 res 必须**同包**链接：直接丢给 `-I` 不行（见失败签名）。

### 失败签名（都实测过）

| 现象 | 含义 / 处理 |
|---|---|
| `resource attr/xxx not found`，而该 attr 是 appcompat/material 的 | 依赖资源没进包 → 把依赖 AAR 的 `res/` 一起 compile + link |
| `-I <宿主 APK>` 传进去仍然 not found（哪怕宿主 APK 里确实有这些资源） | **`-I` 只能当框架/引用用，不能当资源依赖来源**；同一个 `-I` 传进 149 MB 的宿主 APK 也没用 |
| `resource 'styleable/Xxx' has a conflicting value` | 依赖版本没对齐（material 1.13 与 appcompat 1.3.1 撞 `styleable/SearchView`）→ 选库当年的依赖代（appcompat 1.3.x ↔ material 1.4.x） |
| `-R` overlay 链接依赖 | 会连环失败：overlay 单元之间互相看不见 attr，`cardElevation`、`contentPadding` 全 not found。不要用 |
| `error: attribute alpha`（appcompat 1.3.1 的 `res/color/*`） | 它自己的 `R.txt` 里没有 `attr/alpha`，补 `<attr name="alpha" format="float"/>` |
| 只差一个 `Theme.Design.Light.BottomSheetDialog` | material 的样式没进包；补桩就够（UI 是近似的，真要精确就得把 material 也编进来，代价是连锁依赖 cardview/drawerlayout…） |

补桩文件放在单独的 `res/values/stub.xml`，用 `--stub-res <该 res 目录>` 传：

```xml
<resources>
    <style name="Theme.Design.Light.BottomSheetDialog" parent="Theme.AppCompat.Light.Dialog"/>
    <attr name="alpha" format="float"/>
</resources>
```

### 运行时：资源要挂在**两个** AssetManager 上

只挂 Activity 的 `getAssets()` 时，走「传入 Context」的控件正常，走库内静态工具
（`XUI.getContext().getResources()` 这类）的控件报 `Resources$NotFoundException`。
Application 的 AssetManager 是另一个实例，`addAssetPath` 对它是无效的。

```java
// 1) Activity 的资源（主题、?attr 解析）
add.invoke(activity.getAssets(), new Object[]{resApkPath});
// 2) Application 的资源（库的静态 ResUtils 走这里）——对象不同时再挂一次
android.content.res.AssetManager appAm = activity.getApplication().getAssets();
if (appAm != activity.getAssets()) {
    add.invoke(appAm, new Object[]{resApkPath});
}
```

验证探针：分别对 `activity.getResources()` 和 `activity.getApplication().getResources()`
跑 `getIdentifier(name, type, 包名)` + `getColor` / `getDimensionPixelSize`，两侧都能取到才算挂好。

### 库需要宿主注入 Application

不少库用 provider + `Application` 做全局初始化（XUI 的 `XUIInitProvider` 不会进 iApp 的 manifest），
不初始化时 `XUI.getContext()` 直接抛 `ExceptionInInitializerError`。iApp 里手动补：

```java
Class xc = dcl.loadClass("com.xuexiang.xui.XUI");
xc.getMethod("init", new Class[]{android.app.Application.class})
  .invoke(null, new Object[]{activity.getApplication()});
```

### 主题：别用「基类主题」，用它的屏幕型变体

XUI 的 `xui_actionbar_height` / `xui_btn_view_height` 这类尺寸 attr **只在 `XUITheme.Phone` /
`XUITheme.Tablet.*` 里定义**，光用 `XUITheme` 时控件构造抛
`Failed to resolve attribute at index N: TypedValue{t=0x2/d=0x80…}`。
用 `ContextThemeWrapper(activity, 屏幕型主题)` 包一层即可，不要 `activity.setTheme()`（会改宿主主题）。

```java
int tid = activity.getResources().getIdentifier("XUITheme.Phone", "style", "com.xuexiang.xui");
Context ctx = new ContextThemeWrapper(activity, tid);
```

### 打包模式：**资源包和 dex 都要**从 assets 释放

开发模式按工程根读 `apk/assets/`；打包后 `VisualDesigner` 被裁掉，两个产物都在 APK 的 assets 里，
必须一起释放到 `cacheDir` 再加载（只释放 dex 是最常见的漏项——dex 能加载，但主题/资源全丢）。

```java
// dex：Android 14+ 要求只读（开流 → setReadOnly → 写完再设一次）
File dex = new File(activity.getCacheDir(), "xxx.dex");
if (!dex.exists()) { /* 先开流、setReadOnly、写入、再 setReadOnly */ }
new DexClassLoader(dex.getAbsolutePath(), cacheDir, null, activity.getClassLoader());

// 资源包：普通文件即可，同样放 cacheDir，路径喂给 addAssetPath
File res = new File(activity.getCacheDir(), "xxx-res.apk");
```

- 一个 `setup()` 里两条路径：先试工程根（`VisualDesigner.a9`），失败再走 assets→cache；
  日志里明确打 `MODE=dev` / `MODE=packaged`，否则分不清跑的是哪条
- 打包后 `i.syso`（ygs）没有输出：`log()` 同时写 `android.util.Log.i(tag, …)` 和 `i.syso(...)`，
  开发/打包都能看

### 库的 setter 可能假设「属性已经初始化过」

用 `new Xxx(ctx)` 构造（不传 `AttributeSet`）时，库内部那些「从 attrs 里读出来的字段」是空的，
而 setter 不会防这个空。XUI 的两个实例：

| 调用 | 现象 | 正确姿势 |
|---|---|---|
| `ButtonView.setSolidColor(int)`（`(Context)` 构造后） | `NullPointerException: GradientDrawable.setColor on null`（私有字段 `gradientDrawable` 没初始化） | 自己 `new GradientDrawable()` + `setColor` + `setCornerRadius` + `setBackgroundDrawable` |
| `RippleView.setRippleColor(int)` | `Resources$NotFoundException: Resource ID #0xff299ee3`（把 ARGB 当资源 id 查） | 形参是**颜色资源 id**，传 `getIdentifier(name,"color",包名)` 的结果 |
| `SwitchIconView` 的图标 | 无公开 setter | 只能从 `drawable` 属性进；反射构造时给不了，就别指望它显示 |

排查方法：`javap -p -c` 看 setter 的字节码——它 `getfield` 哪个字段、调 `getResources().getColor(id)`
还是直接吃 int，一眼能看出来，比试错快。

### 实例（XUI 1.1.9）

- 依赖：calligraphy3 3.1.1 + viewpump 2.0.3（类依赖，XUI 的 `TitleBar` 等 `implements HasTypeface`）
  + appcompat 1.3.1（资源依赖）+ 上面那个 stub
- 产物：`xui.dex` 约 1.6 MB（1025 个类）+ `xui-res.apk` 约 730 KB
- 17 个控件构造并上屏全过：TitleBar / ShadowButton / ShadowTextView / ButtonView / SwitchIconView /
  SmoothCheckBox / CountDownButton / RippleView / AutoMoveTextView / ClearEditText / FlowTagLayout /
  RadiusImageView / CircleProgressView / HorizontalProgressView / MultipleStatusView /
  MaterialSearchView / TabSegment
- 打包脚本：`scripts/build_aar_dex.py`（通用版，支持多个 `--aar` / `--res-aar` / `--stub-res`）

坐标与命令（可直接照抄换版本号）：

```bash
# 依赖：XUI 在 jitpack；calligraphy3 / viewpump / appcompat 在 maven central 或 google
curl -L -o XUI-1.1.9.aar          https://jitpack.io/com/github/xuexiangjys/XUI/1.1.9/XUI-1.1.9.aar
curl -L -o calligraphy3-3.1.1.aar https://maven.aliyun.com/repository/central/io/github/inflationx/calligraphy3/3.1.1/calligraphy3-3.1.1.aar
curl -L -o viewpump-2.0.3.aar     https://maven.aliyun.com/repository/central/io/github/inflationx/viewpump/2.0.3/viewpump-2.0.3.aar
curl -L -o appcompat-1.3.1.aar    https://maven.aliyun.com/repository/google/androidx/appcompat/appcompat/1.3.1/appcompat-1.3.1.aar
adb pull /system/framework/framework-res.apk          # aapt2 link 的 -I

python scripts/build_aar_dex.py \
  --aar XUI-1.1.9.aar --aar calligraphy3-3.1.1.aar --aar viewpump-2.0.3.aar \
  --res-aar appcompat-1.3.1.aar --stub-res stub/res \
  --framework-res framework-res.apk \
  --manifest-package com.xuexiang.xui --name xui --out out/
```

### 接入骨架（mjava，开发 + 打包两条路径都在里面）

```java
// 产物放 <工程根>/apk/assets/<name>.dex 和 <name>-res.apk
public void log(String s) {
    try { android.util.Log.i("LIB", s); } catch (Throwable t) { }   // 打包后 ygs 是死的
    try { i.syso("LIB " + s); } catch (Throwable t) { }
}

public String copyAsset(String assetName, boolean readOnly) {          // 打包模式：assets → cache
    java.io.File out = new java.io.File(activity.getCacheDir(), assetName);
    try {
        if (out.exists() && out.length() > 0) { return out.getAbsolutePath(); }
        if (out.exists()) { out.setWritable(true); out.delete(); }
        java.io.FileOutputStream fo = new java.io.FileOutputStream(out);
        if (readOnly) { out.setReadOnly(); }                            // 先开流再设只读
        java.io.InputStream in = activity.getAssets().open(assetName);
        byte[] buf = new byte[8192];
        int n = in.read(buf);
        while (n > 0) { fo.write(buf, 0, n); n = in.read(buf); }
        in.close(); fo.close();
        if (readOnly) { out.setReadOnly(); }
        return out.getAbsolutePath();
    } catch (Throwable t) { log("ASSET-ERR " + assetName + " " + t); return null; }
}

public void mountOn(android.content.res.AssetManager am, String path, String tag) {
    try {
        java.lang.reflect.Method m = android.content.res.AssetManager.class
                .getDeclaredMethod("addAssetPath", new Class[]{String.class});
        m.setAccessible(true);
        log("RES[" + tag + "]=" + m.invoke(am, new Object[]{path}));
    } catch (Throwable t) { log("RES-ERR[" + tag + "] " + t); }
}

public boolean setup() {
    String dexPath = null, resPath = null;
    try {                                                              // 开发模式
        Class vd = activity.getClassLoader().loadClass("com.iapp.app.VisualDesigner");
        String root = (String) vd.getField("a9").get(null);
        dexPath = root + "/apk/assets/lib.dex";
        resPath = root + "/apk/assets/lib-res.apk";
        log("MODE=dev");
    } catch (Throwable t) {                                            // 打包模式
        resPath = copyAsset("lib-res.apk", false);
        dexPath = copyAsset("lib.dex", true);
        log("MODE=packaged");
    }
    mountOn(activity.getAssets(), resPath, "act");
    android.content.res.AssetManager appAm = activity.getApplication().getAssets();
    if (appAm != activity.getAssets()) { mountOn(appAm, resPath, "app"); }

    java.lang.ClassLoader cl = new dalvik.system.DexClassLoader(
            dexPath, activity.getCacheDir().getAbsolutePath(), null, activity.getClassLoader());
    i.sss("lib.dcl", cl);
    i.sss("lib.ctx", activity);                                        // 有主题需求就换 ContextThemeWrapper
    return true;
}
```

要点：`setup()` 里先试开发路径、失败再走 assets；`i.sss` 存 ClassLoader 供后续 call 复用
（模块级变量跨 call 必丢）；构造控件统一 `cl.loadClass(name).getConstructor(new Class[]{Context.class})`。

## 编译类进 dex（BeanShell 写不了「继承类」时的通用解）

BeanShell 只能实现接口，**不能继承类**（匿名类会中断事件）。遇到必须继承抽象类的场景
——`PagerAdapter`、`BaseAdapter`、`ItemDecoration` 之类——就自己写 Java 编成 dex：

```
Xxx.java ──javac（-classpath android.jar;依赖.jar）──► classes ──jar──► d8 --lib … ──► xxx.dex
```

```java
// iappbridge/VpAdapter.java
public class VpAdapter extends PagerAdapter {
    public VpAdapter(Context c) { … }          // 只要构造函数能被取到
    @Override public int getCount() { … }
}
```

```java
// mjava：用构造函数 + 反射拿实例（构造函数按参数类型匹配，不受改名影响）
DexClassLoader dcl = new DexClassLoader(dex, cacheDir, null, activity.getClassLoader());
Class a = dcl.loadClass("iappbridge.VpAdapter");
Object ad = a.getConstructor(new Class[]{Context.class}).newInstance(new Object[]{activity});
vp.setAdapter((PagerAdapter) ad);
```

要点：

- **父加载器给宿主**：这类子类依赖的 `androidx.*` 在宿主里，不能像 sora 那样给 `null`
- 自己的包名要有前缀（如 `iappbridge.`），避免和宿主同名类相撞（见 pitfalls #25）
- 方法名不会被混淆——混淆只发生在「拿到宿主自带类」的情况下
- 编译用 `--release 11`，d8 不接受目录输入；脚本见 `scripts/build_class_dex.py`
- 实测：ViewPager 用它跑通了三个翻页事件（见 `events-guide.md`）

## Android 14+ 的 DCL 只读要求（targetSdk ≥ 34）

官方行为变更原文（developer.android.com/about/versions/14/behavior-changes-14
「Safer dynamic code loading」）：

> If your app targets Android 14 (API level 34) or higher and uses Dynamic Code Loading
> (DCL), **all dynamically-loaded files must be marked as read-only**. Otherwise, the
> system throws an exception.

- 适用范围看 **targetSdk**：iApp 打包出来的 targetSdk 是 36，所以在 Android 14/15 设备上
  必然命中；Android 9 及更低没有这条限制
- 实机实测（Android 15）：`sora.dex` 放在 `getCacheDir()`（默认可写）→ 加载被系统拒绝
- 注意限制的是**文件可写**，不是目录。换 `getCodeCacheDir()` 不一定能绕过

### 正确写法（官方推荐顺序）

**先 `setReadOnly()`，再写内容** —— 目的是消除「写完到设只读之间」的竞态窗口：

```java
File d = new File(activity.getCacheDir(), "lib.dex");
if (d.exists()) {          // 已存在的文件官方建议删除重建
    d.setWritable(true);
    d.delete();
}
FileOutputStream fo = new FileOutputStream(d);
d.setReadOnly();           // 打开输出流之后、写入之前（fd 已打开，写入仍可继续）
byte[] buf = new byte[8192];
… fo.write(…) …
fo.close();
d.setReadOnly();           // 收尾再设一次，确保最终权限
```

- 反过来做（写完再 `setReadOnly`）不满足官方建议的顺序
- 已有只读文件时要先 `setWritable(true)` + `delete()`，否则 `FileOutputStream` 打不开
- 每次覆盖都要经过这套流程；**不要把只读文件直接复写成可写的**

### 实现建议

把三条路径统一走一个写 dex 的函数：开发模式（工程目录 → cache）、打包模式（assets → cache）、
以及覆盖已有文件。三条都经过上面的只读流程；Android 14 以下同样适用，没有副作用。

## 未决

- `addAssetPath` 在 **API 28 以下 / 高版本**（灰名单收紧后）的行为未测 ❓
- 资源包与宿主资源**同名资源**的覆盖优先级未测 ❓
