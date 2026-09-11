"""Check the derived overview against live source netlists and the pin contract."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from build_schematic_overview import EL, MANIFEST, OUTPUT, child, children, parse, walk


def run(*args):
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout


def netlist(schematic, output):
    run("kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
        "-o", str(output), str(schematic))
    root = ET.parse(output).getroot()
    components = {}
    for c in root.findall("./components/comp"):
        components[c.attrib["ref"]] = (
            c.findtext("value"), c.findtext("footprint"), c.findtext("datasheet"),
            tuple(sorted(c.find("libsource").attrib.items())),
        )
    groups = {}
    for net in root.findall("./nets/net"):
        nodes = frozenset((n.attrib["ref"], n.attrib["pin"])
                          for n in net.findall("node"))
        groups[nodes] = net.attrib["name"]
    return components, groups


def main():
    manifest = json.loads(MANIFEST.read_text())
    for name, digest in manifest["sources"].items():
        assert hashlib.sha256((EL / name).read_bytes()).hexdigest() == digest, (name, "overview is stale")
    assert hashlib.sha256(OUTPUT.read_bytes()).hexdigest() == manifest["overview_sha256"], "Overview was edited; rebuild from source"
    drawing = parse(OUTPUT.read_text())
    assert not children(drawing, "sheet"), "Overview must be one native sheet"
    assert child(drawing, "paper") == ["paper", '"A0"', "portrait"]
    assert len(children(drawing, "sheet_instances")) == 1
    # No duplicated UUIDs after flattening (including wires and global labels).
    uuids = [v[1] for v in walk(drawing) if v[0] == "uuid"]
    assert len(uuids) == len(set(uuids)), "Duplicate UUID"
    # KiCad XML omits cross-sheet power-unit UUIDs from some multi-unit component
    # timestamp lists. Compare every native symbol instance directly instead.
    def identities(trees):
        result = {}
        for tree in trees:
            for symbol in children(tree, "symbol"):
                uid = child(symbol, "uuid")[1]
                assert uid not in result, uid
                result[uid] = (
                    child(symbol, "lib_id")[1], child(symbol, "unit")[1],
                    tuple(sorted((p[1], p[2]) for p in children(symbol, "property"))),
                    tuple(child(symbol, key)[1] for key in ("in_bom", "on_board", "dnp")),
                )
        return result
    source_trees = [parse((EL / name).read_text()) for name in manifest["sources"]]
    assert identities(source_trees) == identities([drawing]), "Symbol UUID/unit/properties changed"
    contract = {}
    with (EL / "expected-connections.csv").open() as f:
        for row in csv.DictReader(f):
            node = row["reference"], row["pin"]
            name = row["net"] if row["net"] != "NC" else "NC:" + ":".join(node)
            contract.setdefault(name, set()).add(node)
    with tempfile.TemporaryDirectory(prefix="tpa-overview-") as temp:
        temp = Path(temp)
        source, source_nets = netlist(EL / "tpa3255-v03.kicad_sch", temp / "source.xml")
        merged, merged_nets = netlist(OUTPUT, temp / "overview.xml")
        assert source == merged, "Component values/properties/UUIDs differ"
        assert source_nets.keys() == merged_nets.keys(), "Electrical connectivity changed"
        assert set(merged_nets) == {frozenset(nodes) for nodes in contract.values()}, "Pin contract mismatch"
        # User-defined net names must survive; KiCad-generated paths for unnamed
        # local nets and NC pins naturally change when the hierarchy is flattened.
        for group, name in source_nets.items():
            if not name.startswith(("/", "unconnected-(")):
                assert name == merged_nets[group], (name, merged_nets[group])
        violations = {}
        for name, schematic in [("source", EL / "tpa3255-v03.kicad_sch"), ("overview", OUTPUT)]:
            report = temp / (name + "-erc.json")
            run("kicad-cli", "sch", "erc", "--format", "json", "--exit-code-violations",
                "-o", str(report), str(schematic))
            erc = json.loads(report.read_text())
            violations[name] = [v for sheet in erc["sheets"] for v in sheet["violations"]]
            assert not violations[name], violations[name]
    pins = sum(len(group) for group in merged_nets)
    version = run("kicad-cli", "version").strip()
    report = f"""# 單頁總圖合併檢查

- KiCad {version}；A0 直式、單一原生頁面，無子頁。
- {len(merged)} 個元件的編號、數值、符號來源、Footprint／Datasheet 與符號 UUID 均與八頁來源一致。
- {pins} 個電氣腳位、{len(merged_nets)} 個網路群組與八頁來源及 `expected-connections.csv` 完全吻合。
- 保留自訂網路名稱；KiCad 自動產生的無標籤網路路徑隨合併改變，以腳位群組比較確認等價。
- 八頁來源及單頁總圖 ERC 均為 0 錯誤／0 警告，無排除項目；UUID 無重複。
- `overview-sources.json` 記錄來源及總圖 SHA-256；來源變動而未重建時，檢查會失敗。

只調整圖面排版，未改動電路，未新增性能或實機驗證。既有 PCB 仍對應八頁來源的階層路徑，請從 `tpa3255-v03.kicad_pro` 更新 PCB；單頁版供審閱及衍生編輯。

重建與檢查：

```sh
python3 tools/build_schematic_overview.py
python3 tools/verify_schematic_overview.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03-overview.kicad_sch --pdf-from-svg --png-width 4800
```
"""
    (EL / "overview-validation.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
