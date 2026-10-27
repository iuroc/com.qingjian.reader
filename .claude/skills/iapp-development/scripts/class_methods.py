"""列出 APK/DEX 里指定类的自身方法名（用于确认 Material API 是否存在）。

用法：python class_methods.py <apk|dex> <类描述符前缀...>
例：  python class_methods.py <apk|dex> com/google/android/material/slider/

注意：只能看到类自己声明的方法，继承自 framework 的（如 setThumbTintList）不在此列。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dex_common import iter_dex_paths, dump, split_classes

METHOD_RE = re.compile(r"name\s+:\s+'([^']*)'", re.M)


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    prefixes = sys.argv[2:]
    seen = {}
    for _name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            plain = desc.lstrip("L").rstrip(";")
            for pre in prefixes:
                if plain.startswith(pre):
                    names = sorted(set(METHOD_RE.findall(block)))
                    bucket = seen.setdefault(desc, set())
                    bucket.update(n for n in names if not n.startswith("<"))
    for desc in sorted(seen):
        print("== " + desc)
        print("   " + " ".join(sorted(seen[desc])))


if __name__ == "__main__":
    main()
