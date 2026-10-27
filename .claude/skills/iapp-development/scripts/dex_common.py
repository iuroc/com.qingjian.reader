"""dexdump 输出的解析工具。

用法：被其它脚本 import；也可单独运行 `python dex_common.py <apk|dex> <类描述符>` 看类摘要。
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile

DEFAULT_DEXDUMP = "dexdump"

CLASS_RE = re.compile(r"^  Class descriptor  : '(.*)'")


def dexdump_bin() -> str:
    return os.environ.get("DEXDUMP", DEFAULT_DEXDUMP)


def iter_dex_paths(path: str):
    """APK 就解包到临时目录，返回 [(dex 名, 路径)]。"""
    if path.lower().endswith(".apk"):
        tmp = tempfile.mkdtemp(prefix="iapp_dex_")
        out = []
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if re.fullmatch(r"classes\d*\.dex", name):
                    z.extract(name, tmp)
                    out.append((name, os.path.join(tmp, name)))
        return sorted(out)
    return [(os.path.basename(path), path)]


def dump(path: str) -> str:
    r = subprocess.run([dexdump_bin(), "-d", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return r.stdout


def split_classes(text: str):
    """返回 [(descriptor, block_text)]。"""
    cur = None
    buf = []
    for line in text.splitlines():
        m = CLASS_RE.match(line)
        if m:
            if cur is not None:
                yield cur, "\n".join(buf)
            cur = m.group(1)
            buf = [line]
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        yield cur, "\n".join(buf)


def main():
    if len(sys.argv) < 3:
        print("usage: python dex_common.py <apk|dex> <class-descriptor>", file=sys.stderr)
        sys.exit(2)
    target, cls = sys.argv[1], sys.argv[2]
    for name, p in iter_dex_paths(target):
        for desc, block in split_classes(dump(p)):
            if desc == cls:
                print(f"== {name} {desc}")
                print(block[:4000])


if __name__ == "__main__":
    main()
