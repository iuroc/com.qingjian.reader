# 多 .iyu 导航模型（跳转 / 栈 / 返回）

版本前提：iApp 5.0.1013，Android 14 / API 34 实测（2026-10-27），**开发模式与打包 APK 均已验证**。

版本策略：以 API 34 为基准；Android 9 / API 28 及以下只做有限兼容测试，不追平结论。

## 结论速览

| 结论 | 级别 |
|---|---|
| 每个 `.iyu` 页面 = 一个 `com.iapp.app.run.mian` **Activity 实例** | ✅ |
| `uigo` 默认「新建实例并压栈」，**不按文件名去重**（同名页也压栈） | ✅ |
| 前进：旧页 `pause` → 新页 `loading → start → loadingComplete` → 旧页 `stop` | ✅ |
| 返回：被弹页 `pause` → 前页 `restart → start → resume` → 被弹页 `stop → destroy` | ✅ |
| 返回旧页是**复用**：Activity 实例、控件实例都不变，`loading` 不重跑 | ✅ |
| 未绑 `downkey` → 返回键走系统默认弹栈 | ✅ |
| 绑了 `downkey` → 返回键被吞，要 call 到 mjava 里 `activity.finish()` | ✅ |
| `A→A` 自跳 = 再压一个同名实例，旧实例状态原样保留 | ✅ |
| `536870912` = **no-op**：当前页 pause→resume 一次，不跳、不新建 | ✅ |
| `268435456` = 与普通跳转无可见差异（新实例，task 不变） | ✅ |
| `67108864` = 只销毁当前页，**中间页不清** | ✅ |
| `1073741824` = 离开即销毁，返回跳过该页 | ✅ |
| 传参用 `i.sss`；`uigo` 本身没有参数通道 | ✅ |
| 返回结果 = 子页写 `i.sss` + `finish()`，父页在 `resume` 读 | ✅ |
| `uigo` 不设转场，可用 `activity.overridePendingTransition(...)` 接管 | ✅ |
| 自建 Intent 传 extra 可行（必须用 `activity.getClass()`） | ✅（开发模式） |
| mjava `i.lan(n)` 可指定转场（0~11）；结束当前页统一 `activity.finish()` | ✅ |
| `addv` 只能写在 `.iyu`；mjava `i.addv` 返回 null；内嵌页不触发生命周期 | ✅ |
| 内嵌页 id 按"文件首次内嵌顺序"分 10000 号段（不是固定 +10000）；内嵌页事件正常触发 | ✅ |
| 多页 addv 只有 `DrawerLayout` 可用（改 gravity + 延迟 openDrawer） | ✅ |

## 调用方式

跳转只从 mjava 发出（iyu 白名单只允许 `call`/`addv`）：

```java
i.uigo("p_b.iyu");          // 普通：新建实例压栈
i.uigo("p_b.iyu", flag);    // 带 flag
```

```xml
<!-- .iyu 里只做绑定 -->
<eventItme type="clicki">call(null, "mjava", "nav.go", "p_b.iyu", 0)</eventItme>
```

- dex 签名：`Aid_javaCode.uigo(String)` / `uigo(String,int)`，两者都接受 `.iyu` 文件名 ✅
- `uigo` 立即返回，不等目标页载入（调用后本页马上 `pause`）✅

## 页面栈

```
   A(act=112367454)  ← 栈底
   A(act=100162897)  ← 自跳产生的新实例
   B(act=104209952)
   C(act=233137950)  ← 栈顶
```

- 同进程、同 task（默认）；`task=7/9` 与 iApp 编辑器同任务
- 每页的 `activity` 身份哈希都不同 —— 判断"是不是新页面实例"就用它
- 页面被弹掉时 `stop → destroy`，不会留在后台

## 返回

**不绑 `downkey`**：返回键完全由系统处理，逐层弹栈，栈底再返回就回到编辑器。

**绑了 `downkey`**：iApp 在事件派发后直接吞掉按键（和 `shouldoverrideurlloading` return true 同款），页面**不再自动弹出**。要返回必须自己收尾：

```java
// .iyu: <eventItme type="downkey">call(null, "mjava", "nav.back", st_kC)</eventItme>
public void back(int kc) {
    if (kc == 4) {          // KEYCODE_BACK
        activity.finish();
    }
}
```

mjava 里 `activity.finish()` 的效果与默认返回完全一致：本页 `pause/stop/destroy`，前页 `restart/start/resume` ✅。

## 状态边界（选型依据）

| 状态放哪 | 依据 |
|---|---|
| 控件 / 页面内变量 | 后台页不被销毁，返回后原样还在；**但弹掉即丢** |
| 跨页共享 | `i.sss`（每次运行重置，不是持久化） ✅ |
| 需要持久化 | `activity.getFilesDir()` 写文件 / SharedPreferences ✅ |

两条实用推论：

1. **`loading` 里做初始化 = 只初始化一次**。返回旧页不会重跑 `loading`，回到前台走的是 `restart/resume`。要"每次回到页面都刷新"，就把逻辑绑在 `resume` 上。
2. **页面实例会叠加**。A→A 自跳、或从深页跳回首页，都会产生新的同名实例；旧实例仍在栈里，返回会回到旧的那份。flag 做不了页面级去重（见下），不想叠栈只能在入口处自己判断（比如按 `i.sss` 里的当前页做短路）。

## flag

| 值 | 手册描述 | 实测 |
|---|---|---|
| `536870912` | 内存中存在且正在显示时复用 | ✅ **no-op**：从任何页调用都不跳（同页也一样），当前页 `pause → resume` 一次（同一 Activity 实例），无 `loading` |
| `268435456` | 新的内存 | ✅ 与普通跳转**无可见差异**：新实例，task 不变 |
| `67108864` | 清空其上的所有其他界面 | ✅ **不清中间页**：只销毁当前页，目标页作为新实例压上来 |
| `1073741824` | 不排在内存中 | ✅ **生效**：该页离开即 `stop → destroy`，返回时被跳过 |

### 为什么 flag 管不了页面栈

所有 `.iyu` 共用同一个 Activity 组件 `com.iapp.app.run.mian`，而 Android 的 Activity flag 按**组件**匹配，不按页面文件匹配：

- `CLEAR_TOP`：命中的"已存在的目标实例"就是栈顶自己 → 关掉栈顶、再起一个新实例，中间页原样保留
  - 实测栈 `[A, B, C]` 在 C 上执行 `C→A(67108864)`，结果是 `[A, B, A]`，返回依次 A→B→A（N20）
- `SINGLE_TOP`：永远命中栈顶 → 变成 no-op（N13/N15）
- `NEW_TASK`：按 affinity 找任务，iApp 任务本来就在 → 同一个 task（N16）

**结论：uigo 的 flag 不能用来做页面级栈控制。** 需要"清栈/回首页"，得自己连续 `activity.finish()`，或改用「单 Activity + `addv` 内嵌」的架构（见下）。

四个数值恰好等于 Android 的 `FLAG_ACTIVITY_SINGLE_TOP` / `CLEAR_TOP` / `NEW_TASK` / `NO_HISTORY`。四条的实测行为都与"flag 原样进了 Intent、按组件匹配"完全吻合；`uigo` 字节码里确实直接调用 `Intent.setFlags(int)` ✅（已反编译证实，不再是推测）。

## 传参 / 返回结果 / 转场

### 传参

| 通道 | 做法 | 级别 |
|---|---|---|
| `i.sss` | 跳转前 `i.sss("k", v)`，目标页在 `loading` 里读 | ✅ 推荐 |
| 自建 Intent | `new Intent(activity, activity.getClass())` + `putExtra` + `startActivity` | ✅ 开发模式验证 |
| `uigo` 自带 | **没有**。`uigo` 只塞 `ProjectPackageName` + `OpenFilexmlui` 两个内部键 | ✅ dex |

自建 Intent 的三条硬要求：

```java
Class cls = activity.getClass();          // 不能 Class.forName("com.iapp.app.run.mian")
Intent cur = activity.getIntent();
Intent it = new Intent(activity, cls);
it.putExtra("ProjectPackageName", cur.getStringExtra("ProjectPackageName"));
it.putExtra("OpenFilexmlui", file);       // 目标 .iyu 文件名
it.putExtra("k1", value);                 // 自己的参数
activity.startActivity(it);
```

- `Class.forName("com.iapp.app.run.mian")` 抛 `ClassNotFoundException` —— BeanShell 解释器看不见宿主类，只能从对象 `getClass()`
- 两个内部键必须原样带上，否则目标页不知道加载哪个工程的哪个界面
- 用的仍是目标页自己的 Activity 类，所以栈/生命周期语义与 `uigo` 相同

### 返回结果

iApp **没有** ActivityResult 通道：`uigo` 调用的是 `startActivity`，页面之间不会触发 `onactivityresult`。给父页回值只有一条路：

```java
// 子页
i.sss("nav.result", "值");
activity.finish();

// 父页：绑 resume 事件里读
setText(6, "结果: " + i.sss("nav.result"));
```

必须在**同一次运行**内完成 —— `i.sss` 每次运行重置（重新运行后读到 null 属正常）。

### 转场

- `uigo` 自身不设置转场：宿主里 `overridePendingTransition` 只有一处字符串字面量、无原生调用，Activity 主题也没有自定义 windowAnimation
- 想要动画就在 `uigo` 之后自己调：

```java
i.uigo(file);
activity.overridePendingTransition(android.R.anim.slide_in_left, android.R.anim.slide_out_right);
```

实测有可见效果 ✅（系统动画缩放 3 倍时对比明显）。

## 打包模式（APK）

2026-10-27 用真实 APK 整体复验：**导航语义与开发模式一致**。

| 项 | 打包版结果 |
|---|---|
| 多页 `uigo` | ✅ 每页仍是独立的 `com.iapp.app.run.mian` 实例，同 task |
| `i.sss` 传参 / 返回结果 | ✅ 一致 |
| 自建 Intent 传 extra | ✅ 可用，但当前 Intent 里 `ProjectPackageName` / `OpenFilexmlui` 都是 **null**（那两个键只在开发模式用来定位工程） |
| `addv` / 内嵌页事件 | ✅ 打包版二级内嵌的按钮事件实测触发（8 次）；与开发模式一致 |
| `DrawerLayout` / `ScrollView` | ✅ 打包版 G 页：可滚动、双页 addv、延迟 openDrawer 正常滑出 |
| `overridePendingTransition` | ✅ 一致 |
| 入口 | `mian.iyu`（打包固定） |

调试注意：打包后 `i.syso`（`ygs` tag）**完全无输出**，`android.util.Log` 正常 —— 见 `delivery-guide.md`。

## 两套页面模型（选型前提）

| | uigo（页面栈） | addv（容器内嵌） |
|---|---|---|
| 实现 | 每页一个 `run.mian` Activity | 把页面控件树塞进当前 Activity 的一个容器 |
| 调用位置 | mjava `i.uigo(...)` | **只能 `.iyu`**：`addv(容器id, "x.iyu")` |
| 生命周期 | 完整（loading/start/resume…） | **不触发**，纯控件树 |
| 返回键 | 系统弹栈 | 不变（还是当前页） |
| 状态 | 后台页保留 | 靠当前页自己管 |
| 适合 | 层级导航（列表→详情） | 标签页 / 步骤流 / 替换当前页 |

## 转场：lan

```xml
<!-- .iyu -->
<eventItme type="clicki">call(null, "mjava", "nav.go", "p_b.iyu", 0)</eventItme>
```
```java
i.uigo(file);
i.lan(6);   // 手册：0 淡入淡出 … 6 右往左推出 … 11 上下交错
```

- ✅ 实测 `lan(6)` 会让转场变成"向左平移"，与默认转场、与 `overridePendingTransition` 都不同
- 与 `overridePendingTransition` 是两套入口，选一套即可

## 结束当前页

- mjava：`activity.finish()` —— 实测与默认返回完全一致 ✅
- `.iyu` 不写 `end()`；统一 `call` 到 mjava 再 `finish()`

## addv：一个 Activity 里换页

```xml
<!-- .iyu 里写，白名单允许 -->
<View id="20" did="1" type="LinearLayout"><ppt>width=-1
height=150dp
orientation=vertical</ppt><event></event></View>

<eventItme type="clicki">addv(20, "p_b.iyu")</eventItme>
```

- ✅ 实测：目标页控件树被塞进 20 号容器，容器里多出 1 层包装 `LinearLayout`
- ❌ **不能从 mjava 调**：`i.addv(view, "p_b.iyu")` 返回 `null`、无子控件，即使 `i` 就是 `Aid_javaCode`
- ✅ 内嵌**不触发**目标页的任何生命周期事件（`loading` 等都不会跑）
- ✅ 清理：mjava 里 `((ViewGroup) findViewById(20)).removeAllViews()`，实测 `before=1 after=0`
- ✅ **内嵌页的事件绑定照常工作**：内嵌页里按钮的 `clicki` 每次都进 mjava
- ✅ **内嵌页控件的 id 会被重新分配**，规则是：**每个被内嵌的界面文件在进程内独占一个 10000 号段，按"首次内嵌顺序"递增**

  ```
  第 1 个被内嵌的文件（如 p_e.iyu）：9000/9001 → 19000/19001
  第 2 个（如 p_b.iyu）：1/2/10 → 20001/20002/20010
  第 3 个（如 p_f.iyu）：8000 → 38000
  ```

  - 同一次 `addv("a.iyu|b.iyu")` 里的两页按顺序占两个段
  - 号段是**进程级**、跟"文件"绑定：同一文件再内嵌还是同一个段（不随容器、不随层级）
  - **所以不能硬编码**。正确做法：原生遍历找到目标容器，把它作为 `addv` 的第一个参数（`addv` 接受 View）

    ```java
    // mjava：找 F 的白框
    public Object findFBox() { /* 沿树取到那个 ViewGroup，返回 */ }
    ```
    ```xml
    <!-- iyu：call 的接收变量直接喂给 addv -->
    <eventItme type="clicki">call(v, "mjava", "nav.findFBox")
    addv(v, "p_e.iyu")</eventItme>
    ```

    ✅ 实测可用（多层内嵌就是这么做的）
  - 拿到具体控件同理：知道是第几个文件就能算出 id；否则遍历树按 class/文字找
  - ⚠ **不要硬编码内嵌控件的 id**：号段随"文件首次内嵌顺序"变化，同一个页面在不同运行里可能落在不同段（实测踩过一次：处理函数写死 `19003`，而实际在 `29003`，表现成"点了没反应"）
  - 手册的 `ug(a.2, …)` 点号写法就是在做这层映射，**没必要用**

  事件覆盖实测：

  | 场景 | 事件是否触发 |
  |---|---|
  | 一级内嵌（直接嵌进当前页容器） | ✅ 开发模式 16 次全中 |
  | 二级内嵌（E 嵌进被内嵌的 F 里） | ✅ 打包版 8 次全中 |
  | 内嵌到 `DrawerLayout` 抽屉页 | ✅ 抽屉里的按钮点击照常跳页 |
- ✅ 多页 `addv` 的三种容器：

  | 容器 | 结果 |
  |---|---|
  | `ViewPager` | ❌ 子控件进树（`childCount=2`）但界面空白、不能滑 |
  | `VerticalViewPager` | ❌ 同上 |
  | `DrawerLayout` | ✅ **可用**：第 1 页=内容，第 2 页=抽屉 |

  `DrawerLayout` 三步：

  ```java
  // 1. addv(32, "内容页.iyu|抽屉页.iyu")
  // 2. 第二个子控件改成 drawer gravity（反射改，不必引 androidx 类）
  ViewGroup vg = (ViewGroup) activity.findViewById(32);
  View child = vg.getChildAt(1);
  ViewGroup.LayoutParams lp = child.getLayoutParams();
  lp.getClass().getField("gravity").setInt(lp, 0x800003);  // Gravity.START
  child.setLayoutParams(lp);
  // 3. 等布局完成再开（立刻开会被吞）
  vg.postDelayed(new Runnable() { public void run() { vg.openDrawer(0x800003); } }, 400);
  ```

  ✅ 实测：改完后子控件从 `vis=4 / x=-348` 变成 `vis=0 / x=0`，`isDrawerOpen=true`，第二页正常滑出。

## 清栈回首页

手册里 **没有**这个功能：`uigo` 只有 4 个 flag，`67108864` 又因所有页共用 `run.mian` 组件而清不掉中间页。可行做法只有两条：

1. 连续 `activity.finish()`（跳数已知时可行）
2. 改成单 Activity + `addv` 的架构，页面切换不产生栈
