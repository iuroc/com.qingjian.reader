"""把 sora-editor 的 AAR 转成 iApp 可用的 dex + 资源 apk。

用法：
  python build_sora_dex.py --aar <editor.aar> --lang-aar <language-java.aar> \
      --kotlin <kotlin-stdlib.jar> --framework-res <framework-res.apk> \
      --out <输出目录> [--package-id 0x80] [--min-api 21]

产物：
  <out>/sora.dex        代码（editor + language-java + kotlin-stdlib + 生成的 R）
  <out>/sora-res.apk    资源（AAR 的 res/，独立包 ID，运行时 addAssetPath 挂载）

为什么需要这个脚本：
  - iApp 没有 Gradle，外部库要自己转 dex；AAR 还带资源。
  - AAR 里的 R 字段在编译期是 0（AAR 的 R.txt 全是 0x0），运行时 sora 构造
    CodeEditor 会立刻 inflate R.layout.text_compose_panel，R=0 必崩。
    所以必须真的生成一份带真实 ID 的 R，并让运行时能解析这些 ID。
  - 资源用独立包 ID（默认 0x80）链接，避开宿主 0x7f，addAssetPath 后不冲突。
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

DEFAULT_BUILD_TOOLS = os.environ.get("BUILD_TOOLS", "")
DEFAULT_JDK = os.environ.get("JDK_BIN", "")


def resolve_tool(dirpath, names):
    """优先用显式目录，其次 PATH；找不到时返回第一个名字交给系统报错。"""
    if dirpath:
        for name in names:
            p = os.path.join(dirpath, name)
            if os.path.exists(p):
                return p
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    return names[0]


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stdout or "")
        sys.stderr.write(r.stderr or "")
        raise SystemExit("failed: %s" % cmd[0])
    return r.stdout


def unzip_matching(zpath, outdir, pred):
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if n.endswith("/") or not pred(n):
                continue
            p = os.path.join(outdir, n)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(z.read(n))


def zip_dir(dirpath, outjar):
    with zipfile.ZipFile(outjar, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dirpath):
            for f in files:
                if f.endswith(".class"):
                    p = os.path.join(root, f)
                    zf.write(p, os.path.relpath(p, dirpath).replace(os.sep, "/"))


def extract_classes_jar(aar, outjar, strip_r=False):
    """从 aar 取出 classes.jar；strip_r=True 时去掉自带的 R*.class。"""
    with zipfile.ZipFile(aar) as z:
        data = z.read("classes.jar")
    with zipfile.ZipFile(outjar, "w", zipfile.ZIP_DEFLATED) as out:
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as src:
            for n in src.namelist():
                if n.endswith("/"):
                    continue
                if strip_r:
                    base = n.rsplit("/", 1)[-1]
                    if n.startswith("io/github/rosemoe/sora/") and (
                            base == "R.class" or base.startswith("R$")):
                        continue
                out.writestr(n, src.read(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aar", required=True, help="editor AAR")
    ap.add_argument("--lang-aar", default=None, help="language-java AAR（可选）")
    ap.add_argument("--kotlin", required=True, help="kotlin-stdlib jar")
    ap.add_argument("--framework-res", required=True,
                    help="设备的 /system/framework/framework-res.apk（aapt2 链接用）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None, help="中间目录，默认 <out>/_build")
    ap.add_argument("--package-id", default="0x80")
    ap.add_argument("--min-api", default="21")
    ap.add_argument("--android-jar", default=None,
                    help="android.jar（编译 --extra-src 用）")
    ap.add_argument("--extra-src", default=None,
                    help="额外要编进 dex 的 Java 源码目录（如桥接类）")
    ap.add_argument("--build-tools", default=DEFAULT_BUILD_TOOLS)
    ap.add_argument("--jdk", default=DEFAULT_JDK)
    ap.add_argument("--manifest-package", default="io.github.rosemoe.sora")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    work = os.path.abspath(args.work or os.path.join(out, "_build"))
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    aapt2 = resolve_tool(args.build_tools, ["aapt2.exe", "aapt2"])
    d8 = resolve_tool(args.build_tools, ["d8.bat", "d8"])
    javac = resolve_tool(args.jdk, ["javac.exe", "javac"])

    # 1) 抽 classes.jar（去掉自带 R，避免和生成的 R 重名）
    editor_jar = os.path.join(work, "editor.jar")
    extract_classes_jar(args.aar, editor_jar, strip_r=True)
    jars = [editor_jar]
    if args.lang_aar:
        lang_jar = os.path.join(work, "language.jar")
        extract_classes_jar(args.lang_aar, lang_jar, strip_r=True)
        jars.append(lang_jar)

    # 2) AAR 的 res/ 抽出来
    resdir = os.path.join(work, "res")
    unzip_matching(args.aar, work, lambda n: n.startswith("res/"))
    os.rename(os.path.join(work, "res"), resdir)

    # 3) aapt2 编译 + 链接（独立包 ID）
    manifest = os.path.join(work, "AndroidManifest.xml")
    with open(manifest, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                'package="%s">\n'
                '<uses-sdk android:minSdkVersion="%s" android:targetSdkVersion="28"/>\n'
                '</manifest>\n' % (args.manifest_package, args.min_api))
    compiled = os.path.join(work, "compiled.zip")
    run([aapt2, "compile", "--dir", resdir, "-o", compiled])
    resapk = os.path.join(out, "sora-res.apk")
    gendir = os.path.join(work, "gen")
    run([aapt2, "link", "-o", resapk, "-I", os.path.abspath(args.framework_res),
         "--manifest", manifest, "--java", gendir,
         "--package-id", args.package_id, compiled])
    print("resources ->", resapk)

    # 4) 编译生成的 R.java
    rjava = os.path.join(gendir, *args.manifest_package.split("."), "R.java")
    rclasses = os.path.join(work, "rclasses")
    os.makedirs(rclasses, exist_ok=True)
    # --release 11：JDK 25 默认产出 class 版本 69，d8 不认；降到 11 即可
    run([javac, "--release", "11", "-nowarn", "-encoding", "UTF-8", "-d", rclasses, rjava])
    rjar = os.path.join(work, "r.jar")
    with zipfile.ZipFile(rjar, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(rclasses):
            for f in files:
                if f.endswith(".class"):
                    p = os.path.join(root, f)
                    zf.write(p, os.path.relpath(p, rclasses).replace(os.sep, "/"))

    # 4b) 额外 Java 源码（桥接类）：编译期解析 sora 方法引用，运行期改名也不受影响
    extra = []
    if args.extra_src:
        if not args.android_jar:
            raise SystemExit("--extra-src 需要同时给 --android-jar")
        srcdir = os.path.abspath(args.extra_src)
        srcs = []
        for root, _, files in os.walk(srcdir):
            for f in files:
                if f.endswith(".java"):
                    srcs.append(os.path.join(root, f))
        ecls = os.path.join(work, "extraclasses")
        os.makedirs(ecls, exist_ok=True)
        cp = os.pathsep.join([os.path.abspath(args.android_jar)] +
                             [os.path.abspath(j) for j in jars])
        run([javac, "--release", "11", "-nowarn", "-encoding", "UTF-8",
             "-classpath", cp, "-d", ecls] + srcs)
        ejar = os.path.join(work, "extra.jar")
        zip_dir(ecls, ejar)
        extra.append(ejar)
        print("extra classes ->", len(srcs), "source(s)")

    # 5) d8：代码 + kotlin + R + 桥接 → 单个 dex
    dexdir = os.path.join(work, "dex")
    os.makedirs(dexdir, exist_ok=True)
    run([d8, "--min-api", str(args.min_api), "--output", dexdir] +
        jars + [os.path.abspath(args.kotlin), rjar] + extra)
    src_dex = os.path.join(dexdir, "classes.dex")
    dst_dex = os.path.join(out, "sora.dex")
    shutil.copyfile(src_dex, dst_dex)
    print("dex ->", dst_dex, os.path.getsize(dst_dex), "bytes")


if __name__ == "__main__":
    main()
