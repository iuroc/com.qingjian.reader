# .iyu 界面文件结构

从设备上工程实测得到的格式（iApp 5.0.1013 / Android 9）。

## 骨架

```
<View id="1" did="0" type="LinearLayout">
<ppt>width=-1
height=42dp
orientation=vertical
backgroundcolor=#50c4e5
gravity=center_vertical</ppt>
<event></event>
</View>
<View id="2" did="1" type="TextView">
<ppt>width=-2
height=-2
text=我的应用iApp
textsize=16sp
textcolor=#ffffff
layout_marginleft=10dp</ppt>
<event></event>
</View>
<UIEventset><eventItme type="loading">
call(null, "mjava", "app.bind")
</eventItme></UIEventset>
```

## 字段

| 字段 | 含义 | 级别 |
|---|---|---|
| `id` | 控件标识，整数；模块里用 `findViewById(id)` / `i.gvs(id)` 取 | ✅ |
| `did` | 父容器 id，`0` = 根 | ✅ |
| `type` | 控件类型 | ✅ |
| `<ppt>` | 控件属性，每行 `key=value` | ✅ |
| `<event>` | 该控件的事件块 | ✅ |
| `<UIEventset>` | 文件末尾的全局事件区 | ✅ |

## 控件树

✅ 实测：容器 30 里文件顺序写 id=9、3、5，读回子控件 `getId()` 顺序就是 **9,3,5**。

- **兄弟顺序按文件出现顺序，不按 id 大小**
- `did` 指向谁就挂到谁下面，与书写位置无关（B1：id=10 写在最后但 `did=7`，父控件是 7）

## ppt 属性层（两层）

第一层是普通属性，写出来就是值；第二层是 `st_` 前缀的 **setter 桥**，直接调用对应 Java setter。

### 普通属性（✅ 实测）

| 写法 | 实际语义 | 证据 |
|---|---|---|
| `width=-1` / `-2` | match_parent / wrap_content | ✅ |
| `width=42dp` | dp 尺寸 | ✅ |
| `textsize=24` | **sp**，无单位也按 sp | `getTextSize()` = 72.0（density 3.0） |
| `padding=12` | **px**，不是 dp | `getPaddingLeft()` = 12 |
| `text` `textcolor` `backgroundcolor` | 文本/颜色 | ✅ |
| `textstyle=bold` | 粗体 | `getTypeface().isBold()` = true ✅ |
| `maxlines=2` / `ellipsize=end` | 行数 / 省略号 | `getMaxLines()`=2、`getEllipsize()`=END ✅ |
| `visibility=gone / invisible` | 隐藏 | `getVisibility()` = 8 / 4 ✅ |
| `layout_weight=1` | 线性布局权重 | `LayoutParams.weight` = 1.0 ✅ |
| `height=0` + `layout_weight=1` | 填满剩余空间（按键区均分） | ✅ 实战（计算器） |
| `weight=1` | **无效** | 读回 0.0；配合 `width=0` 会让控件宽度为 0（标题直接消失）❌ |
| `alpha=0.5` | **无效** | 读回 1.0 ❌（要用 mjava `setAlpha`） |
| `clickable=true` | 生效 | `isClickable()`=true ✅（Ripple 的前提） |
| `minheight=40dp` | 生效 | `getMinimumHeight()`=120（dp→px）✅ |
| `elevation=4dp` | 生效 | `getElevation()`=12.0（dp→px）✅ |

锚点：该次测量 density = scaledDensity = 3.0，默认字号 14sp → `getTextSize()` = 42.0；换设备必须重取。

布局时机：载入事件里 `getHeight()` 还是 0（尚未测量），要拿真实高度需在布局完成后取。

### st_ 桥（✅ 实测）

| 写法 | 结果 | 锚点 |
|---|---|---|
| `st_setTextSize=20` | 生效，按 sp 解释（60.0 = 20×3） | 默认 42.0 |
| `st_setTextSize=20sp` | **不生效**，回落默认 42.0 | — |
| `st_setTextColor=16711680` | 生效，读回 16711680 | — |
| `st_setTextColor=#ff0000` | **不生效**，读回 -11975345 = 默认色 | 默认 -11975345 |
| `st_setAlpha=128` | 读回 128.0（默认 1.0），**没有 clamp** | 默认 1.0 ⚠ |
| `st_setChecked=true` | **不生效**：Chip 读回 `checkable=false checked=false`（布尔字符串不认，1/0 未测） | 默认 false |
| `st_setGravity=center` | ❓ 未测；`setGravity(int)` 期望整数，字符串 `center` 很可能不生效 | 用普通层 `gravity=center` |
| `st_setGravity=17` | ❓ 未测；17 = `Gravity.CENTER`，若按十进制整数解析可能生效 | — |

### 书写规则（✅ 实测）

- `key = value` 两边带空格 → **整行失效**（`textsize = 20sp` 读回默认 42.0）
- 未知键 `unknownkey=abc` → 页面正常，无报错（静默忽略）
- `us(控件, "st_xxx", 值)` **不认 st_ 键**：`us(13,"st_setTextSize",30)` 后字号仍是 42.0（白名单前测；现在 `us` 已禁用，setter 走 mjava）

### 语法细节（✅ 实测；以下为白名单收紧前的裕语言行为记录）

> 白名单后这些写法不再使用：事件体只写 `call` / `addv`，`syso` / `s` / `us` 等一律下沉 mjava。下表只用于理解旧工程和旧报错。

| 写法 | 结果 |
|---|---|
| 注释独占一行 `// …` | ✅ 正常 |
| 行尾注释 `syso("x") // …` | ❌ `YuErr`，**中断整个载入事件** |
| 字符串里写 `\n` | ✅ 正常，输出为换行；不会劈开源码 |
| `syso("x","y")` 多给参数 | ⚠ 不报错，只输出第一个参数；至少 syso 不校验参数个数 |
| `s a=1`（紧凑） | ✅ a 为 1 |
| `s b`（不赋值） | ✅ b 为 null |

## 未决

- 除 `syso` 外的短指令是否校验参数个数 ❓
- 其余控件类型、属性名对照表 ❓

## 长页面：ScrollView 根 + LinearLayout 内层

内容超过一屏时（探针页尤其常见），根部换成 `ScrollView`，其余控件挂到内层 `LinearLayout`：

```xml
<View id="1" did="0" type="ScrollView">
<ppt>width=-1
height=-1
backgroundcolor=#f5f6f8</ppt>
<event></event>
</View>
<View id="2" did="1" type="LinearLayout">
<ppt>width=-1
height=-2
orientation=vertical
padding=12</ppt>
<event></event>
</View>
<!-- 其余控件 did=2；height=-2 即可，不要写 -1 -->
```

要点：

- `ScrollView` 是短名控件（`android.widget.ScrollView`），不用登记
- 内层 `LinearLayout` 的 `height` 必须 `-2`（wrap_content）；写 `-1` 会撑满导致滚不动
- 子控件高度都给 `-2` 或固定 dp，不要用 `layout_weight`（在 ScrollView 里没有剩余空间可分）
- 嵌套 `ViewPager` / `DrawerLayout` 时，容器高度要用**固定 dp**（DrawerLayout 还要求精确尺寸）
