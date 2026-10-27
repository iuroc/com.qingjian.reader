"""把若干 Java 源码编译成 iApp 可用的 dex（编译类进 dex 的通用流水线）。

用途：BeanShell 写不了「继承类」（如 PagerAdapter 这类抽象类），
但可以把实现编译成 class 再转 dex，运行时用 DexClassLoader 加载。

用法：
  python build_class_dex.py --src <源码目录> --out <输出.dex> \
      --lib <android.jar> [--lib <其它依赖.jar> ...] [--min-api 21] \
      [--build-tools <dir>] [--jdk <dir>]

注意：
  - d8 不接受目录输入，class 目录先打成 jar
  - JDK 25 默认产 class 版本 69，d8 不认，用 --release 11
  - 依赖的 androidx 等库不要打包进来，运行期由宿主提供（DexClassLoader 父加载器给宿主）
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


def run(cmd):
    print("+", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout or "")
        sys.stderr.write(r.stderr or "")
        raise SystemExit("failed: %s" % cmd[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lib", action="append", default=[],
                    help="编译期依赖 jar（android.jar 必给；androidx 等按需）")
    ap.add_argument("--min-api", default="21")
    ap.add_argument("--work", default=None)
    ap.add_argument("--build-tools", default=DEFAULT_BUILD_TOOLS)
    ap.add_argument("--jdk", default=DEFAULT_JDK)
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)
    work = os.path.abspath(args.work or (out + ".build"))
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)

    srcs = []
    for root, _, files in os.walk(src):
        for f in files:
            if f.endswith(".java"):
                srcs.append(os.path.join(root, f))
    if not srcs:
        raise SystemExit("no .java under " + src)

    javac = resolve_tool(args.jdk, ["javac.exe", "javac"])
    d8 = resolve_tool(args.build_tools, ["d8.bat", "d8"])
    classes = os.path.join(work, "classes")
    os.makedirs(classes)
    cp = os.pathsep.join(os.path.abspath(p) for p in args.lib)
    run([javac, "--release", "11", "-nowarn", "-encoding", "UTF-8",
         "-classpath", cp, "-d", classes] + srcs)

    jar = os.path.join(work, "classes.jar")
    with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(classes):
            for f in files:
                if f.endswith(".class"):
                    p = os.path.join(root, f)
                    zf.write(p, os.path.relpath(p, classes).replace(os.sep, "/"))

    dexdir = os.path.join(work, "dex")
    os.makedirs(dexdir)
    libs = []
    for p in args.lib:
        libs.extend(["--lib", os.path.abspath(p)])
    run([d8, "--min-api", str(args.min_api), "--output", dexdir] + libs + [jar])
    shutil.copyfile(os.path.join(dexdir, "classes.dex"), out)
    print("dex ->", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
