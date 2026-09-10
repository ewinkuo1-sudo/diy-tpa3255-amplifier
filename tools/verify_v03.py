"""Audit the V0.3 netlist; run reduced AC and functional power-sequence models.

No TPA3255 PWM, opamp distortion, semiconductor transient or EMI model is claimed.
"""
import csv
import json
import math
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EL=ROOT/'electrical/v03'
SIM=ROOT/'simulation/v03'


def run(*args,cwd=ROOT):
    result=subprocess.run(args,cwd=cwd,text=True,capture_output=True)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout


def write_csv(path,header,rows):
    with path.open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(header);w.writerows(rows)


def interpolate(data,f):
    for a,b in zip(data,data[1:]):
        if a[0]<=f<=b[0]:
            t=math.log(f/a[0])/math.log(b[0]/a[0])
            z=[x*(1-t)+y*t for x,y in zip(a[1:],b[1:])]
            return [complex(*z[i:i+2]) for i in range(0,len(z),2)]
    raise ValueError(f)


def main():
    SIM.mkdir(parents=True,exist_ok=True)
    sch=str(EL/'tpa3255-v03.kicad_sch')
    with tempfile.TemporaryDirectory(prefix='tpa-v03-') as td:
        tmp=Path(td)
        run('kicad-cli','sch','erc','--format','json','--exit-code-violations','-o',str(tmp/'erc.json'),sch)
        erc=json.loads((tmp/'erc.json').read_text())
        assert not any(sheet['violations'] for sheet in erc['sheets'])
        run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',str(tmp/'net.xml'),sch)
        root=ET.parse(tmp/'net.xml').getroot()
        actual={}
        groups={}
        for net in root.findall('./nets/net'):
            name=net.attrib['name'];groups[name]=set()
            for node in net.findall('node'):
                key=(node.attrib['ref'],node.attrib['pin'])
                assert key not in actual
                actual[key]=name;groups[name].add(key)
        expected={}
        with (EL/'expected-connections.csv').open() as f:
            for row in csv.DictReader(f):
                node=(row['reference'],row['pin'])
                name=row['net'] if row['net']!='NC' else 'NC:'+':'.join(node)
                expected.setdefault(name,set()).add(node)
        assert set(actual)==set().union(*expected.values())
        assert {frozenset(v) for v in groups.values()}=={frozenset(v) for v in expected.values()}
        net=lambda ref,pin:actual[(ref,str(pin))]
        def pins(ref,mapping):
            for pin,name in mapping.items(): assert net(ref,pin)==name,(ref,pin,name)
        # Critical checks use physical pin numbers independently of the drawing generator.
        pins('U1',{1:'+12V',2:'VDD_FILTERED',3:'GND',4:'GND',5:'INPUT_A',6:'INPUT_B',
                   11:'DVDD',14:'AVDD',16:'INPUT_C',17:'INPUT_D',18:'RESET_N',20:'VBG',22:'+12V'})
        for n in [29,30,31,36,37,38]:pins('U1',{n:'PVDD'})
        for n in [12,13,25,26,33,34,41,42]:pins('U1',{n:'GND'})
        pins('U1',{39:'OUT_A',40:'OUT_A',27:'OUT_D',28:'OUT_D'})
        for i,(bst,out) in enumerate([(44,40),(43,35),(24,32),(23,28)],1):
            assert net('C'+str(i),1)==net('U1',bst)
            assert net('C'+str(i),2)==net('U1',out)
        for name,cap in [('DVDD','C211'),('AVDD','C212'),('VBG','C213')]:
            assert len(groups[name])==2 and (cap,'1') in groups[name]
        for i,ch in enumerate('ABCD'):
            arm=('L_NEG','L_POS','R_NEG','R_POS')[i]
            pins('R'+str(150+i),{1:arm,2:'SUM_'+ch})
            pins('C'+str(150+i),{1:'SUM_'+ch,2:'INPUT_'+ch})
            pins('R'+str(501+i),{1:'SUM_'+ch,2:'SPK_'+ch})
            pins('C'+str(501+i),{1:'SUM_'+ch,2:'FB_MID_'+ch})
            pins('C'+str(505+i),{1:'FB_MID_'+ch,2:'SPK_'+ch})
            pins('R'+str(505+i),{1:'FB_MID_'+ch,2:'GND'})
        assert groups['TRIG_RETURN']=={('J301','2'),('D301','1'),('U301','2')}
        pins('U301',{1:'TRIG_LED',2:'TRIG_RETURN',3:'GND',4:'TRIG_N'})
        pins('D301',{1:'TRIG_RETURN',2:'TRIG_LED'})
        pins('U303',{1:'AUX_GOOD',2:'GND',3:'RUN_REQUEST',5:'SENSE_12V',6:'+3V3_CTRL'})
        pins('D302',{1:'HOLD_CHARGE',2:'HOLD_CAP'})
        # BAT54 SOT-23: physical pin 2 is NC; cathode is pin 3.
        pins('D303',{1:'AUDIO_MR',3:'AUX_GOOD'})
        assert len(groups[net('D303',2)])==1
        pins('U306',{1:'AUDIO_GOOD',2:'GND',3:'AUDIO_MR',4:'AUDIO_DELAY',5:'SENSE_PVDD',6:'+3V3_CTRL'})
        pins('U401',{1:'DC_PROTECTED',2:'DC_PROTECTED',3:'DC_PROTECTED',6:'DC_PROTECTED',
                     7:'EFUSE_UV',8:'EFUSE_OV',9:'GND',10:'EFUSE_DVDT',11:'EFUSE_ILIM',
                     13:'EFUSE_SHDN',16:'EFUSE_PGTH',17:'AUDIO_MR',18:'PVDD',19:'PVDD',20:'PVDD',21:'GND'})
        pins('D401',{1:'FUSED_48V',2:'DC_PROTECTED'})
        pins('U601',{2:'L_RX_COLD',3:'L_RX_HOT',4:'GND',5:'R_RX_HOT',6:'R_RX_COLD',
                     8:'R_RX_REF',9:'R_RX_OUT',10:'R_RX_OUT',11:'+12V_XLR',12:'L_RX_OUT',13:'L_RX_OUT',14:'L_RX_REF'})
        pins('U602',{1:'L_RX_REF',2:'L_RX_REF',3:'VMID',4:'GND',5:'VMID',6:'R_RX_REF',7:'R_RX_REF',8:'+12V_XLR'})
        for idx,ch in enumerate(('L','R')):
            pins('J'+str(601+idx),{1:'CHASSIS',2:ch+'_XLR_HOT',3:ch+'_XLR_COLD'})
            pins('J'+str(603+idx),{1:ch+'_RCA',2:ch+'_SELECTED',3:ch+'_XLR'})
            pins('C'+str(101+20*idx),{1:ch+'_SELECTED'})
            assert net('C'+str(101+20*idx),2)==net('R'+str(102+20*idx),1)
            for offset,leg in enumerate(('HOT','COLD')):
                pins('R'+str(601+2*idx+offset),{1:ch+'_XLR_'+leg,2:ch+'_LINE_'+leg})
                pins('C'+str(601+2*idx+offset),{1:ch+'_LINE_'+leg,2:ch+'_RX_'+leg})
            pins('C'+str(605+idx),{1:ch+'_RX_OUT',2:ch+'_XLR'})
        assert groups['CHASSIS']=={('J601','1'),('J602','1'),('J605','1'),('J605','2'),('R608','1')}
        pins('R608',{1:'CHASSIS',2:'GND'})
        for ref in ['U302','U304','U305','U307']:pins(ref,{3:'GND',5:'+3V3_CTRL'})
        pins('U302',{2:'TRIG_N',4:'AUTO_REQUEST'})
        pins('U304',{2:'AUX_GOOD',4:'AUX_BUFFER'})
        pins('U305',{2:'HOLD_CAP',4:'EFUSE_ENABLE'})
        pins('U307',{2:'AUDIO_GOOD',4:'RESET_DRIVE'})
        for ref,ps in [('U401',[4,5,12,14]),('U303',[4])]:
            for pin in ps: assert len(groups[net(ref,pin)])==1

        values={c.attrib['ref']:c.findtext('value') for c in root.findall('./components/comp')}
        def val(ref):
            text=values[ref].split()[0]
            scale={'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'M':1e6}
            return float(text[:-1])*scale[text[-1]] if text[-1] in scale else float(text)
        for ref in ['L1','L2','L3','L4']: assert values[ref]=='10u / MA5172-AE'
        # Component selection data: Coilcraft Doc 943-1, 25C maximum DCR.
        dcr=0.026
        names={n:('0' if n=='GND' else 'n'+str(i)) for i,n in enumerate(sorted(groups))}
        node=lambda ref,p:names[net(ref,p)]
        named=lambda n:names[n]
        ac_results=[]
        gains={};sensitivities={};cmrr=[]
        cases=[(mode,load,pole,False) for mode in ['rca','xlr'] for load in [4,8,1e9] for pole in [0,100000]]
        cases += [('common',8,0,False),('common',8,0,True)]
        for mode,load,pole,mismatch in cases:
            case=f'ac-{mode}-{int(load) if load<1e8 else "open"}-pole{pole}'+('-mismatch' if mismatch else '')
            lines=['V0.3 REDUCED AC model - not TPA3255 PWM or hardware stability proof',
                   '* Ideal opamps (A0=1e6), ideal VMID; no noise, clipping or real opamp BW.',
                   '* INA2137: nominal internal 12k/6k network, not manufacturer semiconductor model.',
                   '* Common-mode mismatch: external R +/-0.1%, paired C +/-0.5%; internal ratios ideal.',
                   '* TPA gain is a typical constant; 100kHz pole case is an arbitrary sensitivity study.',
                   f'VMID {named("VMID")} 0 DC 6',f'V12 {named("+12V")} 0 DC 12']
            for idx,ch in enumerate(('L','R')):
                lines += [f'V{ch} {named(ch+"_RCA")} 0 DC 0 AC {int(mode=="rca")}',
                          f'V{ch}H {named(ch+"_XLR_HOT")} 0 DC 0 AC {0 if mode=="rca" else 1 if mode=="common" else .5}',
                          f'V{ch}C {named(ch+"_XLR_COLD")} 0 DC 0 AC {0 if mode=="rca" else 1 if mode=="common" else .5} {180 if mode=="xlr" else 0}']
                jack='J'+str(603+idx)
                lines += [f'VSELECT_{ch} {node(jack,2)} {node(jack,1 if mode=="rca" else 3)} 0']
                # Physical INA2137 pins from TI SBOS072; all four resistors are internal.
                hot,cold,out,ref,sense=(3,2,13,14,12) if idx==0 else (5,6,9,8,10)
                lines += [f'RRX_{ch}P {node("U601",hot)} rx_{ch}p 12k',
                          f'RRX_{ch}REF {node("U601",ref)} rx_{ch}p 6k',
                          f'RRX_{ch}N {node("U601",cold)} rx_{ch}n 12k',
                          f'RRX_{ch}FB {node("U601",sense)} rx_{ch}n 6k',
                          f'ERX_{ch} {node("U601",out)} {named("VMID")} rx_{ch}p rx_{ch}n 1e6']
            for ref in sorted(values):
                if ref[0] not in 'RCL':continue
                n=int(ref[1:])
                if n<20 or 100<=n<200 or 500<=n<700:
                    value=val(ref)
                    if mismatch and ref in ['R601','R602','R603','R604']:
                        value*=1.001 if n%2 else .999
                    if mismatch and ref in ['C601','C602','C603','C604']:
                        value*=1.005 if n%2 else .995
                    lines.append(f'{ref} {node(ref,1)} {node(ref,2)} {value:.12g}')
            for u in ['U2','U3','U602']:
                for stage,plus,minus,out in [('A',3,2,1),('B',5,6,7)]:
                    lines.append(f'E{u}{stage} {node(u,out)} {named("VMID")} {node(u,plus)} {node(u,minus)} 1e6')
            for ch in 'ABCD':
                lines += [f'RINPUT_{ch} {named("INPUT_"+ch)} 0 20k',
                          f'ERAW_{ch} raw_{ch} 0 {named("INPUT_"+ch)} 0 {-10**(21.5/20):.12g}']
                source='raw_'+ch
                if pole:
                    lines += [f'RP_{ch} raw_{ch} pole_{ch} 1k',f'CP_{ch} pole_{ch} 0 {1/(2*math.pi*pole*1000):.12g}',
                              f'EBUF_{ch} buf_{ch} 0 pole_{ch} 0 1']
                    source='buf_'+ch
                lines.append(f'RDCR_{ch} {source} {named("OUT_"+ch)} {dcr}')
            lines += [f'RLOAD_L {named("SPK_A")} {named("SPK_B")} {load}',
                      f'RLOAD_R {named("SPK_C")} {named("SPK_D")} {load}',
                      '.control','set wr_singlescale','set wr_vecnames','set numdgt=12','ac dec 200 1 1000000',
                      f'let left = v({named("SPK_A")})-v({named("SPK_B")})',
                      f'let right = v({named("SPK_C")})-v({named("SPK_D")})',
                      f'let opneg = v({named("L_NEG")})',f'let oppos = v({named("L_POS")})',
                      f'wrdata {case}.dat left right opneg oppos','quit','.endc','.end']
            deck=SIM/(case+'.cir');deck.write_text('\n'.join(lines)+'\n')
            output=run('ngspice','-b',str(deck),cwd=tmp)
            assert 'Error' not in output,output
            data=[list(map(float,line.split())) for line in (tmp/(case+'.dat')).read_text().splitlines()[1:]]
            assert all(len(row)==9 and all(math.isfinite(v) for v in row) for row in data)
            write_csv(SIM/(case+'.csv'),['frequency_hz','left_real','left_imag','right_real','right_imag','opneg_real','opneg_imag','oppos_real','oppos_imag'],data)
            g1=abs(interpolate(data,1000)[0])
            assert abs(interpolate(data,1000)[0]-interpolate(data,1000)[1])<1e-8
            if mode=='common':
                for freq in [20,1000,20000]:
                    rejection=20*math.log10(gains[('xlr',8,0,freq)]/max(abs(interpolate(data,freq)[0]),1e-20))
                    assert rejection>(50 if mismatch else 80),(freq,rejection)
                    cmrr.append([int(mismatch),freq,rejection])
                continue
            assert interpolate(data,1000)[0].real>0
            if load==8 and pole==0:
                sensitivity=20/g1
                sensitivities[mode]=sensitivity
                assert sensitivity<(2.3 if mode=='rca' else 4.6),'Insufficient nominal Z10 input margin'
                op_swing=max(abs(z) for z in interpolate(data,1000)[2:])*sensitivity*math.sqrt(2)
            for freq in [20,1000,20000]:
                gain=abs(interpolate(data,freq)[0])
                gains[(mode,load,pole,freq)]=gain
                ac_results.append([mode,load,pole,freq,gain,20*math.log10(gain/g1)])
        for load in [4,8,1e9]:
            for pole in [0,100000]:
                for freq in [20,1000,20000]:
                    delta=20*math.log10(2*gains[('xlr',load,pole,freq)]/gains[('rca',load,pole,freq)])
                    assert abs(delta)<.1,(load,pole,freq,delta)
        write_csv(SIM/'ac-summary.csv',['input','load_ohm','assumed_plant_pole_hz','frequency_hz','gain_v_v','db_relative_1khz'],ac_results)
        write_csv(SIM/'xlr-external-imbalance.csv',['external_mismatch','frequency_hz','cmrr_db_ideal_internal_network'],cmrr)

        # Datasheet equations and deliberately conservative design assumptions.
        threshold=lambda top,bottom,v:v*(1+val(top)/val(bottom))
        aux=threshold('R306','R307',.405); pv=threshold('R311','R312',.405)
        ov=threshold('R403','R404',1.2)
        ovmax=1.224*(1+val('R403')*1.001/(val('R404')*.999))+150e-9*val('R403')
        assert ovmax<53.5
        delay=val('C305')*1e9/175+.0005
        delaymin=.62*.95  # datasheet minimum at 180nF, with 5% capacitor allowance
        assert delaymin>.250
        resetlow=(100e-6+10e-6)*val('R302')*1.01
        pd=val('R302')*.99;rs=val('R301')*1.01
        resethigh=(3.3*.95-.2)*pd/(pd+rs)-100e-6*pd*rs/(pd+rs)
        assert resetlow<.8 and resethigh>1.9
        assert 20e-6*val('R409')<.8,'eFuse must remain off with logic unpowered'
        trigger_min=(9-1.5)/(val('R303')*1.01)
        assert trigger_min>1e-3 and 3.3*1.05/val('R304')+5e-6<.25e-3
        # Hold timing envelope is an engineering assumption spanning 3V and 4.5V
        # Schmitt table thresholds; verify actual 3.3V timing and diode leakage on hardware.
        rc=val('R310')*val('C304')
        holdmin=rc*.99*.95*math.log((2.4+.5)/(1.97+.5))
        holdmax=rc*1.01*1.05*math.log((3.3-.5)/(.89-.5))
        assert holdmin>.05
        bulk=val('C205')+val('C206')
        slew=20.8e3*48*val('C402')
        charge_current=bulk*48/slew
        # First-order ripple estimate, worst at half duty; copper loss excludes core loss.
        ripple=48/(4*450000*val('L1'))
        coil_rms=math.sqrt(50/8+ripple**2/12)
        copper=coil_rms**2*dcr
        assert coil_rms<6.1
        sequence_tests=check_sequence(val,aux,pv,delay,slew,holdmin)
        run('kicad-cli','sch','export','bom','--group-by','Value','-o',str(EL/'bom-draft.csv'),sch)
        report=['# V0.3 驗證結果','',
                f'- KiCad {erc["kicad_version"]}：ERC 0 錯誤／0 警告，無排除。',
                f'- {len(values)} 元件、{len(actual)} 接腳、{len(groups)} 網路：完整接線群組與關鍵腳位核對通過。',
                '- 額外核對：XLR 正負腳／屏蔽／緩衝參考／輸入選擇、PFFB 同臂與耦合位置、Trigger 隔離、功率供電及靜音控制。',
                f'- 控制時序規格模型：{sequence_tests} 個情境通過；不是控制 IC 的 SPICE 硬體模型。','',
                '## 音訊 AC 簡化模型','',
                '| 輸入 | 負載 | 假設功率級極點 | 20Hz 相對 1kHz | 20kHz 相對 1kHz |','|---|---|---|---|---|']
        for mode,load in [(m,r) for m in ['rca','xlr'] for r in [4,8,1e9]]:
            for pole in [0,100000]:
                rslt=[r for r in ac_results if r[:3]==[mode,load,pole]]
                report.append(f'| {mode.upper()} | {"空載近似" if load>1e8 else str(load)+"Ω"} | {"無限頻寬" if not pole else "100kHz，敏感度試算"} | {rslt[0][5]:+.3f}dB | {rslt[2][5]:+.3f}dB |')
        report += ['',f'無限頻寬功率級模型下，50W/8Ω 所需 RCA 為 {sensitivities["rca"]:.3f}Vrms、XLR 差動為 {sensitivities["xlr"]:.3f}Vrms；低於 Z10 標示的 2.5 / 5Vrms。',
                   'RCA 2.5Vrms 與 XLR 差動 5Vrms 的模型輸出差異，在全部負載／極點案例的 20Hz、1kHz、20kHz 均小於 0.1dB。',
                   '12 組差動／RCA 響應與 2 組共模模型通過；共模模型只評估外部 47Ω 電阻 ±0.1%、配對 47µF 電容 ±0.5% 的影響。',
                   'INA2137 內部電阻比與 REF 驅動在模型中理想化，共模結果不能當成整機 CMRR 規格；需要實測元件不匹配與訊源阻抗。',
                   f'該輸出條件下前端最大交流峰值約 {op_swing:.3f}V，相對 VMID；實際 NE5532 擺幅仍需驗證。',
                   '運放為理想有限增益源；功率級為典型增益線性源。沒有驗證真正的噪聲、THD、開關延遲或回授穩定裕度。',
                   '100kHz 極點是自訂敏感度假設，不能當成原廠 TPA3255 模型。空載 AC 計算成功也不代表實機不振盪。','',
                   '## 控制與元件核算','',
                   f'- 12V 監測名義門檻 {aux:.3f}V；PVDD 監測 {pv:.3f}V。',
                   f'- eFuse 過壓門檻名義 {ov:.3f}V，含比較器／電阻／漏電最壞估算上限 {ovmax:.3f}V。',
                   f'- 電源良好後開聲延遲名義 {delay:.3f}s，180nF 資料表最小值加 5% 電容餘裕約 {delaymin:.3f}s。',
                   f'- 正常 3.3V 控制電源下，關機保持 RC 試算 {holdmin:.3f}–{holdmax:.3f}s；含閾值包絡及 ±5µA 漏電假設，待實測。',
                   f'- RESET 無電源低態核算 ≤{resetlow:.3f}V；RUN 高態核算 ≥{resethigh:.3f}V。',
                   f'- Trigger 設計輸入 9V 時 LED 最小約 {trigger_min*1e3:.3f}mA；12V 標稱約 {(12-1.1)/val("R303")*1e3:.3f}mA。',
                   f'- eFuse 48V 軟啟動名義 {slew:.3f}s；只計 940µF 主電容充電約 {charge_current:.3f}A。',
                   f'- MA5172-AE：50W/8Ω 加估算開關紋波後約 {coil_rms:.3f}Arms，每顆銅損約 {copper:.3f}W（25°C DCR 上限）。',
                   '電感計算不含磁芯損耗；45A 是原廠 10% 電感下降的典型條件，不是連續可用電流。',
                   'PCB 僅有未走線配置草案（見 ../pcb-draft/）；尚無完成的 PCB／製造 DRC、實機電感溫升／保護試驗、Z10 Trigger 電壓與極性量測、功率開關熱驗證或整機音質實測。',
                   '資料來源與設計限制見 [V0.3 設計說明](../../docs/V0.3_設計說明.md)。']
        (EL/'validation.md').write_text('\n'.join(report)+'\n')
        print('\n'.join(report[:6]));print(f'Input sensitivity {sensitivities}; delay {delay:.3f}s; hold >= {holdmin:.3f}s')


def check_sequence(val,aux_threshold,pv_threshold,audio_delay,ramp_time,hold_time):
    """Functional acceptance model: derive timing/thresholds from audited values.

    Tracks slow DC rise, eFuse latch, request and rail supervision. It omits
    actual device propagation, supply impedance, opamp bias settling and PWM.
    """
    cases={
        'normal':lambda t:(1<t<6,12,48,False),
        'missing_48v':lambda t:(t>1,12,0,False),
        'missing_12v':lambda t:(t>1,0,48,False),
        'trigger_bounce':lambda t:(1<t<1.005,12,48,False),
        'brownout_48v':lambda t:(t>1,12,30 if 6<t<6.5 else 48,False),
        'brownout_12v':lambda t:(t>1,10 if 6<t<6.5 else 12,48,False),
        'efuse_latch':lambda t:(1<t<7 or t>8,12,48,6<t<6.1),
        # Two independent internal AC/DC modules may establish their rails in
        # either order. Step timings are test stimuli, not vendor waveforms.
        'psu_48v_late':lambda t:(t>0,12 if t>=1 else 0,48 if t>=3 else 0,False),
        'psu_12v_late':lambda t:(t>0,12 if t>=3 else 0,48 if t>=1 else 0,False),
    }
    for name,event in cases.items():
        dt=.001;aux_timer=0;audio_timer=0;hold=0;pv=0;latched=False;enabled=False;was_audio=False
        rows=[];last_audio_off=None;turnons=[]
        for step in range(12001):
            t=step*dt;request,v12,vin,fault=event(t)
            aux_timer=aux_timer+dt if request and v12>=aux_threshold else 0
            auxgood=aux_timer>=.020
            hold=hold_time if auxgood else max(0,hold-dt)
            new_enable=auxgood or hold>0
            if not new_enable:latched=False
            if fault and new_enable:latched=True
            conducting=new_enable and not latched and vin>=40.08 and vin<50.64
            if conducting:pv=min(vin,pv+48/ramp_time*dt)
            else:pv=min(vin,pv*math.exp(-dt/(val('R410')*(val('C205')+val('C206')))))
            ready=conducting and pv>=pv_threshold and pv>=vin-.2
            audio_timer=audio_timer+dt if auxgood and ready else 0
            audio=audio_timer>=audio_delay
            assert not audio or (auxgood and ready)
            if was_audio and not audio:last_audio_off=t
            if audio and not was_audio:turnons.append(t)
            if enabled and not new_enable and name=='normal':
                assert last_audio_off is not None and t-last_audio_off>=hold_time-.002
            was_audio=audio;enabled=new_enable
            if step%10==0:rows.append([round(t,3),int(request),v12,vin,int(auxgood),int(enabled),round(pv,4),int(audio),int(latched)])
        if name in ['missing_48v','missing_12v','trigger_bounce']:assert not turnons
        elif name=='normal':assert len(turnons)==1 and turnons[0]>1+audio_delay
        elif name.startswith('psu_'):assert len(turnons)==1 and turnons[0]>=3+ramp_time+audio_delay-.01,(name,turnons)
        else:assert len(turnons)==2,(name,turnons)
        if name=='efuse_latch':assert turnons[1]>8+audio_delay
        write_csv(SIM/('sequence-'+name+'.csv'),['time_s','request','aux_v','input_v','aux_good','power_enable','pvdd_v','audio_run','efuse_latched'],rows)
    return len(cases)


if __name__=='__main__':main()
