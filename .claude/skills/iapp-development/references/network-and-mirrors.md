# 国内网络：抓官方文档与依赖

版本前提：通用经验（2026-10 实测），不绑定 iApp 版本。

## 适用范围（先看这条）

本页的读数和结论来自 **Claude Code CLI** 这个工作环境：

- 内置抓取工具 **WebFetch** 在国内网络下对 Google 系域名直接不可用
- **Bash + `curl`** 可用，是国内网络下最稳的通道

**其他智能体工具（IDE 插件、网页版、其它 CLI/桌面端）要视情况而定**：
它们的网络出口、内置抓取工具、代理配置都不一样，WebFetch 不可用不代表别的工具也不行，
反之亦然。换工具时按「**先探测连通性，再选通道**」重新判断一次，不要照搬结论。

## 一句话

**`curl` 落盘 + 国内可达域名/镜像**；别指望 WebFetch 抓 Google 系站点。
抓下来的 HTML 离线转文本，结论要能回溯到原始文件。

## 症状 → 处理

| 现象 | 含义 | 处理 |
|---|---|---|
| WebFetch 报 `Unable to verify if domain … is safe to fetch` | 抓取服务侧不可达（网络环境所致，不是域名问题；Claude Code CLI 实测） | 改用 Bash + `curl` |
| `curl` 返回 `000`、退出码 35（SSL connect error） | 域名不可达或本地信任库拦了 | 换国内可达域名；确认是信任库问题时才用 `-k` |
| `curl http://…` 返回 301 | 站点可达，只是要求 https | 继续用 https（必要时 `-k`） |
| 404 但拿到一坨 HTML | 镜像站没有这个包，返回的是提示页 | 换仓库（central ↔ google） |

判断连通性先跑一条便宜的：

```bash
curl -s -o /dev/null -m 15 -w "%{http_code}\n" "<url>"
```

## 实测可用的镜像

| 用途 | 地址 | 备注 |
|---|---|---|
| Android 官方文档 | `https://developer.android.google.cn/…` | 国内可达；`developer.android.com` 不可达 |
| Maven Central | `https://maven.aliyun.com/repository/central/…` | `repo1.maven.org` 不可达 |
| Google Maven（androidx / com.google） | `https://maven.aliyun.com/repository/google/…` | androidx **不在** central；`dl.google.com` 不可达 |
| Google Maven（备用） | `https://mirrors.cloud.tencent.com/nexus/repository/maven-public/…` | 与上面的 google 仓库同效 |
| Android SDK 平台 | `https://mirrors.cloud.tencent.com/AndroidSDK/platform-XX_rNN.zip` | 内含 `android-XX/android.jar` |

- 找 artifact 先试 central，404 再换 google；两者路径结构一致
- 阿里云的 404 返回的是 HTML 提示页，不是空文件 —— 下载后要校验

## 抓文档的稳定姿势

```bash
curl -sk -m 40 -L "https://developer.android.google.cn/about/versions/14/behavior-changes-14?hl=en" \
     -o page.html -w "%{http_code} %{size_download}\n"
```

- 先看状态码 + 体积（200 且几十 KB 以上才算拿到）
- `-k` 会关闭证书校验：只在确认是**本地信任库**问题（exit 35）时用，并在记录里注明
- 保存原始 HTML，不要只留结论

## 离线转文本

```python
import re, html
s = open(path, encoding="utf-8", errors="ignore").read()
s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
s = html.unescape(re.sub(r"<[^>]+>", " ", s))
i = s.find("关键字")            # 定位到章节再截取
```

用 `python -I` 运行（隔离环境，避免工作目录里的同名模块被导入）。

## 下载物卫生

- 每个下载物放**独立、新建、空**目录；自己写的脚本放别处，按路径传参
- 校验：看文件头（`PK` = zip/aar/jar）、`md5sum`、解压试读
- 大文件用完删（如 SDK zip 75 MB，只留需要的 `android.jar`）
- 记录：URL、状态码、体积、日期写进你自己的证据文件

## 典型组合（本次实战）

| 需求 | 走法 |
|---|---|
| 查 Android 14 行为变更原文 | `developer.android.google.cn` + `curl -k` + 离线转文本 |
| 下 sora-editor AAR | 阿里云 `repository/central` |
| 下 androidx.viewpager（编译适配器用） | 阿里云 `repository/google` |
| 拿 `android.jar` 编译桥接类 | 腾讯 `AndroidSDK/platform-28_r06.zip` |
| 拿设备框架资源喂 aapt2 | `adb pull /system/framework/framework-res.apk`（不需要联网） |
