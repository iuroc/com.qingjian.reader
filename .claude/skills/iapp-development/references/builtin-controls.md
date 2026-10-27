# 内置短名控件

`type` 直接写短名，不需要在 `build.xml` 登记。

> **Material 组件优先写全类名**：本表的短名里有一部分指向 iApp 封装或 androidx
> （`TabLayout`、`CardView`、`SwitchCompat`、`Toolbar`），外观/能力不等于 Material。
> 选型规范与支持矩阵见 `material-components.md`。
下表是**运行时实测**的「短名 → 实际类」（iApp 5.0.1013 / API 28）。

写 mjava 时**导入路径照抄这张表的“实际类”**，不要按 `android.widget.*` 猜（见 `pitfalls.md` 第 12 条）。

| 短名 | 实际类 |
|---|---|
| `Button` | `android.widget.Button` |
| `WebView` | `android.webkit.WebView` |
| `TextView` | `android.widget.TextView` |
| `ImageView` | `android.widget.ImageView` |
| `ImageButton` | `android.widget.ImageButton` |
| `EditText` | `android.widget.EditText` |
| `RadioGroup` | `android.widget.RadioGroup` |
| `RadioButton` | `android.widget.RadioButton` |
| `CheckBox` | `android.widget.CheckBox` |
| `ListView` | `android.widget.ListView` |
| `Spinner` | `android.widget.Spinner` |
| `VideoView` | `android.widget.VideoView` |
| `GifView` | `pl.droidsonroids.gif.GifImageView` |
| `RoundImageView` | `com.iapp.app.RoundImageView` |
| `RatingBar` | `android.widget.RatingBar` |
| `SeekBar` | `android.widget.SeekBar` |
| `ProgressBar` | `android.widget.ProgressBar` |
| `DatePicker` | `android.widget.DatePicker` |
| `TimePicker` | `android.widget.TimePicker` |
| `GridView` | `android.widget.GridView` |
| `LinearLayout` | `android.widget.LinearLayout` |
| `RelativeLayout` | `android.widget.RelativeLayout` |
| `TableLayout` | `android.widget.TableLayout` |
| `TableRow` | `android.widget.TableRow` |
| `FrameLayout` | `android.widget.FrameLayout` |
| `SurfaceView` | `android.view.SurfaceView` |
| `ScrollView` | `android.widget.ScrollView` |
| `HorizontalScrollView` | `android.widget.HorizontalScrollView` |
| `ViewPager` | `androidx.viewpager.widget.ViewPager` |
| `DrawerLayout` | `androidx.drawerlayout.widget.DrawerLayout` |
| `CoordinatorLayout` | `androidx.coordinatorlayout.widget.CoordinatorLayout` |
| `AppBarLayout` | `com.google.android.material.appbar.AppBarLayout` |
| `CollapsingToolbarLayout` | `com.google.android.material.appbar.CollapsingToolbarLayout` |
| `Toolbar` | `androidx.appcompat.widget.Toolbar` |
| `FloatingActionButton` | `com.google.android.material.floatingactionbutton.FloatingActionButton` |
| `NestedScrollView` | `androidx.core.widget.NestedScrollView` |
| `TabLayout` | `com.iapp.app.TabLayout` |
| `RecyclerView` | `androidx.recyclerview.widget.RecyclerView` |
| `ConstraintLayout` | `androidx.constraintlayout.widget.ConstraintLayout` |
| `VerticalViewPager` | `fr.castorflex.android.verticalviewpager.VerticalViewPager` |
| `SwipeRefreshLayout` | `androidx.swiperefreshlayout.widget.SwipeRefreshLayout` |
| `TextInputLayout` | `com.google.android.material.textfield.TextInputLayout` |
| `SwitchCompat` | `androidx.appcompat.widget.SwitchCompat` |
| `CardView` | `androidx.cardview.widget.CardView` |

## 注意

- **`Switch` 不是内置短名**，开关用 `SwitchCompat`
- 短名不是简单去包名：`GifView`、`RoundImageView`、`TabLayout`、`VerticalViewPager` 是封装类
- 设计器显示“未知” = 短名不存在，或 `type` 写了完整类名但没在 `build.xml` 登记
- 清单可能不完整；未列出的类写完整类名，并在**每个工程**各自登记（登记不继承）

## 布局约束

- `DrawerLayout` 必须用**精确尺寸**（如 `300dp × 300dp`）；`-1/-2` 会崩：
  `java.lang.IllegalArgumentException: DrawerLayout must be measured with MeasureSpec.EXACTLY.`
- 探针页里把它单独隔离，别和一批 wrap_content 控件混排
