# Material 组件（MD3）

> 选型先看 `material-components.md`：声明顺序是「ppt 完整类名 → ppt 短名 → mjava 动态创建」。
> 本文件讲 ppt 声明之后的修复与运行期填充细节。

版本前提：iApp 5.0.1013、API 34（TIL 修复实测环境），SDK 内含 material 1.13.0。

## 结论：ppt 里优先声明自定义控件，mjava 只做修复与内容填充

`type=` 写 Material 全类名（或短名）在 ppt 里声明，这是默认做法。运行时组件是真实实例
（API 34 实测：`findViewById` 拿到的就是屏幕上那个，`attached=true`，`addView` 生效）。

需要 mjava 的只有三类情况：

1. **修复**：`TextInputLayout` 的盒子默认不画（子控件带 activity 主题背景），按下面的 `loading` 配方修
2. **运行期内容**：文字、选项、tab、菜单、进度值、adapter —— ppt 属性表达不了
3. **整类无法 ppt 声明**：必须带构造参数的类，或 ppt 路径实测不可用
   （`SearchBar` 写进 ppt 后设计器保存/序列化时会崩，与登记无关；`TabLayout`/`ChipGroup`/`MaterialDivider` 已排除，见 `pitfalls.md` #7）。
   `Carousel` **不是**这类例子——它在内置 APK 里被裁剪，连 `(Context)` 构造都没有，mjava 也救不了

动态创建出来的控件**不用再登记** `build.xml`：登记只服务设计器，ppt 里没有它就不需要。

设计器“未知”：`type` 写完整类名（含点号）必须在 `build.xml` 的 `<newControl>` 里登记；
短名不用，新建工程的登记不继承（格式见 `project-structure.md`）。

### ppt 声明的 TIL：盒子默认不画（修复配方）

盒子默认不画。修复**必须挂在 `loading`**（`loadingComplete` 太晚，首帧会先画出无盒子的页面）：

```java
TextInputLayout til = (TextInputLayout) activity.findViewById(120);
TextInputEditText et = (TextInputEditText) til.getEditText();

TextInputEditText ref = new TextInputEditText(til.getContext()); // 取内置样式
float d = activity.getResources().getDisplayMetrics().density;
et.setTextSize(ref.getTextSize() / d);
et.setPadding(ref.getPaddingLeft(), ref.getPaddingTop(),
              ref.getPaddingRight(), ref.getPaddingBottom());
et.setBackground(null);                      // 去掉 activity 主题的原生下划线
til.updateEditTextBoxBackgroundIfNeeded();   // Material 把盒子贴回去
```

修完与 mjava 动态创建一致；关键是子控件用 `til.getContext()` 的字号/内边距，并去掉 activity 主题背景。

## 动态创建 TIL（仅当 ppt 不可用时）

```java
import android.widget.LinearLayout;
import com.google.android.material.textfield.TextInputLayout;
import com.google.android.material.textfield.TextInputEditText;

TextInputLayout til = new TextInputLayout(activity);
til.setHint("MD3 输入框");
til.setBoxBackgroundMode(TextInputLayout.BOX_BACKGROUND_OUTLINE);
TextInputEditText et = new TextInputEditText(til.getContext());   // 关键：用 layout 的 Context
et.setSingleLine(true);
til.addView(et, new LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT));
```

实测：该环境里资源名解析不到 M3 主题，`materialContext()` 回退到 activity；但上面这段仍拿到 `boxBackgroundMode=2`，布局后是描边框。

归因（✅ Context 对照）：

| 组 | 子控件构造 | 子控件 `ctxCls` | 外观 |
|---|---|---|---|
| 1 | `new TextInputEditText(activity)`，不单行 | `com.iapp.app.run.mian` | 原生下划线 |
| 2 | `new TextInputEditText(activity)`，单行 | 同上 | 原生下划线 |
| 3 | `new TextInputEditText(til.getContext())`，不单行 | `androidx.appcompat.view.ContextThemeWrapper` | outline |
| 4 | `new TextInputEditText(til.getContext())`，单行 | 同上 | outline |

- 所有 `TextInputLayout.getContext()` 都返回 `ContextThemeWrapper`：构造时被包了一层 Material 主题覆盖
- 子控件用 `activity` 构造会**绕过**这层覆盖，按 AppCompat 主题自绘背景
- 1 与 2 外观一致 → `setSingleLine` 不是因素
- 结论：**决定外观的是子控件拿到的 Context**

各模式回读：`110 mode=2`（outline）、`111 mode=1`（filled）、`112 mode=0`（none）、`113/114 mode=2`。

要点：

- `TextInputEditText` 必须是 `TextInputLayout` 的**直接子控件**；TIL 会把它放进自己的 `inputFrame`，那层 `FrameLayout` 是组件内部的，不是 iApp 套的
- 子控件一定要用 `til.getContext()` 构造（即使 layout 用的是 activity）
- `setSingleLine(true)`
- `setBoxBackgroundMode(BOX_BACKGROUND_OUTLINE)` 得到描边框；iApp 5.0.1013 里未显式设置时回读也是 `mode=2`（outline），但显式设置更稳
- 若能把主题 id 解析出来，用 `ContextThemeWrapper(activity, themeId)` 构造 layout 更稳；iApp 5.0.1013 的资源名下解析不到（`getIdentifier("Theme_Material3_*","style",pkg)` 返回 0）

## TextInputLayout 常用参数（✅ 实测可设可读）

| 参数 | 调用 | 说明 |
|---|---|---|
| box 模式 | `setBoxBackgroundMode(...)` | `OUTLINE=2`、`FILLED=1`、`NONE=0`，`getBoxBackgroundMode()` 可回读 |
| 提示 | `setHint(...)` | 浮标文本 |
| 辅助文字 | `setHelperText(...)` | — |
| 错误 | `setErrorEnabled(true)` + `setError(...)` | — |
| 字数 | `setCounterEnabled(true)` + `setCounterMaxLength(n)` | — |
| 前后缀 | `setPrefixText("https://")` / `setSuffixText(".com")` | 配合 `BOX_BACKGROUND_NONE` 可用 |
| 描边 | `setBoxStrokeColor(color)` / `setBoxStrokeWidth(dp)` | 需 OUTLINE |
| 圆角 | `setBoxCornerRadii(l,t,r,b)` | 需 OUTLINE |
| 密码显隐 | `setEndIconMode(TextInputLayout.END_ICON_PASSWORD_TOGGLE)` | 子控件 `setInputType(TEXT_PASSWORD)` |

## 其它组件（mjava 动态创建实测可用；默认仍先试 ppt）

| 组件 | 类 | 备注 |
|---|---|---|
| 按钮 | `com.google.android.material.button.MaterialButton` | 圆角胶囊；可用 `setCornerRadius` / `setBackgroundTintList` / `setStrokeWidth`+`setStrokeColor` 逼近 filled/tonal/outlined/text |
| 卡片 | `com.google.android.material.card.MaterialCardView` | 默认无内容内边距，需 `setContentPadding` |
| 标签 | `com.google.android.material.chip.Chip` | `setText` 后要 `setClickable(true)`；`setCheckable(true)` 做 filter/choice |
| 开关 | `com.google.android.material.switchmaterial.SwitchMaterial` | — |
| 复选框 | `com.google.android.material.checkbox.MaterialCheckBox` | — |
| 单选框 | `com.google.android.material.radiobutton.MaterialRadioButton` | — |
| 滑块 | `com.google.android.material.slider.Slider` | `setValueFrom/To/Value` |
| 圆形进度 | `com.google.android.material.progressindicator.CircularProgressIndicator` | `setIndeterminate(true)` |
| 线性进度 | `com.google.android.material.progressindicator.LinearProgressIndicator` | `setIndeterminate(true)` |
| 悬浮按钮 | `com.google.android.material.floatingactionbutton.FloatingActionButton` | 无图标时显示为空色块 |

## 主题现状（实测）

- `accent=#ff4081`（AppCompat 粉）、`primary=#6750a4`（M3 基线紫）→ 混合主题
- `com.google.android.material.R$style` / `R$attr` 类被裁，反射枚举 M3 主题不可行
- `getIdentifier("Theme_Material3_DayNight","style",pkg)` 返回 0（资源名不在应用包下）；`ContextThemeWrapper` 方案在 iApp 5.0.1013 不可用，回退到 activity 仍可得到 outline

## 时序

- 载入事件里子控件 `isAttachedToWindow()` 仍为 false（尚未 attach），不是失败
