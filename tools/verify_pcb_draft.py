"""Check placement connectivity/geometry; explicitly retain all unrouted DRC items."""
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import pcbnew as p

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'electrical/pcb-draft'
SCH=ROOT/'electrical/v03/tpa3255-v03.kicad_sch'


def main():
    board=p.LoadBoard(str(OUT/'tpa3255-placement.kicad_pcb'))
    fps={fp.GetReference():fp for fp in board.GetFootprints()}
    with tempfile.TemporaryDirectory(prefix='verify-placement-') as td:
        netfile=Path(td)/'source.xml'
        subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadxml','-o',str(netfile),str(SCH)],check=True)
        source=ET.parse(netfile).getroot()
    comps={c.attrib['ref']:c for c in source.findall('./components/comp')}
    assert set(fps)==set(comps)|{'H1','H2','H3','H4'}
    expected={}
    for net in source.findall('./nets/net'):
        for node in net.findall('node'):
            expected[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
    actual={}; numbered_pads=0
    sides=Counter()
    for ref,c in comps.items():
        fp=fps[ref]; assert fp.GetValue()==c.findtext('value'),ref
        linked=c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]
        assert fp.GetPath().AsString()==linked,(ref,fp.GetPath().AsString(),linked)
        sides['front' if fp.GetLayer()==p.F_Cu else 'back']+=1
        for pad in fp.Pads():
            if not pad.GetNumber(): continue
            key=(ref,pad.GetNumber()); numbered_pads+=1
            # DPAK has a lead and tab sharing cathode number 2.
            assert key not in actual or actual[key]==pad.GetNetname(),key
            actual[key]=pad.GetNetname()
            if pad.GetAttribute()==p.PAD_ATTRIB_PTH:
                assert pad.GetLayerSet().Contains(p.F_Mask) and pad.GetLayerSet().Contains(p.B_Mask),(ref,pad.GetNumber(),'mask')
            box=pad.GetBoundingBox()
            assert box.GetLeft()>=0 and box.GetTop()>=0 and box.GetRight()<=p.FromMM(220) and box.GetBottom()<=p.FromMM(160),(ref,'outside board')
    assert actual==expected,'Schematic/board pad-to-net mismatch'
    # Also compare complete node groups to the maintained schematic contract.
    groups={}; contract={}
    for node,net in actual.items(): groups.setdefault(net,set()).add(node)
    with (ROOT/'electrical/v03/expected-connections.csv').open() as f:
        for row in csv.DictReader(f):
            node=(row['reference'],row['pin'])
            net=row['net'] if row['net']!='NC' else 'NC:'+':'.join(node)
            contract.setdefault(net,set()).add(node)
    assert {frozenset(g) for g in groups.values()}=={frozenset(g) for g in contract.values()}
    # Independent critical physical package checks.
    assert {pad.GetNumber() for pad in fps['U1'].Pads()}=={str(n) for n in range(1,45)}
    assert fps['U401'].FindPadByNumber('21').GetNetname()=='GND'
    assert fps['D303'].FindPadByNumber('1').GetNetname()=='AUDIO_MR'
    assert fps['D303'].FindPadByNumber('3').GetNetname()=='AUX_GOOD'
    assert len(groups[fps['D303'].FindPadByNumber('2').GetNetname()])==1
    for ref in ['D301','D302']:
        fp=fps[ref]
        assert fp.FindPadByNumber('2').GetPosition().x<fp.FindPadByNumber('1').GetPosition().x,ref
    assert len(board.Tracks())==0 and board.GetAreaCount()==0
    assert board.GetCopperLayerCount()==4
    subprocess.run(['kicad-cli','pcb','drc','--format','json','-o',str(OUT/'drc.json'),str(OUT/'tpa3255-placement.kicad_pcb')],check=True)
    drc=json.loads((OUT/'drc.json').read_text())
    types=Counter(v['type'] for v in drc['violations'])
    # An unrouted study must never be reported as a clean fabrication DRC.
    assert not drc['violations'],types
    assert drc['unconnected_items'],'Unexpectedly routed or missing connectivity'
    report=f'''# PCB 配置草案檢查

- KiCad {p.Version()}；{len(comps)} 個電路元件、4 個固定孔；{sides['front']} 個元件在正面、{sides['back']} 個在背面。
- {len(actual)} 個電氣腳號（{numbered_pads} 個編號銅焊盤，DPAK 陰極腳與散熱片共用腳號）、{len(groups)} 個網路，與最新原理圖及預期接線群組逐一吻合；符號 UUID 對應已核對。
- 核對 TPA3255 的 44 腳頂面散熱封裝、TPS26631 第 21 腳接地、BAT54 第 3 腳陰極／第 2 腳 NC，以及兩顆軸向二極體的陰極標記與焊盤編號。
- 通孔焊盤的正反面阻焊開口與焊盤位於板內已檢查。
- 幾何／封裝 DRC 違規 {len(drc['violations'])} 項；**仍有 {len(drc['unconnected_items'])} 項未連接**。完整原始結果在 [drc.json](drc.json)，未排除這些未連接項目。
- 板形暂用 220×160 mm、4 層；0 條走線、0 個覆銅區。幾何檢查不表示佈局已適合高功率或低噪聲。

**未通過製造放行。** 多數被動件與接頭仍是尺寸占位，未核定料號、額定與孔位；尚待 12V 保護、回授／啟停與散熱審查、走線、地平面、機箱配合和實機驗證。本報告不證明音質、穩定度、溫升、電流承載或市電安全。
'''.replace('暂用','暫用')
    (OUT/'validation.md').write_text(report)
    print(report)


if __name__=='__main__': main()
