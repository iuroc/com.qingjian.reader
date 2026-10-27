"""打印某个方法的字节码与可读字符串。

用法：python dex_body.py <apk|dex> <类描述符> <方法名> [重载序号]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dex_common import iter_dex_paths, dump, split_classes

NAME_RE = re.compile(r"^      name          : '(.*)'")


def main():
    if len(sys.argv) < 4:
        print("usage: python dex_body.py <apk|dex> <class> <method> [index]", file=sys.stderr)
        sys.exit(2)
    target, cls, method = sys.argv[1], sys.argv[2], sys.argv[3]
    idx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    for name, path in iter_dex_paths(target):
        for desc, block in split_classes(dump(path)):
            if desc != cls:
                continue
            hits = [m.start() for m in re.finditer(rf"^      name          : '{re.escape(method)}'", block, re.M)]
            if not hits:
                continue
            start = hits[idx]
            nxt = block.find("\n    #", start + 10)
            end = nxt if nxt != -1 else len(block)
            print(block[start:end])
            return
    print("method not found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
