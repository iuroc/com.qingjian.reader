# 工程结构与新建工程

版本前提：iApp 5.0.1013、裕 3 模式（`<yuv>3</yuv>`）。本技能只覆盖裕 3 + mjava。

## 初始结构（新建后第一次运行前 → 运行后）

新建：

```
<工程根>/
├── .project
├── AndroidManifest.xml
├── icon.png
├── src/mian.iyu
├── files/          (空)
└── res/            (空)
```

第一次被 iApp 打开/运行后追加：

```
build.xml           # 工程设置 + 自定义控件登记（空模板）
sdk/iapp.sdk        # 默认 SDK 列表
<包名>/             # 空目录（iApp 自己建）
```

`build.xml` 初始内容（✅ 实测）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<iapp>
<classExtends></classExtends>
<pathRemarks></pathRemarks>
<importClass></importClass>
<newControl></newControl>
<codeEvent></codeEvent>
<dexClass></dexClass>
<codeComment></codeComment>
</iapp>
```

## `.project`

```xml
<package>com.demo.newproject</package>
<toolversion>iApp V5.0.1013</toolversion>   <!-- IDE 版本，不是运行模式 -->
<developer>766868_2329632875</developer>
<time>1792832439400</time>                   <!-- epoch 毫秒 -->
```

## `AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<iapp>
<title>应用名</title>
<icon>icon.png</icon>
<packageName>com.demo.newproject</packageName>
<versionName>1.2.3</versionName>
<versionint>111</versionint>   <!-- 界面上的“标识”；打包 versionCode = 100000 + 111 -->
<sdk>21</sdk>
<yuv>3</yuv>                   <!-- 裕 3；开发模式看这个，不看 toolversion -->
<remark>备注</remark>
<Permissions>…</Permissions>
<createTime>2026-10-24 16:58:33</createTime>
<upTime>2026-10-24 16:58:33</upTime>
</iapp>
```

## `src/`

- 只允许 `.iyu` 与 `.mjava`
- 一个工程可以有多个 `.iyu`
- **开发模式**：可以指定任意 `.iyu` 作为入口运行（适合做互不干扰的探针页）
- **打包模式**：入口固定为 `mian.iyu`（少一个 i），其它页面要靠 `uigo`/跳转进入
- 默认 `mian.iyu`：顶部栏 LinearLayout(42dp，#50c4e5) + 标题 TextView + 正文 `Hello world`
- 探针约定：一页一问、一个 `.iyu` 配一到多个 `.mjava`；不要都堆进 `mian.iyu`

## `build.xml` 与自定义控件

- `build.xml` 由 iApp 管理，**不要手改**；唯一允许手写的是 `<newControl>`（控件登记）
- 登记格式（✅ 从 dex 解析代码确认，子项标签是 `itme`，原文拼写如此）：

```xml
<newControl><itme title="显示名" class="完整类名" info="说明"/></newControl>
```

- `title` 进设计器组件树显示，`info` 是说明，`class` 才会进 `.iyu`
- **触发判据是 `type` 的语法，不是“类算不算自定义”**：`type` 写内置短名（不含点号）不用登记；写完整类名（含点号）必须登记
- **每个工程独立**：`build.xml` 随工程走。新建工程（含每轮探针工程）的 `<newControl>` 是空的，旧工程的登记不会继承，新页里用完整类名就要重新登记
- **短名不是“安卓类名去包名”那么简单**：完整清单见 `builtin-controls.md`。`Switch` 不是短名（开关用 `SwitchCompat`）；`GifView`/`RoundImageView`/`VerticalViewPager` 是 iApp 封装
- 判据：设计器组件树里显示“未知”= 没有该短名 / 完整类名没登记；运行时可能仍正常，但设计器组件树展开可能**闪退**
- 登记只让设计器认识它，**不代表类可用**——类还要能从 `sdk/iapp.sdk` 或外部库加载
- 登记项可能被 iApp 重建时清掉
- 自查：`grep -n 'type="[^"]*\.' src/*.iyu` 列出全部完整类名，逐个确认 `build.xml` 里有同 `class` 的 `<itme>`

## `sdk/iapp.sdk`

iApp 首次打开工程时生成，默认包含 appcompat / material / constraintlayout / webkit / swiperefreshlayout / documentfile / core / gif / verticalviewpager。

## icon.png

- 工程根的 `icon.png` 就是应用图标，`AndroidManifest.xml` 里 `<icon>icon.png</icon>` 指向它
- 打包时**原样**写进 `res/mipmap-*/img_iapp.png`，不分 density
- 推荐 512×512、RGBA、满幅圆角方块；关键内容留中间 70%
- **不要用 1×1 占位图**：半透明像素会被启动器拉成纯色方块

生成方式（离线、纯标准库）：

```bash
python scripts/make_icon.py --project-dir <工程目录>
python scripts/make_icon.py --all <ProjectApp 目录>
```

`create_project.py` 不传 `--icon` 时会自动生成。详见 `icon-guide.md`。

## 新建工程的最小文件集

`.project` + `AndroidManifest.xml` + `src/mian.iyu` + `icon.png`（`files/`、`res/` 可空）。
`build.xml` / `sdk/` / `<包名>/` 由 iApp 首次打开时补。

**首次打开后补登记**：若 `src/*.iyu` 的 `type=` 里有完整类名（含点号），此时 `build.xml` 里是空 `<newControl>`，必须补登记——新工程不继承任何旧工程登记。探针工程每轮新建，最容易漏这一步。
