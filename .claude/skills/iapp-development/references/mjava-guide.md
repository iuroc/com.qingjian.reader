# mjava 模块

`.mjava` 文件放在工程 `src/` 下，内容是 **Java 语法的方法**，不需要 `class` 外壳，也不写 `package`。

**执行方式：BeanShell 解释**（✅ 实测，见错误原文）。所以「Java 语法」不等于「javac 语义」，很多 javac 能过的写法在这里是解析错误，且是**整个模块全有或全无**。

## 最小可用模块

```java
import android.widget.TextView;

public void bind() {
    syso("ok");
    TextView tv = (TextView) activity.findViewById(2);
    tv.setText("Hello from mjava");
}
```

✅ 实测（iApp 5.0.1013 / Android 9）：页面文字变为 `Hello from mjava`，日志出现 `ok`。

## import 优先

模块顶部可以正常写 `import`，**默认用它，不要满屏全限定名**：

```java
import android.view.View;
import android.widget.TextView;
```

- 文件顶部 `import a.b.C;` ✅
- 方法内 `imports("android.view.View")` ✅（用于动态导入）
- 直接用全限定名 ✅（但不推荐，可读性差）
- **漏 import 的签名**：`Class: View not found in namespace : at Line: N` —— 整个模块失效。
  常见于只写了方法、没写 import 的模块；`importAll()` 只负责加载子模块，**不能替代 import**
- **反射加载应用内类**：用 `activity.getClassLoader().loadClass(name)`；
  `Class.forName(name)` 在 BeanShell 里看不到应用类（实测 35 个 Material 类全部 lookup-fail）
- **全限定名不总是能用**：`org.json.JSONObject` 被解析成「类 `org` 的静态字段 `json`」，
  报 `No static field or inner class: json of class org` ✅（API 34，2026-10-27）。
  `org.json.*` 必须 `import org.json.JSONObject;` / `import org.json.JSONArray;` 后写短名。

## 两个默认对象

| 变量 | 是什么 | 级别 |
|---|---|---|
| `activity` | 当前 Activity | ✅ |
| `i` | iApp 运行时对象（`i.gvs` / `i.ss` / `i.sss` …） | ✅ |

- `activity.findViewById(2)` 与 `i.gvs(2)` **返回同一个实例**（`==` 为 true）✅
- **裸 `findViewById(2)` 不存在**，报错：`Command not found: findViewById( int )` ✅
- 控件 id 就是 `.iyu` 里 `<View id="2">` 的数值
- 两者都查**当前 Activity** 的视图树；跨页（`uigo` 每页一个 Activity）或 `addv` 内嵌页时 `i.b` 与 `activity` 是否一致未单独验证，取当前页控件用 `activity.findViewById` 最稳

## 作用域

- 模块级变量（文件顶层 `int cnt = 0;`）**不跨 call 保留**：连续两次调用都读到初值 ✅
- 状态要跨调用保存，用 `i.sss` / `i.ss` / 界面控件 / 文件，见 `iapp-i-reference.md`

## 从裕语言调用

```java
call(a, "mjava", "app.bind")          // 无参
s r
call(r, "mjava", "app5.add", 3, 4)    // 有参、取返回值
```

- 第一段是接收返回值的变量；无返回值写 `null`
- 第三段 `app.bind` = 模块名 `app` + 方法名 `bind`
- 参数个数必须与方法一致 ✅
- `call` 出错不会中断整个载入事件，后续语句继续执行 ✅
- **yul 数字字面量的装箱类型不固定**：`0` / `268435456`(2²⁸) / `536870912`(2²⁹) 以 `Integer` 传入，`1073741824`(2³⁰) 以 `Long` 传入 ✅（API 34）
  - 后果：形参写 `int` 时，Long 那个匹配失败 → `Method go( java.lang.String, java.lang.Long ) not found in bsh scripted object: global`，**界面无反应、不崩、只在 logcat 留 `JavaErr`**
  - 对策：跨语言入口的数值形参写成 `Object`，进来再转：
    ```java
    public void go(String file, Object flagObj) {
        int flag = 0;
        if (flagObj instanceof Number) { flag = ((Number) flagObj).intValue(); }
    }
    ```

## 铁律表（API 28 实测）

| 写法 | 结果 | 错误原文 |
|---|---|---|
| `String[] a = {"x","y"}` | ✅ **可用** | — |
| 形参 `final Object x` | ❌ 模块失效 | `Parse error ... Encountered: final` |
| 文件顶层具名 `class Foo` | ❌ 模块失效 | `can't load this type of class file` |
| `0xFF000000` 及任何 > `0x7FFFFFFF` 的十六进制字面量 | ❌ 模块失效 | `Error or number too big for integer type`；用 `android.graphics.Color.parseColor("#RRGGBB")` 或负数代替 |
| `Object... xs` 可变参数 | ❌ 模块失效 | `Parse error ... Encountered: .` |
| `new bsh.Interpreter()` | ❌ 模块失效 | `No static field or inner class: Interpreter of class bsh` |
| 匿名类 `new Object(){...}` | ❌ **且中断整个载入事件** | `YuErr` 指向 call 行 |
| 匿名实现接口 `Comparator` | ✅ 可用（API 28） | — |
| 匿名实现 `View.OnLongClickListener` | ✅ 可用（API 28） | — |
| 匿名实现 `AdapterView.OnItemClickListener` / `DialogInterface.OnClickListener`，且**回调里调用同模块的脚本方法** | ✅ 可用（API 28，文件管理器实战） | — |
| 匿名实现 `Runnable`（`new Thread(...)` / `runOnUiThread(...)`） | ✅ 可用（API 34） | — |
| 后台线程里抛出 BeanShell 解析/求值错误 | ❌ **整个进程被杀** | `java.lang.reflect.UndeclaredThrowableException at $Proxy5.run`；线程内的 `try/catch(Throwable)` 接不住，异常穿过 bsh Proxy 直达 `Thread.run` |
| 循环变量取名 `i` | ✅ 不遮蔽 iApp 的 `i`（循环后 `i != null`） | — |

循环体内 `i` 就是那个整数，不能写 `i.sss`；要在循环里用 iApp 的 `i`，先 `Aid_javaCode app = i;`，或把循环变量改叫 `idx`。

### Java 7/8 语法（⚠ 按解析器版本判断）

iApp 5.0.1013 的 `base.apk` 里能读到 BeanShell `2.0b4`，早于 Java 7/8：

- lambda `() -> {}`、方法引用 `::`：不支持，`Parse error ... Encountered: ->`，整个模块失效。
- try-with-resources `try (Resource r = ...) {}`：不支持，`Parse error`，整个模块失效。
- 替代：lambda → 匿名接口实现（注意 default 方法）；try-with-resources → `try { ... } finally { if (r != null) r.close(); }`；复杂逻辑编译成 dex。

### 调 Material / 框架的可变参数方法

- BeanShell 不能直接调用形参是 `int...` / `Object...` 的方法（Material 里常见，如
  `ProgressIndicator.setIndicatorColor(int...)`）：解析失败，整个方法中断，`catch` 接不住
- 退到父类或等价 API：如进度条颜色改用 `ProgressBar.setProgressTintList(ColorStateList)`（⚠ 未实测）
- 调用了不存在的方法同样中断：`Command not found: xxx( … )`，是 EvalError
- 结论：方法名按**通用 Material API** 写；只有不确定存在的调用才先做静态核对，
  不要为了“保险”把整张 API 表抄进 SKILL

### 版本前提（不要外推）

- 匿名实现**接口**能过、匿名**继承类**不能过：在 API 28 上实测如此。
- `View.OnLongClickListener`：**API 28 可用**（✅ 实测）。Android 14 上该接口新增 default 方法 `onLongClickUseDefaultHapticFeedback`，据现有记录匿名实现会崩；但没有留下对应原始读数，这条先按 ⚠（待实机复核）看待。
  结论要写成「API 28 上可用」，不要写成「OnLongClickListener 不能用」。
- 判据不是 Android 版本号，也不只是抽象方法个数：看**目标 API 上该接口的完整方法集（抽象 + default）**，以及框架会不会在你的用法里调用到新增的 default 方法。`Comparator` 自 API 24 起有 default 方法，但用户代码不调它，所以照样可用；`OnLongClickListener` 的 default 方法会被 `View` 的长按处理链调用，所以在 API 34 上暴露。
- 最终判据仍是**目标 API 上的最小探针**：写匿名实现、真实触发一次，看是否崩。

## 加载模块：`i.fn`（实测）

```java
i.fn("b");            // 加载 b.mjava；模块名不带扩展名
b_hello();            // 加载后直接调
int n = b_add(2, 3);  // 有返回值也直接接
```

- 实测：`i.fn("b")` 后可直接调 `b_hello()`，有参/返回值也直接接
- `i.fn` 把模块加载进**当前**解释器，共享 `activity` / `i` / 方法命名空间
- 一次 call 内加载一次即可；facade 用模块级 `G_IMPORTED` 标记
- 打包安装后同样可用（2048 的 7 模块源码直接打包，实测）
- 同名方法后加载覆盖；子模块方法加前缀避免

### 铁律：先加载，再调用

未加载就调用：

```
Command not found: u_st( java.lang.String ) : at Line: 60 ...
Called from method: layout
```

**整个方法立即中断，`try/catch(Throwable)` 接不住**，后续代码都不执行。
所以 facade 的每个 public 入口第一行必须是 `importAll()`，不能先读任何 `u_*`。

- `importAll()` **只能写在方法体内**：写在文件顶层会在模块加载时立即执行，报
  `Command not found: importAll() : at Line: 1`（2026-10-27 实测）。
  没有 `i.fn` 子模块的模块不需要它，直接删掉即可。

### 不要用的两条

| 写法 | 问题 |
|---|---|
| `i.d.f("b.mjava")` | 只在开发模式可用；打包后 `i.d` 是 `xn0`，`f` 是 Context 字段，没有 `f(String)` |
| `i.call("b.b_hello","mjava")` | 新建解释器，但找不到当前工程模块（实测返回 null，方法没执行） |

交付直接打包源码文件，不合并。

- `i.d.f(name)` 的参数是**带扩展名的裸文件名**（工作目录是 `src/`）：`i.d.f("b.mjava")`。只给 `b` 会按整数解析并抛 `NumberFormatException`；写 `src/b.mjava` 同样报错
- 用相对路径跳出 `src/`（如 `../b.mjava`）会被路径校验吃掉
- `i.d.f` 内部只捕获 `bsh.EvalError`：解析/求值错误打印 `MJavaErr` 并返回 false；文件缺失等其它异常会冒泡
- `i.d` 是每次 call 新建的解释器字段；但把它存进 `i.sss` 后，下一次 call 取回的对象仍可 `eval(...)`——这是“手动留存的旧解释器”，不要和“模块级变量跨 call”混为一谈

```java
// call A
i.sss("savedD", i.d);
// call B
Object d = i.sss("savedD");
Object r = d.eval("...");   // 旧解释器的命名空间还在
```

- 只活到本次运行结束（`i.sss` 每次运行重置），跨进程必丢；
- 它绑定的是旧 call 的 `activity` / `i`，跨页后可能过期；
- 用完 `i.sss("savedD", null)`，避免持有 View/Activity 引用。⚠ 类型转换与跨页行为未单独实测

### 时序（该次测量 50 次均值，针对 `i.d.f`）

| 方式 | 语义 | 耗时 |
|---|---|---|
| `call(null,"mjava","mod.method")` | 每次新建解释器 | 5.17 ms |
| `i.d.f("mod.mjava")` | 导入**当前**解释器（读文件 + eval） | 0.87 ms |
| `i.d.eval("method()")` | 复用已导入的解释器 | 0.23 ms |

`i.fn` 未单独计时；它在一次 call 里只执行一次，量级与 `i.d.f` 同。

### 其他实测边界

- 模块级变量在同一次 call 内保留，下一次 call 归 0；跨 call 状态放 `i.sss`
- `.iyu` 可以直接 `call` 任意模块，不必先进 facade
- 子模块顶层可以正常写 `import`
- `i.hs(String) -> String` 可在 mjava 里同步 GET，放在后台线程里调用 ✅（API 34，2026-10-27，返回 2624 字节）
- `i.us(View,"src","http://…jpg")` 能把网络图直接加载进 ImageView ✅（API 34，同一批次）
- `i` 对象上还有裕语言函数的同名方法：`hs / us / uls / ula / json / uigo / ug / uall`
  （签名见 `iapp-i-reference.md`；`hs`、`us` 已实机，其余 ❓）

完整拆分规范、facade 模式、7 模块 2048 实例见 `modularization-guide.md`。

## BeanShell 方法解析的坑

有些继承来的公开方法在 BeanShell 里解析不到，会抛
`Error in method invocation: Method xxx() not found in class ...`，并**中断整个方法**。

实例：`TextInputEditText.isSingleLine()` 解析失败。遇到这种读数，换等价属性或用反射，别硬调。

对 `Class` 引用调实例方法同理：`String.class.length()` 里的 `length` 不在 `java.lang.Class` 上，会报 `Method ... not found in class 'java.lang.Class'` 并中断；`Class` 自身的方法（`getName()` / `getSimpleName()` / `isInstance()`）正常。判断类引用用 `obj instanceof Class`（或 `Class.class.isInstance(obj)`），不要靠类名字符串。⚠ 未单独实测。

## 跨模块调用：`i.call`

```java
i.call("mjava", "pick.show", new Object[]{"标题", list, "demo.onPick"});
```

| 参数 | 含义 |
|---|---|
| 第 1 个 | **语言标识**，固定 `"mjava"`（DEX 里先 `equals("myu")` 再 `equals("mjava")`）。不是“接收返回值的变量名”，传 `null` 直接 NPE、传 `""` 会静默什么都不做 |
| 第 2 个 | `模块.方法`，**必须带模块名**（内部按 `.` 切开，拼 `模块.mjava` 调 `j6h.f()` 导入） |
| 第 3 个 | `Object[]` 实参，内联或先放变量再传都可以 |

返回值：

- 目标方法返回 int/String 等 → 可以用 `Object r = i.call(...)` 接住（实测 2+3=5、字符串拼接成功）
- 目标方法返回 **void** → 赋值会报 `Void initializer`，且**整个方法立即中止**，后续语句不再执行

因此**一律当语句调用，不接返回值**；需要返回值时让组件方法统一 `return String`。

每次 `i.call` 都会新建一个 BeanShell 解释器并重新导入模块（约 10ms 级），高频路径别用它做内层循环。
界面对象、`activity`、`i.sss` 是共享的，所以跨模块建出来的 View 和监听器在调用返回后继续有效。

## 失败签名

解析/求值失败时，`ygs` 与 `System.err` 同时出现：

```
JavaErr：
Typed variable declaration : Command not found: findViewById( int ) : at Line: 4 : in file: inline evaluation of: ``...`` : findViewById ( 2 )
Called from method: bare : at Line: -1 : in file: <Called from Java Code> : <Compiled Java Code>
```

`inline evaluation of` 证明执行器是 BeanShell。
