"""Flatten the maintained V0.3 sheets into a derived, editable A0 review drawing.

Read the checked-in schematics, not the original drawing generator. Preserve
symbol UUIDs, library definitions, properties, wires and labels; only translate
page coordinates, rewrite instance paths and replace page navigation/title text.
The eight-sheet project remains the source for PCB synchronization.
"""
import copy
import hashlib
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
# A0 portrait: two columns, four rows. All translations stay on the 1.27 mm grid.
PANELS = [
    ("xlr-input", 0, 0, "01  平衡輸入與選擇 / XLR + RCA"),
    ("input", 1, 0, "02  訊號驅動 / NE5532"),
    ("feedback", 0, 1, "03  濾波後回授 / PFFB"),
    ("tpa3255-v03", 1, 1, "04  功率放大與喇叭輸出 / TPA3255 + LC"),
    ("power-control", 0, 2, "05  類比供電與去耦 / 12V + VMID"),
    ("control-supply", 1, 2, "06  控制供電與狀態 / 3.3V"),
    ("trigger", 0, 3, "07  自動啟停與關機延遲 / Trigger"),
    ("dc-switch", 1, 3, "08  主電源開關與靜音 / 48V + RESET"),
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


def translate(node, dx, dy):
    for item in walk(node):
        if item[0] in {"at", "xy", "start", "end", "center"}:
            item[1] = number(float(item[1]) + dx)
            item[2] = number(float(item[2]) + dy)


def annotation(text, x, y, size=2.0):
    uid = uuid5(NAMESPACE_URL, NAME + text)
    return parse(
        f'(text {q(text)} (at {number(x)} {number(y)} 0) '
        f'(effects (font (face "Noto Sans CJK TC") (size {size} {size})) '
        f'(justify left)) (uuid {uid}))'
    )


def separator(x1, y1, x2, y2):
    uid = uuid5(NAMESPACE_URL, f"{NAME}/line/{x1}/{y1}/{x2}/{y2}")
    return parse(
        f'(polyline (pts (xy {x1} {y1}) (xy {x2} {y2})) '
        f'(stroke (width 0.3) (type dash)) (fill (type none)) (uuid {uid}))'
    )


def build():
    sources = {name: parse((EL / (name + ".kicad_sch")).read_text())
               for name, _, _, _ in PANELS}
    # Ensure every root-sheet child is included exactly once. New sheets must be
    # given an explicit position rather than being silently omitted.
    hierarchy = children(sources["tpa3255-v03"], "sheet")
    expected = {"tpa3255-v03"}
    for sheet in hierarchy:
        filename = next(json.loads(p[2]) for p in children(sheet, "property")
                        if p[1] == '"Sheetfile"')
        expected.add(Path(filename).stem)
    if expected != set(sources):
        raise ValueError("Source sheet set has changed; update the overview layout")

    libraries = {}
    items = []
    allowed = {"symbol", "wire", "bus", "bus_entry", "junction", "no_connect",
               "global_label", "text", "polyline", "rectangle", "circle", "arc"}
    metadata = {"version", "generator", "generator_version", "uuid", "paper",
                "title_block", "lib_symbols", "sheet", "sheet_instances",
                "embedded_fonts"}
    for name, col, row, title in PANELS:
        source = sources[name]
        dx, dy = col * 419.1, 38.1 + row * 279.4
        for symbol in children(child(source, "lib_symbols"), "symbol"):
            if symbol[1] in libraries and libraries[symbol[1]] != symbol:
                raise ValueError(f"Conflicting library symbol: {symbol[1]}")
            libraries[symbol[1]] = copy.deepcopy(symbol)
        for original in source[1:]:
            key = original[0]
            if key in metadata:
                continue
            if key not in allowed:
                # Local/hierarchical labels need namespacing before flattening.
                raise ValueError(f"Unsupported source item in {name}: {key}")
            item = copy.deepcopy(original)
            if key == "text":
                at = child(item, "at")
                if float(at[2]) == 15:
                    continue  # Replaced with bilingual section title below.
                if name == "tpa3255-v03" and float(at[2]) == 22:
                    item[1] = q("Matching net labels connect throughout this single page.")
                if name == "power-control" and float(at[2]) == 23:
                    item[1] = q("PVDD from section 08. 12V standby remains on; no mains wiring on this PCB.")
            translate(item, dx, dy)
            if key == "symbol":
                instances = child(item, "instances")
                project = child(instances, "project")
                path = child(project, "path")
                instances[:] = ["instances", ["project", q(NAME),
                    ["path", q("/" + UUID), copy.deepcopy(child(path, "reference")),
                     copy.deepcopy(child(path, "unit"))]]]
            items.append(item)
        items.append(annotation(title, 15 + dx, 15 + dy, 3.0))

    drawing = parse(
        f'(kicad_sch (version 20250114) (generator "diy_tpa3255_overview") '
        f'(uuid {UUID}) (paper "A0" portrait) '
        '(title_block (title "TPA3255 V0.3 / COMPLETE SINGLE-PAGE SCHEMATIC") '
        '(date "2026-09-11") (rev "0.3 REVIEW") '
        '(comment 1 "Derived from eight-sheet source; electrical draft / no hardware validation")))'
    )
    drawing.append(["lib_symbols", *[libraries[k] for k in sorted(libraries)]])
    drawing.extend(items)
    drawing.extend([
        annotation("TPA3255 V0.3  完整電路總圖", 15, 22, 5.0),
        annotation("音訊：01 輸入 → 02 驅動 → 04 功率輸出；03 回授由輸出返回輸入。", 15, 34),
        annotation("同名網路標籤表示相連。180 個元件完整保留；A0 單頁，可放大閱讀。", 15, 42),
        separator(418, 48, 418, 1157),
        *[separator(12, y, 829, y) for y in (322, 601.4, 880.8)],
        annotation("供電／控制：05 類比供電、06 控制供電；07 Trigger → 08 電源開關／RESET → 04 功率級。", 15, 1161, 1.8),
        annotation("低壓音訊與控制草案；機內市電區另圖規劃。尚未完成走線及實機驗證。", 15, 1170, 1.8),
        ["sheet_instances", ["path", q("/"), ["page", q("1")]]],
    ])
    OUTPUT.write_text("(kicad_sch\n" + "\n".join("  " + dump(v) for v in drawing[1:]) + "\n)\n")
    (EL / (NAME + ".kicad_pro")).write_text("{}\n")
    hashes = {name + ".kicad_sch": hashlib.sha256((EL / (name + ".kicad_sch")).read_bytes()).hexdigest()
              for name in sorted(sources)}
    MANIFEST.write_text(json.dumps({"sources": hashes,
        "overview_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}, indent=2) + "\n")
    print(f"Generated {OUTPUT.relative_to(ROOT)} from {len(sources)} maintained sheets")


if __name__ == "__main__":
    build()
