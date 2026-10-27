"""创建一个最小 iApp 工程（裕 3 模式）。

用法：
  python create_project.py --root <ProjectApp 目录> --package com.demo.x --title 演示 \
      --version 1.0 --versionint 1 [--sdk 21] [--remark 备注] [--icon a.png] \
      [--icon-category auto|game|calc|...] [--icon-text auto|2048] [--icon-color "#BBADA0"] \
      [--developer 766868_2329632875] [--toolversion "iApp V5.0.1013"] [--force]

只写最小文件集：.project / AndroidManifest.xml / src/mian.iyu / icon.png / files/ / res/
build.xml、sdk/、<包名>/ 由 iApp 首次打开时生成，不在这里创建。

没传 --icon 时，用同目录的 make_icon.py 离线生成图标：标题里的数字/英文做
大字徽章，中文标题按品类画符号。完全不联网，不依赖 Pillow。
"""
import argparse
import os
import shutil
import sys
import time
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_icon

DEFAULT_MIAN = """<View id="1" did="0" type="LinearLayout">
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
<View id="3" did="0" type="TextView">
<ppt>width=-2
height=-2
text=Hello world
textsize=15sp
layout_marginleft=20dp
layout_margintop=20dp</ppt>
<event></event>
</View>
<UIEventset></UIEventset>
"""

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<iapp>
<title>{title}</title>
<icon>icon.png</icon>
<packageName>{package}</packageName>
<versionName>{version}</versionName>
<versionint>{versionint}</versionint>
<sdk>{sdk}</sdk>
<yuv>3</yuv>

<remark>{remark}</remark>
<Permissions>android.permission.READ_EXTERNAL_STORAGE
android.permission.REQUEST_INSTALL_PACKAGES
android.permission.INTERNET
android.permission.WRITE_EXTERNAL_STORAGE</Permissions>
<createTime>{now}</createTime>
<upTime>{now}</upTime>
</iapp>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="ProjectApp 目录")
    ap.add_argument("--package", required=True, dest="package")
    ap.add_argument("--title", required=True)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--versionint", default="1")
    ap.add_argument("--sdk", default="21")
    ap.add_argument("--remark", default="")
    ap.add_argument("--icon", default=None)
    ap.add_argument("--icon-category", default="auto")
    ap.add_argument("--icon-text", default="auto")
    ap.add_argument("--icon-color", default=None)
    ap.add_argument("--icon-size", type=int, default=512)
    ap.add_argument("--developer", default="766868_2329632875")
    ap.add_argument("--toolversion", default="iApp V5.0.1013")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    proj = os.path.join(a.root, a.package)
    if os.path.exists(proj) and not a.force:
        raise SystemExit(f"已存在：{proj}（加 --force 覆盖）")
    if a.force and os.path.exists(proj):
        shutil.rmtree(proj)

    os.makedirs(os.path.join(proj, "src"))
    os.makedirs(os.path.join(proj, "files"), exist_ok=True)
    os.makedirs(os.path.join(proj, "res"), exist_ok=True)

    now_ms = int(time.time() * 1000)
    with open(os.path.join(proj, ".project"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<package>{escape(a.package)}</package>"
                f"<toolversion>{escape(a.toolversion)}</toolversion>"
                f"<developer>{escape(a.developer)}</developer>"
                f"<time>{now_ms}</time>")

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(proj, "AndroidManifest.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(MANIFEST.format(title=escape(a.title), package=escape(a.package),
                                version=escape(a.version), versionint=escape(str(a.versionint)),
                                sdk=escape(str(a.sdk)), remark=escape(a.remark), now=now))

    with open(os.path.join(proj, "src", "mian.iyu"), "w", encoding="utf-8", newline="\n") as f:
        f.write(DEFAULT_MIAN)

    icon_dst = os.path.join(proj, "icon.png")
    if a.icon:
        shutil.copyfile(a.icon, icon_dst)
    else:
        make_icon.generate_icon(icon_dst, title=a.title, package=a.package,
                                category=a.icon_category, text=a.icon_text,
                                color=a.icon_color, size=a.icon_size)
        print(f"icon: {icon_dst}")

    print(f"created: {proj}")


if __name__ == "__main__":
    main()
