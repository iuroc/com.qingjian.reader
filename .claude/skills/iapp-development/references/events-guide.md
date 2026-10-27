# 事件

## 权威名单（来自 `com.iapp.app.VisualDesigner.<init>`）

iApp 设计器支持的事件类型就是下面这些，`<eventItme type="…">` 只能写名单内的名字。

### 控件事件

| 组 | 名称 |
|---|---|
| 勾选 | `oncheckedchanged` |
| 偏移 | `onoffsetchanged` |
| 点击类 | `clicki` `touchmonitor` `press` `keyboard` `pressmenu` |
| 编辑 | `editormonitor` `ontextchanged` `beforetextchanged` `aftertextchanged` |
| 焦点 | `focuschange` |
| 滚动 | `onscrollstatechanged` `onscrolled` `onscroll` |
| 列表 | `clickitem` `onitemselected` `onnothingselected` |
| 浏览器 | `onprogresschanged` `shouldoverrideurlloading` `onpagestarted` `onpagefinished` `onreceivederror` `ondownloadstart` |
| 分页 | `onpageselected` `onpagescrolled` `onpagescrollstatechanged` |
| 抽屉 | `ondrawerclosed` `ondraweropened` `onoptionsitemselected` |
| 拍照 | `onpicturecallback` |
| 拖动条 | `onstarttrackingtouch` `onstoptrackingtouch` `onprogresschanged2` |
| Tab | `ontabselected` `ontabunselected` `ontabreselected` |
| 下拉刷新 | `onrefresh` |

### 界面事件（`<UIEventset>`）

`loading` `loadingComplete`
`resume` `pause` `start` `stop` `restart` `destroy`
`downkey` `upkey` `menu`
`sensor` `onactivityresult` `onrequestpermissionsresult`

注意：

- **载入完毕是 `loadingComplete`**（驼峰），不是 `loadingend`
- **没有 `androidResume/androidPause/...`**：dex 里那些 `android*` 字符串不是设计器事件名，写进 `.iyu` 不会触发
- **事件名写错不报错**：`onreceivedtitle`、`onloadresource`、`onconsolemessage` 这类不存在的名字，iApp 静默忽略（没有 YuErr、也没有回调）。只能对照上面这张名单自查
- `onactivityresult` / `onrequestpermissionsresult` 在名单里，但参数形状未系统验证；要拿精确结果优先在 mjava 里用原生回调/`requestPermissions` 配合
- `sensor` 的 `st_x/st_y/st_z` 来自 DEX 推断，运行期未验 ❓
- 编写时遵守 iyu 白名单：事件体只写 `call` / `addv`

## 事件内置变量（`st_*`，DEX 证实）

事件代码执行前，iApp 把本次事件的参数塞进 yul 变量（`qm.Z(name,value)`），名字统一 `st_` 前缀。
**这是把事件参数传给 mjava 的唯一正确途径**——写别的名字（如 `url`、`position`）都是未定义变量。

| 变量 | 含义 | 出现在 |
|---|---|---|
| `st_vId` | 控件 id（int） | 几乎所有控件事件 |
| `st_vW` | 控件 View 本身 | 几乎所有控件事件 |
| `st_pN` | 位置 position | `clickitem` `onitemselected` `ontab*` `onpage*` |
| `st_iD` | 行 id（long） | `clickitem` `onitemselected` |
| `st_iC` | 是否勾选（boolean） | `oncheckedchanged` |
| `st_hF` | 是否有焦点（boolean） | `focuschange` |
| `st_nS` / `st_fR` | 进度值 / 是否用户操作 | SeekBar `onprogresschanged2` |
| `st_fM` / `st_vT` / `st_bT` | 首个可见项 / 可见数 / 总数 | ListView `onscroll` |
| `st_sE` | 滚动状态 | `onscrollstatechanged` `onpage*` |
| `st_vO` | 偏移量 | `onoffsetchanged` |
| `st_url` | 目标网址 | WebView `shouldoverrideurlloading` `onpagestarted` `onpagefinished` |
| `st_bP` | favicon（Bitmap） | WebView `onpagestarted` |
| `st_eA` / `st_eX` / `st_eY` / `st_rX` / `st_rY` | 动作 / 坐标 / 原始坐标 | 触摸类 |
| `st_eR` / `st_kC` / `st_eK` | 按键相关字段 | `keyboard` `editormonitor` |
| `st_x` / `st_y` / `st_z` | 三轴数值 | `sensor` |

用法：

```xml
<eventItme type="clickitem">call(null, "mjava", "fm.onItem", st_pN)</eventItme>
```

写错变量名的后果不是报错，而是**这个参数被丢掉**：`call(..., url)` → 实际调用 `override()` 零参 → `JavaErr: Method override() not found`。

## 运行期已确认触发

| 事件 | 触发条件 |
|---|---|
| `loading` | 打开界面 |
| `clicki` | 单击 |
| `touchmonitor` | 触摸（单击、长按都会） |
| `press` | 长按 |
| `keyboard` | 每次按键（高频） |
| `editormonitor` / `beforetextchanged` / `ontextchanged` / `aftertextchanged` | 文本变化，顺序固定 |
| `focuschange` | 获得/失去焦点 |
| `oncheckedchanged` | CheckBox / SwitchCompat 勾选变化 |
| `onpagestarted` `onprogresschanged` `onpagefinished` `onreceivederror` | WebView 加载 |
| `loadingComplete` | 界面可交互（`loading` 之后） |
| `start` / `resume` | 打开界面、从后台回到前台 |
| `pause` / `stop` | 按 Home 退到后台 |
| `restart` | 从后台回到前台（在 `start/resume` 之前） |
| `downkey` / `upkey` | 物理/导航按键的按下与释放（一次按键成对出现） |
| `ontabselected` / `ontabunselected` / `ontabreselected` | TabLayout 切换 / 重按当前 tab |
| `ondraweropened` / `ondrawerclosed` | 抽屉打开 / 关闭 |
| `destroy` | 退出页面 |

实测顺序：打开 `loading → start → loadingComplete`；Home `pause → stop`；回来 `restart → start → resume`。

## 按键参数（downkey / upkey）✅

事件体可以直接用这三个变量，当作 `call` 的参数传进 mjava：

| 变量 | 含义 |
|---|---|
| `st_kC` | 键码（Android `KeyEvent.KEYCODE_*` 数值） |
| `st_eA` | 动作（KeyEvent action） |
| `st_eR` | 重复计数 |

```xml
<UIEventset><eventItme type="downkey">
call(null, "mjava", "game.keyCode", st_kC)
</eventItme></UIEventset>
```

方向键实测键码：`19` 上、`20` 下、`21` 左、`22` 右。

要点：

- 不传 `st_kC` 时事件体照样触发，但 mjava 拿不到按的是哪个键
- **这一条入口就够**：2026-10-26 隔离复核把 `setOnKeyListener` 注释掉，方向键仍全部生效 ✅
- 不要同时挂 `setOnKeyListener`（可能双触发）；真要兜底，在 mjava 按 `(键码, 120ms)` 去抖
- 长按会重复触发 `downkey`，同样用去抖吞掉
- 非方向键（Ctrl、字母键、返回键）也会进 `downkey`，在 mjava 里过滤即可
- **绑了 `downkey` 就等于接管了返回键**：返回键码 `4` 会进事件，但页面**不再自动弹出**（与 `shouldoverrideurlloading` 同款）。要自定义返回就 `call` 到 mjava，在 mjava 里判 `kc == 4` 后 `activity.finish()` ✅（API 34）
- 反编译 `main2` 的 UIEventset 参数表为 `st_kC,st_eA,st_eR`；方向键在 API 28 实测（2026-10-26）

## touchmonitor 能拿到什么 ⚠/❓

反编译 `main2$i.onTouch`（裕 3 运行期）能看到它给事件体派发一组**位置参数**：

```
view、view id、action、x、y、rawX、rawY
```

- 事件体一定会触发（单击、长按都算），这是 ✅ 的
- DEX 里派发的是 `view / id / action / x / y / rawX / rawY`；对应变量名推测为 `st_eX` / `st_eY` / `st_rX` / `st_rY`，但**运行期未验证在事件体里能否取到** ❓
- 需要坐标/方向时，直接改用 mjava：

```java
board.setOnTouchListener(new View.OnTouchListener() {
    public boolean onTouch(View v, MotionEvent e) {
        int act = e.getAction();   // 0=DOWN 1=UP
        // e.getX() / e.getY() / e.getRawX() / e.getRawY()
        return true;
    }
});
```

API 28 实测（2026-10-26）：这套写法可用，回调里可以直接调同模块方法。

**多点触控（API 28 实测）**：`getActionMasked()`、`getActionIndex()`、`getPointerCount()`、`getPointerId(i)`、`findPointerIndex(id)`、`getX(int)` / `getY(int)` 都能在 BeanShell 里解析。
但 `getHistorySize(int)` / `getHistoricalX(int,int)` 这些**带 pointerIndex 的重载会解析失败并杀进程**（`catch` 接不住），只用无参 `getHistorySize()`。
API 28 实测（2026-10-26）。

## 滚动 / 列表事件（✅ 实测）

| 控件 | 事件 | 结果 |
|---|---|---|
| ListView | `onscroll` | ✅ 高频 |
| ListView | `onscrollstatechanged` | ✅ |
| ListView | `onscrolled` | ❌ 不触发 |
| ListView | `clickitem` | ✅ |
| Spinner | `onitemselected` | ✅（非空列表） |
| Spinner | `onnothingselected` | ❌ 空列表点开、先选后清空，两种条件都不触发 |
| ScrollView | `onscroll/onscrolled/onscrollstatechanged` | ❌ 不触发 |
| WebView | 同上 | ❌ 不触发 |

结论：滚动事件绑在**列表型控件**上；`onscrolled` 大概只属于 RecyclerView（待验）。

## 拖动条 / 下拉刷新（✅ 实测）

| 控件 | 事件 | 结果 |
|---|---|---|
| SeekBar | `onstarttrackingtouch` | ✅ 手指按下时一次 |
| SeekBar | `onprogresschanged2` | ✅ 每次进度变化；`setProgress()` 程序化设置也触发 |
| SeekBar | `onstoptrackingtouch` | ✅ 抬手时一次 |
| SeekBar | `onprogresschanged` | ❌ 不触发（该名字属于浏览器组） |
| SwipeRefreshLayout | `onrefresh` | ✅ 下拉到位触发 |

注意：

- SeekBar 一律用 `onprogresschanged2`；一次拖动会产生十几次回调，别在里面做重活
- `onrefresh` 里**必须自己调 `setRefreshing(false)`**，否则下拉动画一直转。完整写法：

```java
public void onrefresh() {
    SwipeRefreshLayout sw = (SwipeRefreshLayout) activity.findViewById(42);
    sw.setRefreshing(false);
}
```

## Spinner 初始化会自动回调一次

`setAdapter()` 之后 `onitemselected` 立即触发一次（默认第 0 项）。所以“用户选了”和“刚设完数据”在回调里长得一样：

- 首次回调不要当成用户操作（比如别在里面弹提示）
- 需要区分时用标志位，或用 `onTouch`/`clicki` 判断是否用户主动打开

## WebView（✅ 实测）

| 事件 | 结果 |
|---|---|
| `onpagestarted` / `onprogresschanged` / `onpagefinished` | ✅ 加载全过程都能收到 |
| `onreceivederror` | ✅ 收到（错误页）；**只带 `st_vId` / `st_vW`，没有错误码** |
| `shouldoverrideurlloading` | ✅ 点链接就触发，变量 `st_url` 是目标地址 |
| `ondownloadstart` | ❌ 绑了 `shouldoverrideurlloading` 时到不了；未绑时未验 ❓ |

**关键机制（DEX 证实）**：`run/mian$i0.shouldOverrideUrlLoading` 分两条路——

- **没绑这个事件**：iApp 自己处理，`http/https/rtsp/ftp` → `webView.loadUrl(url)`，其它 scheme → `startActivity(ACTION_VIEW)`。所以默认点链接是会跳的
- **绑了这个事件**：先执行你的 yul 代码，然后**直接 `return true`**，默认跳转完全被跳过。想跳就得自己写

```xml
<eventItme type="shouldoverrideurlloading">call(null, "mjava", "br.override", st_url)</eventItme>
```

```java
public void override(Object u) {
    String url = String.valueOf(u);
    if (url.startsWith("http")) {
        ((WebView) activity.findViewById(20)).loadUrl(url);
    }
}
```

注意：事件体里写 `url` 是**未定义变量**，调用会退化成 `override()` 零参 → `JavaErr: Method override() not found`。必须用 `st_url`。

补充（API 28 实测）：

- `canGoBack()` / `goBack()` 正常；返回栈自己维护
- `onprogresschanged` 到 100 会回调**多次**（一次加载常见 3 次），不要在 100 做重活
- `loadDataWithBaseURL` 打开的本地页，`getUrl()` 返回 `about:blank`，不要靠它判断当前页
- 老设备 WebView 内核可能较旧（例如 Chrome 91），前端按对应能力写，别用太新的 CSS/JS

## 抽屉 / 页面销毁（✅ 实测）

| 事件 | 结果 |
|---|---|
| `ondraweropened` | ✅ 程序化 `openDrawer` 和手势打开都回调 |
| `ondrawerclosed` | ✅ 程序化 `closeDrawers` 和点抽屉外关闭都回调 |
| 界面 `destroy` | ✅ 退出页面时触发 |

DrawerLayout 在 ppt 里给精确尺寸（如 `320dp × 300dp`），内容区和抽屉在 mjava 里 `addView` 动态塞。

## 不可依赖的事件

| 事件 | 实测情况 |
|---|---|
| `pressmenu` | ❌ Button 单击/长按都正常，长按菜单事件多次按压一次都不触发 |
| `onnothingselected` | ❌ 空列表点开、先选后清空都不触发 |
| 界面 `menu` | ❌ 模拟器无菜单键，未触发（真实设备未验） |

`pressmenu` 想要“长按弹菜单”，改用 `press` 自己在 mjava 里 `AlertDialog` / `PopupMenu`。

## ViewPager 翻页事件（✅ 实测）

前提：**适配器必须是编译类**。`PagerAdapter` 是抽象类，BeanShell 只能实现接口、
不能继承类，所以要写一个 `.java` 编成 dex 再加载（配方见
`external-library-guide.md` 的「编译类进 dex」）。加载时 `DexClassLoader` 的父加载器
**要给宿主 loader**，因为 `androidx.viewpager.*` 在宿主里。

| 事件 | 触发条件 | 参数 |
|---|---|---|
| `onpageselected` | 手势翻页、`setCurrentItem(n,true)` 都触发 | 1 个：`st_pN` = 页码（0 基，准确） |
| `onpagescrolled` | 高频，一次翻页十几次 | 2 个：`st_pN` = 页码；第二个 `st_vO` **恒为 null**（偏移量拿不到） |
| `onpagescrollstatechanged` | 每次滚动都成组 | 1 个：`st_sE` = 0 静止 / 1 拖拽 / 2 回弹 |

事件顺序（实测时间戳）：`state 1 → state 2 → sel → state 0`；
程序化 `setCurrentItem(n, true)` 同样会走这一串。

```xml
<View id="20" type="ViewPager">
<event><eventItme type="onpageselected">call(null, "mjava", "vp.onSel", st_pN)</eventItme>
<eventItme type="onpagescrolled">call(null, "mjava", "vp.onScroll", st_pN)</eventItme>
<eventItme type="onpagescrollstatechanged">call(null, "mjava", "vp.onState", st_sE)</eventItme></event>
</View>
```

注意：

- `onpagescrolled` 频率与 `onscroll` 同级，回调里别做重活
- `VerticalViewPager` 是否同样支持这三个事件未测 ❓
- 想确认某个事件的参数个数：在 mjava 里写 0/1/2 参重载（`onSel()` / `onSel(Object p)` / `onSel(Object p, Object o)`），iApp 注入几个就命中哪个；命中哪档本身就是读数

## AppBarLayout 偏移（✅ 实测）

| 事件 | 触发条件 | 参数 |
|---|---|---|
| `onoffsetchanged` | 手势滚动、`setExpanded(...)` 程序化折叠/展开都触发；频率高 | 1 个：`st_vO` = **真实偏移量（px，负值）** |

- 实测范围 `0 → -360`（标题条 120dp × density 3），`getTotalScrollRange()` 同值
- 参数不会被丢：日志里从没出现 0 参重载
- 结构按标准来：`CoordinatorLayout` → `AppBarLayout`（绑事件）+ 嵌套滚动子视图
  （`NestedScrollView`）；子视图的 `CoordinatorLayout.LayoutParams`
  要 `setBehavior(new AppBarLayout.ScrollingViewBehavior())`，否则内容会压在标题条下面
- AppBarLayout 的**子视图**必须用 `AppBarLayout.LayoutParams` 并 `setScrollFlags(
  SCROLL_FLAG_SCROLL | SCROLL_FLAG_ENTER_ALWAYS)`，否则滚不动

```xml
<View id="20" type="AppBarLayout">
<event><eventItme type="onoffsetchanged">call(null, "mjava", "ab.onOffset", st_vO)</eventItme></event>
</View>
```

常见用法：`st_vO` 接近 `-totalScrollRange` 时标题条收起，可以据此换标题/改透明度。

## 仍未验（缺条件）

| 事件 | 状态 | 缺什么才能验 |
|---|---|---|
| `onoptionsitemselected` | ❓ | 需要 ActionBar 上真的有菜单项：`activity.getActionBar()` 可能是 null（iApp 主题未必带 ActionBar），得先用 mjava 拿到 ActionBar/Toolbar 并 `addMenu`，再点菜单 |
| `onpicturecallback` | ❓ | 需要相机回调：无摄像头的模拟器测不了，得真机，或先给模拟器接一个虚拟摄像头 |

这两项价值不高，标 ❓ 即可；真要用时按上表补条件。
