"""列出 APK/DEX 里的类与成员数量。

用法：python dex_classes.py <apk|dex> [过滤子串]
输出：dex 文件、类描述符、字段数、方法数
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dex_common import iter_dex_paths, dump, split_classes


def main():
    if len(sys.argv) < 2:
        print("usage: python dex_classes.py <apk|dex> [filter]", file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    print("dex\tclass\tfields\tmethods")
    for name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            if needle and needle not in desc:
                continue
            fields = len(re.findall(r"^      name          :", block, re.M))
            methods = len(re.findall(r"^#\d+              : \(in ", block, re.M))
            print(f"{name}\t{desc}\t{fields}\t{methods}")


if __name__ == "__main__":
    main()
