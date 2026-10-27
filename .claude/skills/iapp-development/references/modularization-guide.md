# mjava 模块化规范

版本前提：iApp 5.0.1013、Android 9（API 28）、裕 3。

## 一句话

**入口模块做 facade；用 `i.fn("模块名")` 把子模块加载进当前解释器；方法加前缀；每个 public 入口第一行加载。**

## 怎么加载另一个 mjava（✅ 实测）

实测写法：

```java
i.fn("b");      // 加载 b.mjava；模块名不带扩展名
b_hello();      // 加载后直接调
b_add(2, 3);    // 有返回值也直接接
```

- `i.fn` 把模块加载进**当前这次 call 的解释器**，共享 `activity` / `i` / 方法命名空间
- 一次 call 内加载一次即可；我们的每个 public 入口是新的 call，
  所以用 `G_IMPORTED` 标记“本次 call 已加载”
- **打包安装后同样可用**：2048 的 7 模块源码直接打包，用户实测运行正常
- 多模块方法名要加前缀，避免覆盖

### 铁律：先 fn，再调用

```java
public void layout() {
    importAll();                       // ← 必须第一行
    if (u_st("built").equals("1")) {    // 这里才能用 u_st
        return;
    }
    ...
}
```

没加载就调用：

```
Command not found: u_st( java.lang.String ) : at Line: 60 ...
Called from method: layout
```

**整个方法直接中断，`try/catch(Throwable)` 也接不住。**

### 不要用 `i.d.f`

- `i.d.f("b.mjava")` 只在**开发模式**可用（按文件名读当前工程 `src/`）
- 打包 APK 后 `i.d` 变成混淆类 `xn0`，`f` 是 `Context` 字段，没有 `f(String)`：

```
Method f( java.lang.String ) not found in class 'xn0'
```

- 交付用 `i.fn`，不要用 `i.d.f`

### `i.call` 可用，但每次新建解释器

```java
Object r = i.call("mjava", "b.b_add", new Object[]{2, 3});  // 返回 5
i.call("mjava", "b.b_hello");                                // void 方法：当语句调
```

- 参数顺序：**语言 → "模块.方法" → Object[]**
  （写成 `i.call("b.b_hello","mjava")` 会返回 null，方法不执行）
- 每次新建解释器，约 5–11ms；模块级变量不共享
- 目标方法返回 void 时**不要接返回值**：`Object r = i.call(...)` 会报
  `Void initializer` 并中断整个方法
- 本项目跨模块加载用 `i.fn`（同一解释器、直接调）；`i.call` 适合偶尔的隔离调用

## 推荐结构（facade + 私有子模块）

```
src/
├── mian.iyu             # 只 call facade
├── game.mjava           # facade：init/layout/newGame/...；importAll()
├── g2048_util.mjava     # u_*     工具：dp / st / sv / log
├── g2048_core.mjava     # core_*  纯规则：不碰视图/存储
├── g2048_store.mjava    # store_* 持久化
├── g2048_ui.mjava       # ui_*    视图与样式
├── g2048_anim.mjava     # anim_*  动画原语
└── g2048_input.mjava    # input_* 触摸/按键
```

### facade 的写法

```java
boolean G_IMPORTED = false;

public void importAll() {
    if (G_IMPORTED) return;
    G_IMPORTED = true;
    String[] mods = new String[]{
        "g2048_util", "g2048_core", "g2048_store",
        "g2048_ui", "g2048_anim", "g2048_input"
    };
    for (int k = 0; k < mods.length; k++) {
        i.fn(mods[k]);
    }
}

public void init() {
    importAll();
    ...
}
```

- `G_IMPORTED` 模块级变量只在**一次 call 内**有效，下一次自动重置
- 加载顺序 = 依赖顺序：`util` 最先，`core` 次之，其余最后
- `.iyu` 只认 facade；子模块视为私有

### 子模块的写法

- 方法统一前缀：`u_` / `core_` / `store_` / `ui_` / `anim_` / `input_`
- 顶层可以写 `import`（✅ 实测）
- 子模块可以调用其他已加载模块的方法（同一解释器）
- 不要在子模块顶层放需要跨 call 存活的状态

### 避免环

```
util  ←  core / store / ui / anim / input  ←  game(facade)
```

- 动画模块只放**原语**（平移、缩放），`postDelayed` 的流程回调留在 facade
- 子模块需要“发起一次移动”时，通过 facade 的 `doMove`（同一解释器里可见），不要让 anim 反过来加载 game

## 状态与命名

| 需求 | 做法 |
|---|---|
| 跨 call 状态 | `i.sss`（`u_st/u_sv` 包装） |
| 一次 call 内的缓存 | 模块级变量（如 `G_IMPORTED`） |
| 同名方法 | 后加载覆盖先加载；靠前缀避免 |
| 同名模块 | 不要重名；`i.fn` 按模块名加载 |

### 多模块方法名

- `i.fn` 把所有模块的方法加载进**同一个解释器**：同名方法后加载覆盖先加载，子模块方法一律加前缀（`core_` / `ui_` / `store_`）。
- 模块级变量也在同一命名空间：同名变量互相覆盖，常量也加前缀。
- `importAll()` 只由 facade 定义；子模块不要定义，否则后加载的会覆盖 facade 的。
- 用 `i.call` 或 `.iyu` 的 `"模块.方法"` 形式时，方法名按模块隔离；但同一模块内仍要唯一。
- **点号后那一段就是方法名本身**：模块里必须真有叫 `method` 的方法。入口写成 `probe_boot` 再
  `call(null,"mjava","qj_probe.boot")` 会报
  `Method boot() not found in bsh scripted object: global` ✅（API 34，2026-10-27）。
  前缀只在 mjava 之间 `i.fn` 后互相调用时需要，`模块.方法` 的寻址不认前缀。
- 不要用 `init` / `layout` / `update` 这种通用名裸奔；要么放 facade，要么加模块前缀。

## 性能

- `i.fn` 一次 call 只加载一轮；量级与 `i.d.f` 相当（均在 1ms 级）
- 之后的方法调用是同解释器内的普通调用，没有跨 call 开销
- 不要把 `i.fn` 放进循环或每帧
- 重复 `i.fn` 同一模块：会重新求值——方法重定义、模块级变量重置、顶层副作用重跑；不报错。用 `G_IMPORTED` 防重入。⚠ 未单独实测

## 失败签名

| 现象 | 原因 |
|---|---|
| `Command not found: xxx(...)` + 方法中断、后续无日志 | 调用了未加载/拼错的方法；**catch 不住** |
| `Method f( java.lang.String ) not found in class 'xn0'` | 打包版用了 `i.d.f`，改用 `i.fn` |
| `i.call(...)` 返回 null、方法没执行 | 参数顺序写成了 `i.call("模块.方法","mjava")`；正确是 `i.call("mjava","模块.方法",...)` |
| `Class: Xxx not found in namespace` | 子模块里少 import / 用了不存在的类 |

## 什么时候拆

| 信号 | 动作 |
|---|---|
| 单文件 > 300–400 行 | 按职责拆 |
| 同时出现“规则 + 视图 + 存储 + 动画” | 至少拆 core / store / ui / anim |
| 逻辑想单独写自检 | 拆 core（纯逻辑，可在 `loading` 跑） |
| 同一段样式/动画重复 3 次以上 | 拆 util / anim |

## 2048 实例

| 文件 | 行数 | 职责 |
|---|---|---|
| `game.mjava` | ~333 | facade + 流程编排 |
| `g2048_util.mjava` | ~35 | dp / i.sss / 日志 |
| `g2048_core.mjava` | ~199 | 规则 + 自检 |
| `g2048_store.mjava` | ~90 | 存档 |
| `g2048_ui.mjava` | ~233 | 样式 / 卡片 / 弹层 |
| `g2048_anim.mjava` | ~50 | 平移 / 缩放原语 |
| `g2048_input.mjava` | ~114 | 滑动 / 方向键 |

拆分前单文件约 700 行；拆分后每个文件一个职责，源码直接打包，不合并。

拆分时踩过的真实错误：`layout()` 在 `importAll()` 之前读了 `u_st("built")`，
新 call 的解释器里还没有 `u_st` → `Command not found`，整个 `layout` 中断，棋盘不渲染。
修复：把 `importAll()` 移到方法体第一行。
