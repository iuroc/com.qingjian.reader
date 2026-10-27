# 内部结构（静态分析）

版本前提：iApp 5.0.1013（versionCode 127）。

## 关键类

| 类 | 作用 | 证据 |
|---|---|---|
| `com.iapp.app.Aid_javaCode` | 运行时 `i` 对象本体；390 个公开方法、12 个公开字段 | 反射 + dexdump |
| `com.iapp.app.Aid_jsCode` / `Aid_luaCode` | 其它语言的同构实现 | 静态：同样有静态 `ss_dim` |
| `bsh.Interpreter` 子类 `j6h` | `i.d`：每次 call 新建的 BeanShell 解释器；`f(String)` 导入 `.mjava` | 字节码 |
| `com.iapp.app.VisualDesigner` | 字段 `a9` = 当前工程根（开发环境）；打包后被裁掉 | 字节码 + 打包实测 |
| `qm` | 静态字段容器（307 字段、0 方法），`n` 是 HashMap | dexdump |
| `fj` | 文件/资源工具：`a` 读源码、`s` 建 DexClassLoader | 字节码 |

## 宿主自带的第三方库（重要）

宿主的 APK **自身就打包了一份混淆过的 sora-editor**（IDE 自己的代码编辑器用的）：

```
grep -c rosemoe /data/app/com.iapp.app-*/oat/x86_64/base.vdex   → 15
崩溃栈里可见：io.github.rosemoe.sora.widget.CodeEditor.p3
```

后果：工程里再引入官方 sora 时，`DexClassLoader` 若以宿主 loader 为父，
**父优先委派会拿到宿主那份混淆版**，方法名全是 `A`/`A0`/`p3`，
按名字反射全 miss、按签名匹配错位、编译桥接类直接 SIGSEGV。

对策：`new DexClassLoader(dex, cacheDir, null, null)`（父加载器给 `null`）。

意义不止于 sora：**任何可能被宿主内置的库**（编辑器、图片加载、图表、网络库）
都要考虑这条。开发模式出现「方法名短得像混淆过」时，先查宿主 vdex。

## 字段

`Aid_javaCode` 12 个公开字段：`a`(HashMap)、`b`(Activity)、`c`(Context)、`d`(j6h)、`e`(FrameLayout)、`f`(int)、`g`(WebChromeClient.CustomViewCallback)、`h`(Handler)、`i`(static HashMap)、`j`(static int)、`alertdialog`(static AlertDialog)、`ss_dim`(static HashMap，默认 null)；用途见 `iapp-i-reference.md`。

`ss_dim` 在 `Aid_javaCode` / `Aid_jsCode` / `Aid_luaCode` 中都是 **static**。

## 打包产物结构（APK）

```
assets/lib.so             # 运行库
assets/b5lib.dex          # 工程 apk/assets 下的自定义文件（若有）
assets/oat/x86_64/*.odex  # 打包时生成
assets/extra_conf1g.xml
classes.dex
lib/arm64-v8a/libygsiyu.so
lib/arm64-v8a/libluajava.so
```

工程源码（`.iyu`/`.mjava`）不以明文出现在 APK 中。

## 分析脚本

随包脚本（`scripts/`）：
- `dex_classes.py` 列类与成员数
- `dex_api_dump.py` 导公开 API
- `dex_body.py` 导方法字节码
- `dex_map_fields.py` 按字段名反查类

依赖 build-tools 的 `dexdump`：默认从 `PATH` 找，找不到时用 `DEXDUMP` 环境变量指定完整路径。

## 查一个方法读写了哪些字段

| 手头有 | 手段 | 看什么 |
|---|---|---|
| 源码 | 读代码 / IDE Find Usages / `grep` | 直接看字段名 |
| `.class` / `.jar` | `javap -c -p <类>` | `getfield` / `putfield` / `getstatic` / `putstatic` |
| `.dex` / `.apk` | `dexdump -d`，或 `python scripts/dex_body.py <apk> <类> <方法>` | `iget` / `iput` / `sget` / `sput`（含 `-object` 变体），字段引用形如 `Lcom/x/Y;.f:I` |
| 混淆过 | 先 `dex_map_fields.py` 把字段名映射到类，再回反汇编 | 字段名与所属类 |
| 反射 / 动态代理 / JNI | 运行时探针：反射读字段前后值，或调用前后 `i.syso` 记录 | 值变化；静态看不到的路径 |

注意：方法可能调其它方法，字段访问要沿调用图追；`dexdump -d` 里的 `invoke-*` 给出下一跳。

## 搜不到某个类，能判不存在吗

不能直接判。先确认覆盖：

- APK 里**所有** dex 都搜过：`classes*.dex`、`assets/**/*.dex`；multidex 别只搜 `classes.dex`。
- 类可能来自 framework、宿主 APK、`DexClassLoader` 动态加载、运行时字节码生成，不在当前 artifact 的 dex 里。
- 混淆/改名、内部类 `Outer$Inner`、描述符格式 `Lpkg/Class;` 与点号名都要试。
- 运行时探针要用**正确的 ClassLoader** `loadClass` 并接 `ClassNotFoundException`；BeanShell 解释器看不见宿主类，不能拿 `Class.forName` 直接判。

只有覆盖完这些、且没有动态加载路径，“这个 artifact 里没有”才是可靠负结论；“运行时不存在”还要再排除动态加载与生成。
