# Material 组件选型与支持矩阵

版本前提：iApp 5.0.1013 / API 34；工程 `sdk/iapp.sdk` 内置 `com.google.android.material:material:1.13.0`
（APK 内 490 个 `com/google/android/material/` 类）。

## 选型规范（按顺序）

1. **ppt 里声明：`com.google.android.material.*` 完整类名**
   - `.iyu` 的 `type=` 写全类名，并在 `build.xml` 登记
   - 理由：设计器能看到控件树与预览，布局在编辑阶段就能验证；mjava 只补颜色、内容和 ppt 表达不了的配置
   - 分工：尺寸/边距/权重/文本写在 ppt；tint、描边、选中态、运行期内容由 mjava 补。`padding` 在 ppt 里是 px，不是 dp
   - 运行期内容（文字、选项、tab、菜单、进度值、adapter）在 mjava 里填，**不改变声明方式**
2. **ppt 短名兜底**：没有可靠 Material 映射时使用；注意部分短名指向 iApp 封装或 androidx
3. **mjava 动态创建仅限两种**：① 整类无法在 ppt 声明（**必须带构造参数**）；② ppt 路径经实测不可用
   （`SearchBar` 写进 ppt 后设计器保存/序列化时会崩，与登记无关；`TabLayout`/`ChipGroup`/`MaterialDivider` 已排除，见 `pitfalls.md` #7）。
   适配器**不是**理由（`RecyclerView` 可在 ppt 声明后 `setAdapter`）。**不要因为“保险”把整页改成 mjava 创建**
4. **判断依据**：`type` 值含点号 → 完整类名 → 登记；无点号 → 短名 → 先查 `builtin-controls.md` 指向哪个类

### 短名与 Material 类的差异（必须知道）

| 短名 | 实际类 | 结论 |
|---|---|---|
| `CardView` | `androidx.cardview.widget.CardView` | 要 M3 卡片 → `MaterialCardView` |
| `SwitchCompat` | `androidx.appcompat.widget.SwitchCompat` | 要 M3 开关 → `MaterialSwitch` / `SwitchMaterial` |
| `Toolbar` | `androidx.appcompat.widget.Toolbar` | 要 M3 工具栏 → `MaterialToolbar` |
| `TabLayout` | `com.iapp.app.TabLayout` | **iApp 封装**，不是 Material TabLayout |
| `RecyclerView` | `androidx.recyclerview.widget.RecyclerView` | 没有 Material 对应物，保留 |
| `AppBarLayout` / `CollapsingToolbarLayout` / `FloatingActionButton` / `TextInputLayout` | 直接就是 material 类 | 短名与全类名等价 |

其余 Material 组件（`MaterialButton`、`Chip`、`Slider`、`MaterialCheckBox`、`MaterialRadioButton`、
`SwitchMaterial`、`TextInputEditText`、两个 Progress、`MaterialCardView`、`MaterialToolbar` …）
**没有短名**，只能写完整类名。

## 支持矩阵

状态定义（2026-10-27 实测）：

- ✅ **上屏可见**：默认就有可见外观（已渲染验证）
- ⚪ **可上屏但默认空白**：能构造、能 attach，但需要内容/属性才显形（容器类）
- ❌ **不可用**：iApp 5.0.1013 的内置 APK 里不可构造

### 可直接当控件用

| 组件 | 完整类名 | 状态 | 备注 |
|---|---|---|---|
| 按钮 | `com.google.android.material.button.MaterialButton` | ✅ | `setCornerRadius` / `backgroundTintList` / `setStrokeWidth(int)` + `setStrokeColor(ColorStateList)` |
| 分段按钮容器 | `...button.MaterialButtonToggleGroup` | ✅ | `did` 挂 `MaterialButton` 子控件；`setSingleSelection` |
| 分离按钮 | `...button.MaterialSplitButton` | ⚪ | 继承 `MaterialButtonGroup`，`REQUIRED_BUTTON_COUNT=2`：必须挂**恰好 2 个** `MaterialButton` 子按钮，否则空白 |
| 卡片 | `...card.MaterialCardView` | ✅ | `did` 挂子控件；`setContentPadding` |
| 复选 | `...checkbox.MaterialCheckBox` | ✅ | 配色随 activity 主题 |
| 单选 | `...radiobutton.MaterialRadioButton` | ✅ | 需放进 `android.widget.RadioGroup` |
| 开关 | `...switchmaterial.SwitchMaterial` | ✅ | M2 命名；M3 用 `MaterialSwitch` |
| M3 开关 | `...materialswitch.MaterialSwitch` | ✅ | 胶囊+圆形滑块，默认可见 |
| 标签 | `...chip.Chip` | ✅ | `setCheckable(true)`；`st_` 桥设不了布尔 |
| 标签组 | `...chip.ChipGroup` | ⚪ | 空容器，需 Chip 子项 |
| 滑块 | `...slider.Slider` | ✅ | `setValueFrom/To/StepSize/Value` |
| 区间滑块 | `...slider.RangeSlider` | ✅ | 默认单 thumb 可见；双值用 `setValues(...)` |
| 线性进度 | `...progressindicator.LinearProgressIndicator` | ✅ | `setIndeterminate(true)` |
| 圆形进度 | `...progressindicator.CircularProgressIndicator` | ✅ | 同上 |
| 加载指示 | `...loadingindicator.LoadingIndicator` | ✅ | 1.13 新增 |
| FAB | `...floatingactionbutton.FloatingActionButton` | ✅ | 无图标时是空色块 |
| 扩展 FAB | `...floatingactionbutton.ExtendedFloatingActionButton` | ✅ | 胶囊底可见；内容需 `setText`/图标 |
| 输入框容器 | `...textfield.TextInputLayout` | ✅（需修复） | 见下节 |
| 输入框 | `...textfield.TextInputEditText` | ✅ | 用 `til.getContext()` 构造 |
| 自动完成 | `...textfield.MaterialAutoCompleteTextView` | ⚪ | 默认无背景，需 hint/背景 + adapter |
| 工具栏 | `...appbar.MaterialToolbar` | ⚪ | 需 `setTitle` 才显形 |
| 应用栏 | `...appbar.AppBarLayout` | ✅ | `onoffsetchanged`、`st_vO` 可用 |
| 折叠栏 | `...appbar.CollapsingToolbarLayout` | ⚪ | 需标题/配 AppBarLayout |
| 底部应用栏 | `...bottomappbar.BottomAppBar` | ✅ | 底栏可见，常配 FAB |
| 底部导航 | `...bottomnavigation.BottomNavigationView` | ✅ | 底栏可见；选项需 menu |
| 侧边导航 | `...navigationrail.NavigationRailView` | ⚪ | 需 menu 才显形 |
| 抽屉导航 | `...navigation.NavigationView` | ⚪ | 需 menu / header |
| 标签页 | `...tabs.TabLayout` | ✅ | 基线可见；页签需 `newTab()` |
| 搜索栏 | `...search.SearchBar` | ✅（运行期） | 胶囊+搜索图标可见；**ppt 声明后设计器保存/序列化时会崩（`VisualDesigner.T0`，与登记无关），只能 mjava 动态创建** |
| 搜索视图 | `...search.SearchView` | ⚪ | 默认折叠不可见，需展开/配置 |
| 轮播 | `...carousel.Carousel` | ❌ | iApp 5.0.1013 的内置 APK 里被裁剪：无 `<init>`，只剩 5 个 getter；**ppt 和 mjava 都不可用，不能当动态创建的例子** |
| 遮罩容器 | `...carousel.MaskableFrameLayout` | ⚪ | 空容器 |
| 分隔线 | `...divider.MaterialDivider` | ✅ | 细线可见 |
| 可塑图片 | `...imageview.ShapeableImageView` | ⚪ | 需图片 drawable |
| 拖拽把手 | `...bottomsheet.BottomSheetDragHandleView` | ✅ | 把手可见 |

> ⚪ 项在正式页面里必须补内容/属性，否则是一片空白。首次使用先做最小上屏探针。

### ⚪ 空容器补内容速查

| 组件 | 补什么 |
|---|---|
| `MaterialSplitButton` | 恰好 2 个 `MaterialButton`（`REQUIRED_BUTTON_COUNT=2`） |
| `ChipGroup` | `Chip` 子项 |
| `TabLayout`（✅ 但需页签） | `newTab().setText(...)` |
| `BottomNavigationView` | `inflateMenu` / menu 项 |
| `NavigationRailView` | menu |
| `NavigationView` | menu + 可选 header |
| `MaterialToolbar` | `setTitle`（或 menu） |
| `CollapsingToolbarLayout` | 标题，通常配 `AppBarLayout` |
| `MaterialAutoCompleteTextView` | hint/背景 + adapter |
| `SearchView` | 展开/配置后才有内容 |
| `MaskableFrameLayout` | 子 View |
| `ShapeableImageView` | 图片 drawable + shapeAppearance |

判断口诀：**空白先看它是不是容器/菜单型组件**，是就补内容；内容补了还空白，才是真问题。

### 不是控件的 Material API（mjava 里用）

`Snackbar`、`MaterialAlertDialogBuilder`、`BottomSheetDialog`、`SideSheetDialog`、
`MaterialDatePicker` / `MaterialTimePicker`、`BadgeDrawable`、`TabLayoutMediator` —— 都不是 View，
不能写进 ppt 的 `type=`。

## 样式注意

- 工程主题是 AppCompat 混合主题，**不是 Material 3**；组件默认色不会自动变成 M3 token，
  要 M3 观感需手动设 `ColorStateList` / tint
- ppt 声明的组件子控件用 activity Context：`TextInputLayout` 按 `md-components-guide.md` 的 `loading` 配方修复，
  其它组件（复选/单选/开关/Chip）配色也随 activity 主题
- ppt 全类名控件的 Context 分组（API 34 实测）：`MaterialButton` / `Chip` / `FAB` / `TextInputLayout`
  自带 `ContextThemeWrapper`；`MaterialCardView` / `MaterialCheckBox` / `MaterialRadioButton` /
  `SwitchMaterial` / `Slider` / 两个 Progress / `MaterialButtonToggleGroup` 拿到的是 activity
  （`com.iapp.app.run.mian`），配色随 activity 主题，不是 M3 token
- `st_` 桥只认数值参数；布尔字符串（`st_setChecked=true`）无效
- `MaterialButton.setStrokeColor` **只有 `ColorStateList` 重载**：传 int 抛
  `Method setStrokeColor( int ) not found in class '...MaterialButton'`，并中断整个载入事件
  （2026-10-27 实测，material 1.13.0）。描边写法：`btn.setStrokeWidth(dp(1)); btn.setStrokeColor(ColorStateList.valueOf(color))`
- 这类中断会**静默跳过同一 `loading` 事件里后面所有区块**：表现是“后面的控件没上色 / 输入框没盒子”，
  报错行却指向前面的按钮。`try/catch(Throwable)` **接不住**（实测：加了 try/catch 仍在
  `setIndicatorColor(int)` 处中断，日志里没有 catch 输出），只能事先核对重载，并把可疑调用放到初始化最后
- `LinearProgressIndicator` / `CircularProgressIndicator` 的 `setIndicatorColor` 是 `int...` 可变参数：
  **单值 `int` 会抛 `Method setIndicatorColor( int ) not found` 并中断，传 `int[]` 则正常** ✅
  （2026-10-27，`setIndicatorColor(new int[]{color})` 后日志打出 `M3 init done`）。`setTrackColor(int)` 正常 ✅

## 验证方法

```bash
# 静态：哪些 Material 类有 (Context) 构造（APK 用你自己设备的 iApp APK）
python scripts/material_scan.py <你的 iApp APK>

# 静态：某个类自己声明了哪些方法（只核对不确定的 API，别抄表）
python scripts/class_methods.py <你的 iApp APK> com/google/android/material/slider/

# 运行时逐类构造：自己建一个探针页 + mjava，日志打一个自定义 tag
# 运行时上屏画廊：同上，逐类 addView 并截图
adb logcat -d -v time 'ygs:V' '*:S' | grep '<你的 tag>'
```

- 构造扫描：35 个候选 34 个可用 `(Context)` 构造，`Carousel` 被裁剪
- 上屏画廊：20 个待验证项 **20/20 构造并 attach 成功**，无崩溃/重叠（10 个默认可见，10 个空容器）
- 反射加载应用内类必须用 `activity.getClassLoader().loadClass(name)`；`Class.forName` 在 BeanShell 里看不到应用类
- `class_methods.py` **只列类自身声明的方法**：`setThumbTintList` 来自 `CompoundButton`，查不到 ≠ 不存在。
  核对它是为了确认**该版本 iApp 的内置 APK** 里 API 还在（APK 会被裁剪，`Carousel` 就是先例），不是用来维护 API 表
- Material API 的调用约定（varargs 不可用、方法不存在会中断）见 `mjava-guide.md` 铁律表

升级 iApp（material 版本变化）后重跑这两步，矩阵要重新标定。
