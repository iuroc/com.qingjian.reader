# 调试与失败签名

## 取日志

```
adb logcat -d -v time 'ygs:V' 'System.err:V' '*:S'
```

mjava 里的 `i.syso(...)` 输出在 tag `ygs`；iApp 内部报错同时进 `ygs` 与 `System.err`。

## 三种错误前缀（✅ 实测 iApp 5.0.1013 / Android 9）

| 前缀 | 来自 | 影响范围 | 例子 |
|---|---|---|---|
| `MJavaErr` | mjava 模块解析/加载期 | **只废掉该模块**，后续语句继续 | `Parse error at line 1, column 17. Encountered: final` |
| `JavaErr` | 模块求值期 | 只废掉该次 call，后续继续 | `Command not found: findViewById( int )` |
| `YuErr` | 裕语言侧，会**中断整个载入事件** | 本次事件余下语句不执行 | 匿名类模块调用后出现，`第N行` 指向 call 行 |

判断方法：看报错后有没有下一条 `i.syso` 输出。

## 原文样例

解析错误（final 形参）：

```
MJavaErr：
Parse error at line 1, column 17.  Encountered: final
```

类加载错误（具名类 / 匿名类）：

```
MJavaErr：
Sourced file: inline evaluation of: ``class Foo { ... }`` unknown error:
can't load this type of class file : at Line: 1 : ...
```

求值错误（裸 findViewById）：

```
JavaErr：
Typed variable declaration : Command not found: findViewById( int ) : at Line: 4 : in file:
inline evaluation of: ``...`` : findViewById ( 2 )
Called from method: bare : at Line: -1 : in file: <Called from Java Code> : <Compiled Java Code>
```

## 规律

- 所有 mjava 错误文本里都有 `inline evaluation of` —— 执行器是 **BeanShell**
- 模块解析失败是「全有或全无」：一个方法写坏，整个模块的方法都不可用
- 解析期错误（`MJavaErr`）发生在模块加载前，模块里的 `try/catch` 还没机会执行，**兜不住**；能兜的是方法体内的运行期 Java 异常
- 影响范围是模块级：该模块所有方法都不可用；其它模块和已加载模块不受影响，后续语句继续；如果随后调用该模块的方法，会再触发 `JavaErr`（`Command not found`），中断本次 call
- 行号只在 `at Line: N` 里对模块文件有效；iApp 弹窗里的「mian.iyu 第 N 行」不可靠
