# 样式分层：ppt 还是 mjava

核心判据：**画布能看见的，留在 ppt；需要计算或全局统一的，才进 mjava。**

## 三条规则

### 1. mjava 只补差

ppt 能表达的静态样式，不要在 mjava 里再写一遍。
重复设置会让画布预览与真机不一致（画布不会执行 mjava，真机会），这是“飘逸”的根源。

- ✅ ppt：颜色、字号、内边距、外边距、方向、对齐、可见性、粗细、行数
- ✅ mjava：dp→px 换算、按屏宽比例计算、圆角/渐变等 drawable、运行期状态
- ❌ mjava 里重复设置 ppt 已写的颜色/字号

### 2. 复用分档

| 复用次数 | 做法 |
|---|---|
| 2–3 处 | 直接复制 ppt 片段 |
| 5 处以上且结构一致 | 抽成组件 `.iyu` |
| 需要计算 / 集中管理 | 做 mjava helper |

### 3. 主题级例外

某个颜色或尺寸必须**全局统一**时，即使它看起来是控件级属性，也放到 mjava 主题模块统一设置。

这是有意用「画布看不见」换「单一真源」：

- 画布与真机的一致性让位于全局可维护性
- 换色/换尺寸只改一处
- 代价：设计器里看到的颜色可能与真机不同，必须靠真机验证

## 判据速记

| 问自己 | 放哪 |
|---|---|
| 画布能预览、且只影响这个控件？ | ppt |
| 要不要换算/计算/读运行期状态？ | mjava |
| 同一套颜色/字号是否要全应用统一？ | mjava 主题模块 |
| 结构重复 5 次以上？ | 组件 `.iyu` |

## 实测分界（API 28）

| 样式 | ppt | mjava |
|---|---|---|
| 尺寸/边距/内边距 | ✅ `width=-1/-2/42dp`、`padding=12`（px） | — |
| 方向/对齐 | ✅ `orientation`、`gravity` | — |
| 颜色/字号 | ✅ `textcolor`、`backgroundcolor`、`textsize=18`（sp） | 全局统一时进主题模块 |
| 字重 | ✅ `textstyle=bold` | — |
| 行数/省略 | ✅ `maxlines=2`、`ellipsize=end` | — |
| 显隐 | ✅ `visibility=gone/invisible` | 运行期切换才用 setter |
| 权重 | ✅ **只能写 `layout_weight`**（`weight` 无效） | — |
| 透明度 | ❌ 不生效 | ✅ `setAlpha(0.5f)` |
| 圆角/渐变 | ❌ 无此属性 | ✅ `GradientDrawable` |
| `dp` / `sp` 单位 | ✅ `width=42dp`、`textsize=16sp`、`elevation=4dp` | mjava setter 收 **px**，调用前自己换算 |
| 按屏宽比例计算 | — | ✅ |

**坑**：`weight=1` + `width=0` 会让控件宽度为 0（标题直接消失），必须写 `layout_weight`。

**`st_` 桥不归层，尽量不用**：它是 ppt 里直接调 Java setter（如 `st_setTextColor=16711680`），
只认整数、布尔字符串无效、无单位后缀无效（详见 `iyu-guide.md`）。静态样式优先用普通属性；
普通属性表达不了就进 mjava，不要用 `st_` 造第三种写法。

## 波纹（Ripple）

`RippleDrawable` 只能由 mjava 构造；**宿主控件 `clickable=true` 才会响应**（ppt 的 `clickable` 键有效）。

```java
android.content.res.ColorStateList ripple = android.content.res.ColorStateList.valueOf(
        android.graphics.Color.parseColor("#66FFFFFF"));
android.graphics.drawable.GradientDrawable bg = new android.graphics.drawable.GradientDrawable();
bg.setColor(android.graphics.Color.parseColor("#2196F3"));
bg.setCornerRadius(dp(24));
view.setBackground(new android.graphics.drawable.RippleDrawable(ripple, bg, null));
```

第三个参数是**遮罩**：行内水波纹要给一个不透明圆角矩形遮罩，否则涟漪会按无边界圆扩散成整圆；整块背景本身已是圆角时，可传 `null` 让内容 drawable 约束涟漪。

| 组合 | 现象 |
|---|---|
| RippleDrawable + `clickable=false` | 无波纹 |
| RippleDrawable + `clickable=true`（TextView / LinearLayout / Button） | 正常波纹 |
| Button + ppt `backgroundcolor` | 覆盖原生背景，原生波纹丢失 |

## 组合控件（Material / 自定义类）

**自定义控件默认就写在 ppt 里**（`type=` 全类名 + `build.xml` 登记）：实例真实可写，设计器也能看到
（API 34 实测；API 28 的旧结论是“影子实例”⚠，按版本差异对待）。外观差异只在子控件 Context
（TIL 按 `md-components-guide.md` 的 `loading` 配方修复），不需要整页改成 mjava 动态创建。
只有两种情况在 mjava 里 `new`：① 整类无法在 ppt 声明（必须带构造参数）；② ppt 路径实测不可用
（`SearchBar` 写进 ppt 后设计器保存/序列化时会崩，与登记无关；`TabLayout`/`ChipGroup`/`MaterialDivider` 已排除，见 `pitfalls.md` #7）。

## MD 风格输入框

用 `EditText` + `GradientDrawable`（圆角 + 描边），焦点态换描边色：

```java
view.setOnFocusChangeListener(new android.view.View.OnFocusChangeListener() {
    public void onFocusChange(android.view.View v, boolean focused) {
        // 重建 GradientDrawable，描边色 #3F51B5 / #CCCCCC
    }
});
```

实测：聚焦后边框变蓝；`setPadding` 用 dp 换算。
