"""Native-schematic helpers and entry point for the integrated review drawing.

Read maintained source symbols; re-layout and route the derived overview with
integrated_schematic_layout. Source netlists and physical-wire continuity are
independently checked by verify_schematic_overview. The source project continues
to own existing PCB identities and synchronization.
"""
import json
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
EL = ROOT / "electrical/v03"
NAME = "tpa3255-v03-overview"
OUTPUT = EL / (NAME + ".kicad_sch")
MANIFEST = EL / "overview-sources.json"
UUID = str(uuid5(NAMESPACE_URL, "diy-tpa3255/v03/single-page-overview"))
SOURCE_NAMES = [
    "xlr-input", "input", "feedback", "tpa3255-v03", "power-control",
    "control-supply", "trigger", "dc-switch",
]


def parse(text):
    """Small lossless-token S-expression reader; quoted strings remain quoted."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    root = None
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            else:
                if root is not None:
                    raise ValueError("Multiple S-expression roots")
                root = node
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unmatched closing parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Token outside S-expression")
            stack[-1].append(token)
    if stack or root is None:
        raise ValueError("Incomplete S-expression")
    return root


def dump(node):
    return "(" + " ".join(dump(v) if isinstance(v, list) else v for v in node) + ")"


def child(node, key):
    return next(v for v in node[1:] if isinstance(v, list) and v[0] == key)


def children(node, key):
    return [v for v in node[1:] if isinstance(v, list) and v[0] == key]


def walk(node):
    yield node
    for value in node:
        if isinstance(value, list):
            yield from walk(value)


def q(text):
    return json.dumps(text, ensure_ascii=False)


def number(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") if value else "0"


def annotation(text, x, y, size=2.0):
    uid = uuid5(NAMESPACE_URL, NAME + text)
    return parse(
        f'(text {q(text)} (at {number(x)} {number(y)} 0) '
        f'(effects (font (face "Noto Sans CJK TC") (size {size} {size})) '
        f'(justify left)) (uuid {uid}))'
    )


def build():
    from integrated_schematic_layout import build_integrated
    build_integrated()


if __name__ == "__main__":
    build()
