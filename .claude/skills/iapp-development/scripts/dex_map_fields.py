"""按字段名反查类，辅助辨认混淆类。

用法：python dex_map_fields.py <apk|dex> [字段名过滤]
输出：字段名、类型、所属类、访问权限
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
    if len(sys.argv) < 2:
        print("usage: python dex_map_fields.py <apk|dex> [filter]", file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    print("field\ttype\tclass\tscope")
    for name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            lines = block.splitlines()
            for i, line in enumerate(lines):
                m = NAME_RE.match(line)
                if not m or (needle and needle not in m.group(1)):
                    continue
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                nxt2 = lines[i + 2] if i + 2 < len(lines) else ""
                t = TYPE_RE.match(nxt)
                a = ACCESS_RE.match(nxt2)
                if not t or not a:
                    continue
                acc = int(a.group(1), 16)
                if acc & 0x8:
                    scope = "static"
                elif acc & 0x1:
                    scope = "public"
                else:
                    scope = "other"
                print(f"{m.group(1)}\t{t.group(1)}\t{desc}\t{scope}")


if __name__ == "__main__":
    main()
