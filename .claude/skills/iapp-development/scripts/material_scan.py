"""扫描 APK/DEX 里 Material 组件类是否有可用构造器。

用法：python material_scan.py <apk|dex> [包前缀]
输出：类描述符 | 构造器签名（只列有 (Context) 或 (Context, AttributeSet) 的类）
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dex_common import iter_dex_paths, dump, split_classes

CTX = "(Landroid/content/Context;)V"
CTX_ATTR = "(Landroid/content/Context;Landroid/util/AttributeSet;)V"

METHOD_RE = re.compile(
    r"name\s+:\s+'([^']*)'\s*\n\s*type\s+:\s+'([^']*)'", re.M
)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python material_scan.py <apk|dex> [prefix]", file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else "com/google/android/material/"
    for name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            if prefix not in desc or "$" in desc:
                continue
            ctors = [t for n, t in METHOD_RE.findall(block) if n == "<init>"]
            if CTX in ctors or CTX_ATTR in ctors:
                print(f"{desc}\t{','.join(ctors)}")


if __name__ == "__main__":
    main()
