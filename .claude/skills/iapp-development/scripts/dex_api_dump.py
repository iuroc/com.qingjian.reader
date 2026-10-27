"""导出一个类的公开 API（字段 + 方法签名）。

用法：python dex_api_dump.py <apk|dex> <类描述符，如 Lcom/iapp/app/Aid_javaCode;>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dex_common import iter_dex_paths, dump, split_classes

NAME_RE = re.compile(r"^      name          : '(.*)'")
TYPE_RE = re.compile(r"^      type          : '(.*)'")
ACCESS_RE = re.compile(r"^      access        : 0x([0-9a-f]+)")


def main():
    if len(sys.argv) < 3:
        print("usage: python dex_api_dump.py <apk|dex> <class>", file=sys.stderr)
        sys.exit(2)
    target, want = sys.argv[1], sys.argv[2]
    for name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            if desc != want:
                continue
            print(f"== {name} {desc}")
            lines = block.splitlines()
            for i, line in enumerate(lines):
                m = NAME_RE.match(line)
                if m:
                    nxt = lines[i + 1] if i + 1 < len(lines) else ""
                    nxt2 = lines[i + 2] if i + 2 < len(lines) else ""
                    t = TYPE_RE.match(nxt)
                    a = ACCESS_RE.match(nxt2)
                    acc = int(a.group(1), 16) if a else 0
                    if t and (acc & 0x1):
                        print(f"public\t{m.group(1)}\t{t.group(1)}")
            return
    print("class not found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
