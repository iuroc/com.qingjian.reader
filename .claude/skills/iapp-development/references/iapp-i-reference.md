# i 对象参考（Aid_javaCode）

版本前提：iApp 5.0.1013、API 28 实测。

## 身份

- `i` 的真实类：`com.iapp.app.Aid_javaCode`
- 公开方法 390 个，公开字段 12 个：
  `a b c d e f g h i j alertdialog ss_dim`
- 反射筛选 `ss/sss/dim/d` 得到 6 个方法重载（见下）

## 关键成员

| 成员 | 签名 | 行为 | 级别 |
|---|---|---|---|
| `i.d` | 字段，`bsh.Interpreter` 子类 | 当前**这次 call** 的 BeanShell 解释器 | ✅ |
| `i.d.set(k,v)` / `get(k)` | — | 同一次 call 内可读写；`get(未定义)` 返回 null | ✅ |
| `i.d.eval("1+1")` | — | 返回 2 | ✅ |
| `i.d.f(name)` | 方法表中存在 `f` | 仅开发模式按文件名导入；打包后无 `f(String)` | ⚠ |
| `i.fn(name)` | — | 加载模块进当前解释器；交付用 | ✅ |
| `i.call(lang,"mod.method",Object[])` | — | 新建解释器调用；void 方法不要接返回值 | ✅ |
| `i.d(Aid_javaCode,String)` | → int | 同名方法，与字段 `d` 并存 | ✅ |
| `i.ss` | `ss(String)`→Object / `ss(String,Object)`→void | 底层 HashMap 默认 **null**，读写直接 NPE | ✅ |
| `i.sss` | `sss(String)`→Object / `sss(String,Object)`→void | 跨 call 共享；每次**运行**重置 | ✅ |
| `i.dim` | `dim(String,Object)`→void | 按 key 前缀分派 | ✅ |
| `i.a` | 实例字段（Map） | `i.dim` 无前缀时的落点；**每次 call 新实例** | ✅ |

## 公开字段（dexdump `base.apk`，类型确定）

| 字段 | 类型 | 用途 | 级别 |
|---|---|---|---|
| `a` | HashMap | `i.dim` 无前缀落点 | ✅ |
| `b` | Activity | 当前页 Activity | ✅ |
| `c` | Context | 当前上下文 | ✅ |
| `d` | j6h（`bsh.Interpreter`） | 当前 call 的解释器 | ✅ |
| `e` | FrameLayout | 未实测；从类型看是容器/根布局 | ❓ |
| `f` | int | 未实测 | ❓ |
| `g` | WebChromeClient.CustomViewCallback | WebView 全屏回调 | ⚠ 推断 |
| `h` | Handler | 主线程 Handler | ⚠ 推断 |
| `i` | **static** HashMap | 未实测；与 `ss_dim` 是两个字段 | ❓ |
| `j` | **static** int | 未实测 | ❓ |
| `alertdialog` | **static** AlertDialog | 全局对话框 | ⚠ 推断 |
| `ss_dim` | **static** HashMap | `i.ss` 底层，默认 null | ✅ |

`i.d` 与 `i.sss` 不是同一套存储：`i.d` 是解释器的变量命名空间（每个 call 一份，模块级变量在这里）；`i.sss` 是独立的类级 Map，跨 call 但每次运行重置。`i.d.set("x",1)` 不会让 `i.sss("x")` 变成 1，反之亦然。

IYU 侧 `sss.名` 读哪张表：按 `i.dim("sss.名", v)` 实测分派（`sss.` → `i.sss`）推断，读的是 `i.sss`；但没有“iyu 写入 → mjava 读出”的直接探针，标 ⚠。白名单下 `.iyu` 不再写 `sss.`。

## 裕语言函数在 i 对象上的同名方法（dexdump 签名，2026-10-27）

`Aid_javaCode` 直接暴露了裕语言那几个常用函数的同名方法，mjava 里可以当原生 API 调：

| 方法 | 签名 | 用途 | 状态 |
|---|---|---|---|
| `hs` | `(String) -> String`（另有 5 个重载） | 同步 HTTP 请求 | ✅ API 34 实机，返回 2624 字节 |
| `us` | `(Object,String,Object) -> boolean` | 设控件属性；第一参可传 View 实例或 id | ✅ API 34 实机，加载网络图 |
| `uls` | `(Object,Object,String[,int,int]) -> void` | ListView + 模板渲染 | ⚠ 仅签名 |
| `ula` | `(Object,Object[,Object]) -> Object` | 列表字段映射 | ⚠ 仅签名 |
| `json` | `(String) -> Object` 等 4 个重载 | JSON 解析 | ⚠ 仅签名 |
| `uigo` | `(String[,int]) -> void` | 页面跳转 | ⚠ 仅签名 |
| `ug` | `(Object,String) -> Object` | 读控件属性 | ⚠ 仅签名 |
| `uall` | `(Object,boolean) -> Object[]` | 取容器子控件 | ⚠ 仅签名 |

注意：

- `hs` 是**同步**的，主线程直接调会阻塞；放 `new Thread(new Runnable(){...})` 里 ✅
- `us` 的第一参类型是 `Object`，动态创建的 View 可以直接传，不必是 id
- 解析 JSON 别写全限定名 `org.json.JSONObject`（BeanShell 解析失败并杀进程），用 `import org.json.JSONObject;`

## 生命周期（同一 pid 内实测）

| 对象 | 跨 call | 跨「运行」 | 跨进程 |
|---|---|---|---|
| `i.d` 解释器 | ❌ 每次 call 新建（`dget-cross=null`） | ❌ | ❌ |
| `i.a` 实例 Map | ❌ 每次 call 重置 | ❌ | ❌ |
| `i.sss` | ✅（`sss=1` → `sssRead=1`） | ❌ 同 pid 两次运行都从 null 起算 | ❌ |

读数：

```
B4c-dget0=null
B4c-dget1=v1
B4c-deval=2
B4c-dget-cross=null
B4c-dim-d=null
B4c-dim-a={b4x=v2}
B4c-pre-sss=v3
B4c-pre-ss-err=NullPointerException … HashMap.put … null object reference
B4c-pre-a={a=v5}
```

结论：`i.d` 与 `i.a` 是**每次 call 新建的实例字段**；`i.sss` 是**每次运行重置的类级存储**。

## i.dim 前缀分派（✅）

| 调用 | 落点 | 验证 |
|---|---|---|
| `i.dim("sss.b4y","v3")` | `i.sss("b4y")` = v3 | ✅ |
| `i.dim("ss.b4z","v4")` | `i.ss("b4z")` → NPE（ss_dim 为 null） | ✅ |
| `i.dim("b4x","v2")` | 没有写进 `i.d`（`i.d.get` = null），落在 `i.a` Map | ✅ |
| `i.dim("a","v5")` | 落到 `i.a` Map，`{a=v5}` | ✅ |

注意：`i.a` 每次 call 重置，所以 `dim` 无前缀写入的值**活不过一次 call**。

## 读取有没有副作用（❓）

`i.d.get(name)` 对已赋值的普通变量预期是只读（命名空间读取 + `Primitive.unwrap`），但有两点没实测：

- 变量是未求值的 `LHS` / `Primitive` 时，`unwrap` 是否触发 `getValue()` 并执行表达式；
- `i.d` 是 `bsh.Interpreter` 子类，子类是否重写了 `get`。

判定探针：放一个带副作用的哨兵对象，读 `get` 前后比对身份、hash、字段值、计数器；再测未定义名与延迟表达式。未测前记 ❓，不要写“读 get 不会改变对象”。

`i.d.get` 不能当存在性探针：`get(未定义)` 返回 null，但已定义的变量也可能就是 null，两者分不开；且 `get` 可能触发 LHS 求值。要判存在，自己维护 key 集合（如 `i.sss("__keys")`），或对受控写入用哨兵值；跨 call 一律看 `i.sss`，不看 `i.d`。

## 与旧预期的差异

- 旧预期：`i.sss` 是静态 HashMap，同进程跨运行保留。
- 实测：跨 call 保留，但**同 pid 的两次运行不保留**（两次 `B4-sss=1`）。重置点在「每次运行」，疑似每次运行重建类加载器。
