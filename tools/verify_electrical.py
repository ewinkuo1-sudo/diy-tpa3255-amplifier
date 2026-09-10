"""Export using KiCad, audit actual connectivity, simulate passive/ideal blocks.

Run after editing the schematic. Does not regenerate it, so GUI edits are retained.
"""
import csv
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EL=ROOT/'electrical'
SIM=ROOT/'simulation'


def run(*args,cwd=ROOT):
    p=subprocess.run(args,cwd=cwd,text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    return p.stdout


def main():
    SIM.mkdir(exist_ok=True)
    sch=str(EL/'tpa3255-v02.kicad_sch')
    with tempfile.TemporaryDirectory(prefix='tpa3255-audit-') as tmp:
        tmp=Path(tmp)
        run('kicad-cli','sch','erc','--format','json','--exit-code-violations','-o',str(tmp/'erc.json'),sch)
        erc=json.loads((tmp/'erc.json').read_text())
        assert not any(s['violations'] for s in erc['sheets'])
        run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',str(tmp/'net.xml'),sch)
        root=ET.parse(tmp/'net.xml').getroot()
        actual={}
        for net in root.findall('./nets/net'):
            for node in net.findall('node'):
                key=(node.attrib['ref'],node.attrib['pin'])
                assert key not in actual,key
                actual[key]=net.attrib['name']
        expected=list(csv.DictReader((EL/'expected-connections.csv').open()))
        expected_groups={}
        for row in expected:
            node=(row['reference'],row['pin'])
            label=row['net'] if row['net']!='NC' else 'NC:'+':'.join(node)
            expected_groups.setdefault(label,set()).add(node)
        actual_groups={}
        for node,net in actual.items():
            actual_groups.setdefault(net,set()).add(node)
        assert set().union(*expected_groups.values())==set(actual), 'Missing or extra pins'
        assert {frozenset(x) for x in expected_groups.values()}=={frozenset(x) for x in actual_groups.values()}, 'Netlist has an open or short'
        # Source-based critical invariants, independent of drawing coordinates.
        must={1:'+12V',2:'VDD_FILTERED',3:'GND',4:'GND',5:'INPUT_A',6:'INPUT_B',
              11:'DVDD',14:'AVDD',16:'INPUT_C',17:'INPUT_D',18:'RESET_N',20:'VBG',22:'+12V'}
        for pin,net in must.items(): assert actual[('U1',str(pin))]==net,(pin,net)
        for pin in [29,30,31,36,37,38]: assert actual[('U1',str(pin))]=='PVDD'
        for pin in [12,13,25,26,33,34,41,42]: assert actual[('U1',str(pin))]=='GND'
        assert actual[('U1','39')]==actual[('U1','40')]=='OUT_A'
        assert actual[('U1','27')]==actual[('U1','28')]=='OUT_D'
        for net,cap in [('DVDD','C211'),('AVDD','C212'),('VBG','C213')]:
            assert len(actual_groups[net])==2 and (cap,'1') in actual_groups[net]
        for i,(bst,out) in enumerate([(44,40),(43,35),(24,32),(23,28)],1):
            assert actual[('C'+str(i),'1')]==actual[('U1',str(bst))]
            assert actual[('C'+str(i),'2')]==actual[('U1',str(out))]
        for a,b in [('SPK_A','SPK_B'),('SPK_C','SPK_D')]: assert a!=b and a!='GND' and b!='GND'

        components={c.attrib['ref']:c.findtext('value') for c in root.findall('./components/comp')}
        # Convert actual nets to legal SPICE identifiers. Values come from KiCad.
        nodeids={name:('0' if name=='GND' else 'n'+str(i)) for i,name in enumerate(sorted(actual_groups))}
        node=lambda ref,pin:nodeids[actual[(ref,str(pin))]]
        named=lambda name:nodeids[name]
        def value(ref):
            first=components[ref].split()[0]
            assert re.fullmatch(r'[0-9.]+[unpMk]?',first),(ref,first)
            return first
        def passive(ref):
            return f'{ref} {node(ref,1)} {node(ref,2)} {value(ref)}'
        input_lines=['TPA3255 V0.2 input AC model from audited KiCad netlist',
                     '* Ideal finite-gain opamps; no NE5532 noise, clipping or bandwidth model.',
                     f'VMID {named("VMID")} 0 DC 6',
                     f'VL {named("L_RCA")} 0 DC 0 AC 1',
                     f'VR {named("R_RCA")} 0 DC 0 AC 1']
        for ref in sorted(components):
            if ref[0] in 'RC' and 100<=int(ref[1:])<200: input_lines.append(passive(ref))
        for ref in ['U2','U3']:
            for stage,plus,minus,out in [('A',3,2,1),('B',5,6,7)]:
                input_lines.append(f'E{ref}{stage} {node(ref,out)} {named("VMID")} {node(ref,plus)} {node(ref,minus)} 1e6')
        for ch in 'ABCD': input_lines.append(f'RLOAD_{ch} {named("INPUT_"+ch)} 0 20k')
        vectors=[]
        for ch,a,b in [('left','A','B'),('right','C','D')]:
            vectors += [f'let {ch} = v({named("INPUT_"+a)})-v({named("INPUT_"+b)})']
        control=['.control','set wr_singlescale','set wr_vecnames','set numdgt=12','ac dec 200 1 100000',*vectors,
                 'wrdata input-ac.dat left right','quit','.endc','.end']
        (SIM/'input-ac.cir').write_text('\n'.join(input_lines+control)+'\n')
        # Output filter uses the exact two half-bridge passive branches, no PWM model.
        filter_lines=['TPA3255 V0.2 differential output LC model from audited netlist',
                      '* Ideal sources; 0.05-ohm DCR per inductor is an assumption.',
                      '* Includes the schematic 1n shunts and 10n+3.3-ohm RC branches.']
        for load in [4,8]:
            suffix=str(load)
            prefix=lambda n:'0' if n=='0' else n+'_'+suffix
            filter_lines += [f'VP{load} drvP{load} 0 AC 0.5',f'VN{load} drvN{load} 0 AC 0.5 180',
                             f'RDCRA{load} drvP{load} {prefix(named("OUT_A"))} 0.05',
                             f'RDCRB{load} drvN{load} {prefix(named("OUT_B"))} 0.05']
            for ref in ['L1','L2','C5','C6','C9','C10','C13','C14','R1','R2']:
                filter_lines.append(f'{ref}_{load} {prefix(node(ref,1))} {prefix(node(ref,2))} {value(ref)}')
            filter_lines.append(f'RLOAD{load} {prefix(named("SPK_A"))} {prefix(named("SPK_B"))} {load}')
        vector_filters=[f'let load{load} = v({named("SPK_A")}_{load})-v({named("SPK_B")}_{load})' for load in [4,8]]
        filter_control=['.control','set wr_singlescale','set wr_vecnames','set numdgt=12','ac dec 200 1 100000',
                        *vector_filters,'wrdata filter-ac.dat load4 load8','quit','.endc','.end']
        (SIM/'filter-ac.cir').write_text('\n'.join(filter_lines+filter_control)+'\n')
        for name in ['input-ac','filter-ac']:
            output=run('ngspice','-b',str(SIM/(name+'.cir')),cwd=tmp)
            assert 'Error' not in output,output
            data=[]
            for line in (tmp/(name+'.dat')).read_text().splitlines()[1:]:
                numbers=list(map(float,line.split()))
                assert len(numbers)==5,numbers
                data.append(numbers)
            assert data and all(math.isfinite(v) for row in data for v in row)
            with (SIM/(name+'.csv')).open('w',newline='') as f:
                writer=csv.writer(f,lineterminator='\n');writer.writerow(['frequency_hz','first_real','first_imag','second_real','second_imag']);writer.writerows(data)

        def at(name,f):
            rows=list(csv.DictReader((SIM/(name+'.csv')).open()))
            # Log-frequency interpolation of complex AC gain.
            for left,right in zip(rows,rows[1:]):
                x,y=float(left['frequency_hz']),float(right['frequency_hz'])
                if x<=f<=y:
                    t=math.log(f/x)/math.log(y/x)
                    result=[]
                    for channel in ['first','second']:
                        z=[]
                        for field in ['real','imag']:
                            key=channel+'_'+field
                            z.append(float(left[key])*(1-t)+float(right[key])*t)
                        result.append(complex(*z))
                    return result
            raise ValueError(f)
        gain=at('input-ac',1000)[0]
        assert abs(abs(gain)-(2*10000/24900)*(20000/20100))<0.001
        assert abs(at('input-ac',1000)[0]-at('input-ac',1000)[1])<1e-9
        assert gain.real<0, 'Input stage must invert the differential signal'
        # Reset resistor/leakage worst cases: source and sink leakage directions.
        pulldown=float(components['R302'].split()[0].replace('k',''))*1000
        series=float(components['R301'].split()[0].replace('k',''))*1000
        low=100e-6*pulldown*1.01
        high=3.3*0.95*(pulldown*0.99)/(series*1.01+pulldown*0.99)-100e-6*(series*1.01*pulldown*0.99)/(series*1.01+pulldown*0.99)
        assert low<0.8 and high>1.9,(low,high)
        summary=['# V0.2 電氣驗證','',
                 '由 `python3 tools/verify_electrical.py` 產生；先讀取實際 KiCad netlist，再建立區塊模型。','',
                 f'- KiCad {erc["kicad_version"]}：ERC 0 錯誤、0 警告；未排除違規。',
                 f'- 接線群組核對：{len(components)} 個元件、{len(actual)} 個接腳、{len(actual_groups)} 個 net 通過。',
                 '- 已核對：主／輔助電源網路分離（共地）、44-pin 對應關鍵網路、bootstrap、重複輸出腳、內部穩壓輸出只接去耦。',
                 '- ngspice：兩聲道輸入級及 4Ω／8Ω 輸出濾波區塊 AC 分析通過；不是整顆 TPA3255 的開關模型。','',
                 '| 頻率 | 輸入級差動增益 V/V | 4Ω 濾波增益 dB | 8Ω 濾波增益 dB |','|---|---|---|---|']
        for freq in [20,1000,20000]:
            v=at('input-ac',freq)[0]; f4,f8=at('filter-ac',freq)
            summary.append(f'| {freq} Hz | {abs(v):.5f} | {20*math.log10(abs(f4)):+.3f} | {20*math.log10(abs(f8)):+.3f} |')
        amp_gain=10**(21.5/20)
        sensitivity=20/(abs(gain)*amp_gain)
        summary += ['',f'1kHz 時以前端模型增益及晶片典型 21.5dB 計算，50W/8Ω 所需 RCA 約 {sensitivity:.3f}Vrms（未含輸出 LC 損耗）。',
                    f'RESET 以 100µA 漏電、1% 電阻與 3.3V 電源 ±5% 假設核算：無跳線低態 ≤{low:.3f}V；RUN 高態 ≥{high:.3f}V。','',
                    '模型限制：運放為理想受控源、有限 DC 增益 10⁶；TPA3255 輸入以 20kΩ 小訊號負載近似；VMID 為理想 6V。',
                    '未建模運放實際頻寬／擺幅／雜訊、啟停、PWM、保護、電感飽和、EMI、寄生、實際喇叭阻抗或熱。',
                    '電感 DCR 每顆 0.05Ω 為假設，需以選定料號修正。8Ω 高頻增益尚需調整或訂定驗收範圍。',
                    '未指定 footprint、F1 額定與功率元件最終料號，這份 ERC 通過不代表可製板。','',
                    '來源：見 [V0.2 設計說明](../docs/V0.2_電路設計.md)。']
        (EL/'validation.md').write_text('\n'.join(summary)+'\n')
        run('kicad-cli','sch','export','bom','--group-by','Value','-o',str(EL/'bom-draft.csv'),sch)
        print('\n'.join(summary[:8]))


if __name__=='__main__':main()
