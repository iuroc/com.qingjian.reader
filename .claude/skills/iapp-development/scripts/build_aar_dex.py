"""把 AAR 库转成 iApp 可加载的 dex + 资源 apk（通用版，支持「资源不自足」的库）。

用法（XUI 1.1.9 实测配方）：

  python build_aar_dex.py \
      --aar XUI-1.1.9.aar \
      --res-aar appcompat-1.3.1.aar \
      --res-aar calligraphy3-3.1.1.aar \
      --stub-res stub/ \
      --framework-res framework-res.apk \
      --manifest-package com.xuexiang.xui \
      --name xui --out out/

产物：
  <out>/<name>.dex        代码（库 + 依赖 jar + 重新生成的 R）
  <out>/<name>-res.apk    资源（库 + --res-aar + --stub-res，独立包 ID）

为什么不能照 JAR 那套直接 d8：
  - AAR 里的 R 全是 0，必须在链接期生成真 R；
  - 库的 values.xml 往往引用宿主依赖（appcompat/material）的 attr 和 style，
    aapt2 link 解析不到就整包失败。`-I <别的 apk>` 不能当资源依赖用（实测），
    只能把依赖的 res 也编进同一个包。
  - 依赖的版本要对齐：material 1.13 与 appcompat 1.3.1 会撞 styleable/SearchView。

参数要点：
  --aar          代码+资源都收的库（可重复）
  --res-aar      只收资源的依赖库（appcompat / calligraphy 之类，可重复）
  --stub-res     补链接缺口的 res 目录（少量 not found 的 style/attr 写这里）
  --package-id   资源包 ID，必须 ≥ 0x7f；宿主占 0x7f，用 0x80
  --r-package    要被剥掉的旧 R 类所在包，默认等于 --manifest-package
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

DEFAULT_BUILD_TOOLS = os.environ.get("BUILD_TOOLS", "")
DEFAULT_JDK = os.environ.get("JDK_BIN", "")


def resolve_tool(dirpath, names):
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


def extract_classes_jar(aar, outjar, r_prefixes):
    """从 aar 取 classes.jar；剥掉 r_prefixes 下的旧 R 类。"""
    with zipfile.ZipFile(aar) as z:
        data = z.read("classes.jar")
    kept = stripped = 0
    with zipfile.ZipFile(io.BytesIO(data)) as src, \
            zipfile.ZipFile(outjar, "w", zipfile.ZIP_DEFLATED) as out:
        for n in src.namelist():
            if n.endswith("/"):
                continue
            base = os.path.basename(n)
            if any(n.startswith(p) and (base == "R.class" or base.startswith("R$"))
                   for p in r_prefixes):
                stripped += 1
                continue
            out.writestr(n, src.read(n))
            kept += 1
    print("%s: kept %d class(es), stripped %d R class(es)" % (os.path.basename(outjar), kept, stripped))


def extract_res(aar, outdir):
    with zipfile.ZipFile(aar) as z:
        names = [n for n in z.namelist() if n.startswith("res/") and not n.endswith("/")]
        for n in names:
            p = os.path.join(outdir, n.replace("/", os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(z.read(n))
    return len(names)


def zip_dir(dirpath, outjar):
    with zipfile.ZipFile(outjar, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dirpath):
            for f in files:
                if f.endswith(".class"):
                    p = os.path.join(root, f)
                    zf.write(p, os.path.relpath(p, dirpath).replace(os.sep, "/"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aar", action="append", default=[], help="代码+资源的库（可重复）")
    ap.add_argument("--res-aar", action="append", default=[], help="只编资源的依赖库（可重复）")
    ap.add_argument("--stub-res", default=None, help="补缺口的 res 目录（可含 values/）")
    ap.add_argument("--framework-res", required=True, help="设备 /system/framework/framework-res.apk")
    ap.add_argument("--manifest-package", required=True, help="产物资源包的包名（= 库的 package）")
    ap.add_argument("--name", required=True, help="产物文件名前缀")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None)
    ap.add_argument("--package-id", default="0x80")
    ap.add_argument("--min-api", default="21")
    ap.add_argument("--r-package", action="append", default=[], help="要剥掉的 R 包名（可重复）")
    ap.add_argument("--extra-src", default=None, help="要一起编进 dex 的 Java 源码目录（桥接类）")
    ap.add_argument("--android-jar", default=None, help="配合 --extra-src 编译用")
    ap.add_argument("--build-tools", default=DEFAULT_BUILD_TOOLS)
    ap.add_argument("--jdk", default=DEFAULT_JDK)
    args = ap.parse_args()

    if not args.aar:
        raise SystemExit("至少给一个 --aar")

    out = os.path.abspath(args.out)
    work = os.path.abspath(args.work or os.path.join(out, "_build_" + args.name))
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    aapt2 = resolve_tool(args.build_tools, ["aapt2.exe", "aapt2"])
    d8 = resolve_tool(args.build_tools, ["d8.bat", "d8"])
    javac = resolve_tool(args.jdk, ["javac.exe", "javac"])

    r_pkgs = args.r_package or [args.manifest_package]
    r_prefixes = tuple(p.replace(".", "/") + "/" for p in r_pkgs)

    # 1) 代码 jar
    jars = []
    for i, aar in enumerate(args.aar):
        jar = os.path.join(work, "lib%d.jar" % i)
        extract_classes_jar(aar, jar, r_prefixes)
        jars.append(jar)

    # 2) 资源：库 + 只资源依赖 + 补丁，各编各的，最后一起 link
    compiled = []
    for i, aar in enumerate(args.aar + args.res_aar):
        resdir = os.path.join(work, "res%d" % i)
        os.makedirs(resdir, exist_ok=True)
        n = extract_res(aar, resdir)
        if n == 0:
            print("skip res (empty):", os.path.basename(aar))
            continue
        c = os.path.join(work, "compiled%d.zip" % i)
        # 解出来的结构是 <resdir>/res/values/...，aapt2 --dir 要指到 res/ 本身
        run([aapt2, "compile", "--dir", os.path.join(resdir, "res"), "-o", c])
        compiled.append(c)
        print("res %d: %d file(s) from %s" % (i, n, os.path.basename(aar)))
    if args.stub_res:
        stub = os.path.join(work, "stub.zip")
        run([aapt2, "compile", "--dir", os.path.abspath(args.stub_res), "-o", stub])
        compiled.append(stub)

    # 3) link：独立包 ID
    manifest = os.path.join(work, "AndroidManifest.xml")
    with open(manifest, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                'package="%s">\n'
                '<uses-sdk android:minSdkVersion="%s" android:targetSdkVersion="34"/>\n'
                '</manifest>\n' % (args.manifest_package, args.min_api))
    resapk = os.path.join(out, args.name + "-res.apk")
    gendir = os.path.join(work, "gen")
    run([aapt2, "link", "-o", resapk,
         "-I", os.path.abspath(args.framework_res),
         "--manifest", manifest, "--java", gendir,
         "--package-id", args.package_id] + compiled)
    print("resources ->", resapk, os.path.getsize(resapk), "bytes")

    # 4) 编译生成的 R
    rjava = os.path.join(gendir, *args.manifest_package.split("."), "R.java")
    if not os.path.exists(rjava):
        raise SystemExit("R.java not generated: " + rjava)
    rclasses = os.path.join(work, "rclasses")
    os.makedirs(rclasses, exist_ok=True)
    # --release 11：JDK 25 默认 class 69，d8 不认
    run([javac, "--release", "11", "-nowarn", "-encoding", "UTF-8", "-d", rclasses, rjava])
    rjar = os.path.join(work, "r.jar")
    zip_dir(rclasses, rjar)

    # 5) 可选桥接类
    extra = []
    if args.extra_src:
        if not args.android_jar:
            raise SystemExit("--extra-src 需要同时给 --android-jar")
        srcs = []
        for root, _, files in os.walk(os.path.abspath(args.extra_src)):
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

    # 6) d8 合成一个 dex
    dexdir = os.path.join(work, "dex")
    os.makedirs(dexdir, exist_ok=True)
    run([d8, "--min-api", str(args.min_api), "--output", dexdir] + jars + [rjar] + extra)
    dst = os.path.join(out, args.name + ".dex")
    shutil.copyfile(os.path.join(dexdir, "classes.dex"), dst)
    print("dex ->", dst, os.path.getsize(dst), "bytes")


if __name__ == "__main__":
    main()
