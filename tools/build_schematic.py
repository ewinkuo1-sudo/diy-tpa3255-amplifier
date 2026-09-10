"""Generate the reviewable V0.2 four-sheet KiCad schematic.

Project-owned symbols use pin numbers checked against TI PDFs. KiCad exports and
the netlist audit are required after generation. No PCB or footprints are assigned.
"""
import csv
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'electrical'
PROJECT = 'tpa3255-v02'


def uid(key):
    return str(uuid5(NAMESPACE_URL, 'diy-tpa3255/v02/' + key))


def q(s):
    return json.dumps(str(s), ensure_ascii=False)


def effects(size=1.27, justify=''):
    return f'(effects (font (size {size} {size})) {justify})'


def prop(name, value, x, y, hide=False):
    return f'(property {q(name)} {q(value)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) {"hide" if hide else ""}))'


def line(x1,y1,x2,y2):
    return f'(polyline (pts (xy {x1} {y1})(xy {x2} {y2})) (stroke (width 0.254)(type default))(fill(type none)))'


LIB = {}
PINS = {}


def symbol(name, pins, graphics, reference='U', unit=1):
    # pins: number, name, type, x, y, angle. Library y is upward.
    PINS.setdefault(name,{})[unit] = pins
    body=''.join(f'(pin {typ} line (at {x} {y} {angle})(length 2.54)(name {q(pname)} {effects(1.0)})(number {q(n)} {effects(1.0)}))'
                 for n,pname,typ,x,y,angle in pins)
    if name not in LIB:
        LIB[name] = f'(symbol {q(name)} (pin_names(offset 0.508)) (in_bom yes)(on_board yes)' + prop('Reference',reference,0,5)+prop('Value',name,0,-5)
    LIB[name] += f'(symbol {q(name+"_"+str(unit)+"_1")} {graphics} {body})'


def primitive(name):
    if name=='R':
        g='(rectangle(start -2.54 1.016)(end 2.54 -1.016)(stroke(width 0.254)(type default))(fill(type none)))'
    elif name=='C':
        g=line(-0.762,-2.032,-0.762,2.032)+line(0.762,-2.032,0.762,2.032)+line(-2.54,0,-0.762,0)+line(0.762,0,2.54,0)
    elif name=='L':
        g=''.join(f'(arc(start {x} 0)(mid {x+0.635} 0.9)(end {x+1.27} 0)(stroke(width 0.254)(type default))(fill(type none)))' for x in [-2.54,-1.27,0,1.27])
    else:
        g='(rectangle(start -2.54 1.016)(end 2.54 -1.016)(stroke(width 0.254)(type default))(fill(type none)))'+line(-2.54,0,2.54,0)
    symbol(name,[('1','~','passive',-5.08,0,0),('2','~','passive',5.08,0,180)],g,name)


for name in ['R','C','L','Fuse']: primitive(name)
for count in [2,3,4]:
    pins=[(str(i+1),str(i+1),'passive',-5.08,-i*5.08,0) for i in range(count)]
    g=f'(rectangle(start -2.54 2.54)(end 2.54 {-count*5.08+2.54})(stroke(width 0.254)(type default))(fill(type background)))'
    symbol('Conn'+str(count),pins,g,'J')
symbol('Flag',[('1','~','power_out',0,0,90)],line(0,0,0,2.54)+line(0,2.54,1.27,1.27),'#FLG')

# TPA3255: physical pin sequence from SLASEA8A Fig. pinout, pp.3-4.
names=['GVDD_AB','VDD','M1','M2','INPUT_A','INPUT_B','OC_ADJ','FREQ_ADJ',
       'OSC_IOM','OSC_IOP','DVDD','GND','GND','AVDD','C_START','INPUT_C',
       'INPUT_D','RESET_N','FAULT_N','VBG','CLIP_OTW_N','GVDD_CD',
       'BST_D','BST_C','GND','GND','OUT_D','OUT_D','PVDD_CD','PVDD_CD','PVDD_CD',
       'OUT_C','GND','GND','OUT_B','PVDD_AB','PVDD_AB','PVDD_AB','OUT_A','OUT_A','GND','GND','BST_B','BST_A']
types={name:'passive' for name in names}
for name in ['GVDD_AB','GVDD_CD','VDD','PVDD_AB','PVDD_CD','GND']: types[name]='power_in'
for name in ['DVDD','AVDD','VBG']: types[name]='power_out'
for name in ['M1','M2','INPUT_A','INPUT_B','INPUT_C','INPUT_D','RESET_N']: types[name]='input'
for name in ['FAULT_N','CLIP_OTW_N']: types[name]='open_collector'
types['C_START']='output'
types['OSC_IOP']='output'
types['OSC_IOM']='bidirectional'
for name in ['OUT_A','OUT_B','OUT_C','OUT_D']: types[name]='output'
# One output pin per half-bridge is output type; duplicated package pads are
# passive. Netlist audit also checks both duplicated pairs and bootstrap nodes.
pins=[]
for n,name in enumerate(names,1):
    if n<=22: x,y,angle=-27.94,53.34-(n-1)*5.08,0
    else: x,y,angle=27.94,53.34-(44-n)*5.08,180
    pins.append((str(n),name,'passive' if n in (27,39) else types[name],x,y,angle))
symbol('TPA3255',pins,'(rectangle(start -25.4 55.88)(end 25.4 -55.88)(stroke(width 0.254)(type default))(fill(type background)))')
triangle='(polyline(pts(xy -5.08 5.08)(xy 5.08 0)(xy -5.08 -5.08)(xy -5.08 5.08))(stroke(width 0.254)(type default))(fill(type background)))'
for unit,ns in [(1,('3','2','1')),(2,('5','6','7'))]:
    symbol('NE5532',[(ns[0],'+','input',-7.62,2.54,0),(ns[1],'-','input',-7.62,-2.54,0),(ns[2],'OUT','output',7.62,0,180)],triangle,unit=unit)
symbol('NE5532',[('8','V+','power_in',0,7.62,270),('4','V-','power_in',0,-7.62,90)],'',unit=3)
symbol('TLV76033',[('2','IN','power_in',-10.16,0,0),('1','OUT','power_out',10.16,0,180),('3','GND','power_in',0,-7.62,90)],
       '(rectangle(start -7.62 5.08)(end 7.62 -5.08)(stroke(width 0.254)(type default))(fill(type background)))')
LIB={k:v+')' for k,v in LIB.items()}


class Sheet:
    def __init__(self,name,page):
        self.name,self.page=name,page
        self.uuid=uid(name)
        self.path='/'+uid(PROJECT)+(('/'+uid('sheet/'+name)) if name!=PROJECT else '')
        self.items=[]
        self.used=set()
        self.seq=0
        self.manifest=[]
        self.endpoints={}
        self.skip_nets=set()

    def uuid_item(self):
        self.seq+=1
        return uid(self.name+'/'+str(self.seq))

    def text(self,x,y,s,size=1.5):
        self.items.append(f'(text {q(s)} (at {x} {y} 0) {effects(size,"(justify left)")}(uuid {self.uuid_item()}))')

    def wire(self,x1,y1,x2,y2):
        self.items.append(f'(wire(pts(xy {x1} {y1})(xy {x2} {y2}))(stroke(width 0)(type default))(uuid {self.uuid_item()}))')

    def label(self,x,y,net,right=True):
        self.items.append(f'(global_label {q(net)} (shape passive)(at {x} {y} {0 if right else 180}) {effects(1.0,"(justify left)" if right else "(justify right)")} (uuid {self.uuid_item()}))')

    def part(self,kind,ref,value,x,y,nets,unit=1,vertical=False):
        x,y=round(round(x/1.27)*1.27,4),round(round(y/1.27)*1.27,4)
        self.used.add(kind)
        flag=kind=='Flag'
        inst=uid(self.name+'/'+ref+'/'+str(unit))
        orientation=90 if vertical else 0
        properties=prop('Reference',ref,x,y-4,flag)+prop('Value',value,x,y-1.8,flag)
        # Place large IC names above the body instead of over pins.
        if kind=='TPA3255': properties=prop('Reference',ref,x,y-62)+prop('Value',value,x,y-59)
        if kind=='NE5532': properties=prop('Reference',ref+('' if unit==3 else ('A' if unit==1 else 'B')),x,y-9)+prop('Value',value,x,y-6.8)
        # Actual Reference must not include unit suffix; KiCad displays it.
        if kind=='NE5532': properties=prop('Reference',ref,x,y-9)+prop('Value',value,x,y-6.8)
        properties+=prop('Footprint','',x,y,True)+prop('Datasheet',{'TPA3255':'https://www.ti.com/lit/ds/symlink/tpa3255.pdf','NE5532':'https://www.ti.com/lit/ds/symlink/ne5532.pdf','TLV76033':'https://www.ti.com/lit/ds/symlink/tlv760.pdf'}.get(kind,''),x,y,True)
        self.items.append(f'(symbol(lib_id {q("Project:"+kind)})(at {x} {y} {orientation})(unit {unit})(in_bom {"no" if flag else "yes"})(on_board {"no" if flag else "yes"})(dnp no)(uuid {inst}) {properties} (instances(project {q(PROJECT)}(path {q(self.path)}(reference {q(ref)})(unit {unit})))))')
        for num,pname,typ,px,py,angle in PINS[kind][unit]:
            if vertical:
                px,py=-py,px
                angle=(angle+90)%360
            xx,yy=round(x+px,4),round(y-py,4)
            net=nets.get(num)
            self.endpoints[(ref,num)]=(xx,yy)
            if net is None:
                self.items.append(f'(no_connect(at {xx} {yy})(uuid {self.uuid_item()}))')
            elif net not in self.skip_nets:
                dx,dy={0:(-5.08,0),180:(5.08,0),90:(0,5.08),270:(0,-5.08)}[angle]
                self.wire(xx,yy,round(xx+dx,4),round(yy+dy,4))
                self.label(round(xx+dx,4),round(yy+dy,4),net,angle!=0)
            if not flag:
                self.manifest.append((ref,num,pname,net or 'NC',self.name))

    def two(self,kind,ref,value,x,y,n1,n2,vertical=False):
        self.part(kind,ref,value,x,y,{'1':n1,'2':n2},vertical=vertical)

    def child(self,name,x,y):
        self.items.append(f'(sheet(at {x} {y})(size 60 20)(stroke(width 0.254)(type default))(fill(color 0 0 0 0))(uuid {uid("sheet/"+name)})'
                          +prop('Sheetname',name,x+30,y-2)+prop('Sheetfile',name+'.kicad_sch',x+30,y+22)
                          +f'(instances(project {q(PROJECT)}(path {q("/"+uid(PROJECT))}(page {q("2" if name=="input" else "3")})))))')

    def save(self):
        lib=''.join(LIB[k].replace('(symbol '+q(k), '(symbol '+q('Project:'+k),1) for k in sorted(self.used))
        content=f'(kicad_sch(version 20250114)(generator "diy_tpa3255")(uuid {self.uuid})(paper "A3")(title_block(title {q("TPA3255 V0.2 / "+self.name)})(date "2026-09-10")(rev "0.2 REVIEW")(comment 1 "Electrical draft - no PCB / footprints / hardware validation"))(lib_symbols {lib})'
        content+=''.join(self.items)
        if self.name==PROJECT: content+='(sheet_instances(path "/"(page "1")))'
        (DEST/(self.name+'.kicad_sch')).write_text(content+')\n')


def build():
    DEST.mkdir(exist_ok=True)
    core=Sheet(PROJECT,'1')
    core.text(15,15,'POWER STAGE / STEREO BTL / BENCH PROTOTYPE',2.5)
    core.text(15,22,'Global net names connect all three sheets. Same labels are electrically connected.',1.5)
    nets={}
    for n,name in enumerate(names,1):
        nets[str(n)]= ('GND' if name in ('M1','M2','GND') else
                     'PVDD' if name.startswith('PVDD') else
                     '+12V' if name.startswith('GVDD') else
                     None if name.startswith('OSC_IO') else
                     'VDD_FILTERED' if name=='VDD' else name)
    core.part('TPA3255','U1','TPA3255DDV',90,105,nets)
    core.text(20,172,'M1=M2=0; OSC pins intentionally NC.',1.5)
    core.text(20,179,'Top PowerPAD: ground heatsink per TI pin table.',1.5)
    core.text(20,186,'BST and duplicate output pads use passive ERC types;',1.5)
    core.text(20,192,'bootstrap and output ties are checked by netlist audit.',1.5)
    for i,ch in enumerate('ABCD'):
        yy=45+i*38.1
        core.two('C','C'+str(1+i),'33n / 100V',155,yy,'BST_'+ch,'OUT_'+ch)
        core.two('L','L'+str(1+i),'10u / TBD current',218,yy,'OUT_'+ch,'SPK_'+ch)
        core.two('C','C'+str(5+i),'1u / 100V film',274,yy,'SPK_'+ch,'GND')
        core.two('C','C'+str(9+i),'1n / 100V',350,yy,'SPK_'+ch,'GND')
        core.two('C','C'+str(13+i),'10n / 100V',300,yy+17.78,'SPK_'+ch,'Z_'+ch)
        core.two('R','R'+str(1+i),'3.3 / power TBD',365,yy+17.78,'Z_'+ch,'GND')
    core.part('Conn2','J1','LEFT BTL',222,216,{'1':'SPK_A','2':'SPK_B'})
    core.part('Conn2','J2','RIGHT BTL',300,216,{'1':'SPK_C','2':'SPK_D'})
    core.text(190,236,'Speaker terminals float: never join B or D to GND.',1.5)
    core.text(190,244,'LC values are a trial baseline; 8-ohm response needs review.',1.5)
    core.child('input',20,222)
    core.child('power-control',100,222)

    inp=Sheet('input','2')
    inp.text(15,15,'RCA INPUT / SINGLE-ENDED TO DIFFERENTIAL',2.5)
    inp.text(15,23,'NE5532 on 12V, VMID approx. 6V. Signal capacitors are bipolar/film.',1.5)
    inp.skip_nets={ch+'_'+suffix for ch in ('L','R') for suffix in ['AC','INV1','INV2','NEG','POS']}
    def join(points):
        points=[(round(round(x/1.27)*1.27,4),round(round(y/1.27)*1.27,4)) for x,y in points]
        for first,last in zip(points,points[1:]):
            if first!=last: inp.wire(*first,*last)
    def junction(x,y):
        inp.items.append(f'(junction(at {x} {y})(diameter 0)(color 0 0 0 0)(uuid {inp.uuid_item()}))')
    for idx,ch in enumerate(('L','R')):
        base=100+idx*20
        y=80+idx*86.36
        u='U'+str(2+idx)
        inp.part('Conn2','J'+str(101+idx),ch+' RCA',30,y,{'1':ch+'_RCA','2':'GND'})
        inp.two('R','R'+str(base+1),'100k',65,y+19.05,ch+'_RCA','GND')
        inp.two('C','C'+str(base+1),'10u / 25V BP',70,y,ch+'_RCA',ch+'_AC')
        inp.two('R','R'+str(base+2),'24.9k / 0.1%',110,y,ch+'_AC',ch+'_INV1')
        inp.part('NE5532',u,'NE5532',175,y-2.54,{'3':'VMID','2':ch+'_INV1','1':ch+'_NEG'},unit=1)
        inp.two('R','R'+str(base+3),'10k / 0.1%',175,y-25.4,ch+'_INV1',ch+'_NEG')
        inp.two('C','C'+str(base+2),'22p / C0G',175,y-43.18,ch+'_INV1',ch+'_NEG')
        inp.two('R','R'+str(base+4),'10k / 0.1%',245,y-2.54,ch+'_NEG',ch+'_INV2')
        inp.part('NE5532',u,'NE5532',310,y-5.08,{'5':'VMID','6':ch+'_INV2','7':ch+'_POS'},unit=2)
        inp.two('R','R'+str(base+5),'10k / 0.1%',310,y-27.94,ch+'_INV2',ch+'_POS')
        inp.two('C','C'+str(base+3),'22p / C0G',310,y-45.72,ch+'_INV2',ch+'_POS')
        pt=lambda ref,pin:inp.endpoints[(ref,str(pin))]
        join([pt('C'+str(base+1),2),pt('R'+str(base+2),1)])
        for stage,rin,rf,cf,outpin,invpin,left,right in [
            (1,base+2,base+3,base+2,1,2,150,205),
            (2,base+4,base+5,base+3,7,6,285,340)]:
            left=round(round(left/1.27)*1.27,4);right=round(round(right/1.27)*1.27,4)
            a=pt('R'+str(rin),2); z=pt(u,invpin); o=pt(u,outpin)
            f1=pt('R'+str(rf),1);f2=pt('R'+str(rf),2)
            c1=pt('C'+str(cf),1);c2=pt('C'+str(cf),2)
            join([a,(left,a[1]),z])
            join([c1,(left,c1[1]),(left,f1[1]),(left,a[1])])
            join([f1,(left,f1[1])])
            join([c2,(right,c2[1]),(right,f2[1]),(right,o[1]),o])
            join([f2,(right,f2[1])])
            for xx,yy in [(left,a[1]),(left,f1[1]),(right,f2[1]),(right,o[1])]: junction(xx,yy)
            inp.label(right,o[1],ch+('_NEG' if stage==1 else '_POS'))
            if stage==1: join([(right,o[1]),pt('R'+str(base+4),1)])
    inp.skip_nets.clear()
    inp.text(15,199,'AC coupling + input RF filters (C0G shunt after 100 ohms)',1.8)
    for i,(ch,arm,dest) in enumerate([('L','NEG','A'),('L','POS','B'),('R','NEG','C'),('R','POS','D')]):
        x=48+i*96.52
        inp.two('C','C'+str(150+i),'10u / 25V BP',x,214,ch+'_'+arm,'AC_'+dest)
        inp.two('R','R'+str(150+i),'100',x,232,'AC_'+dest,'INPUT_'+dest)
        inp.two('C','C'+str(154+i),'100p / C0G',x,250,'INPUT_'+dest,'GND')

    pwr=Sheet('power-control','3')
    pwr.text(15,15,'EXTERNAL SUPPLIES / LOCAL DECOUPLING / MANUAL RESET',2.5)
    pwr.text(15,23,'Bench version: current-limited DC sources; no mains circuit or automatic power supervisor.',1.5)
    pwr.part('Conn2','J201','PVDD INPUT',30,47,{'1':'PVDD_IN','2':'GND'})
    pwr.two('Fuse','F1','TBD rating',87,47,'PVDD_IN','PVDD')
    pwr.part('Conn2','J202','12V INPUT',30,82,{'1':'+12V','2':'GND'})
    for i,net in enumerate(['PVDD','+12V','GND']):
        pwr.part('Flag','#FLG'+str(i+1),'PWR_FLAG',145,40+i*12.7,{'1':net})
    for i in range(4):
        pwr.two('C','C'+str(201+i),'1u / 100V X7R',205+(i%2)*78.74,42+(i//2)*22.86,'PVDD','GND')
    for i in range(2):
        pwr.two('C','C'+str(205+i),'470u / 80V',205+i*78.74,87.72,'PVDD','GND')
    pwr.text(180,103,'Place 2x MLCC + 1x bulk at EACH PVDD group.',1.5)
    pwr.two('R','R201','3.3',45,120,'+12V','VDD_FILTERED')
    for ref,val,x,y,net in [
        ('C207','10u / 25V',110,120,'VDD_FILTERED'),('C208','100n / 25V',182,120,'VDD_FILTERED'),
        ('C209','100n / 25V',254,120,'+12V'),('C210','100n / 25V',326,120,'+12V'),
        ('C211','1u / 16V',45,147,'DVDD'),('C212','1u / 16V',112,147,'AVDD'),('C213','1u / 16V',182,147,'VBG'),
        ('C214','47n / 25V',254,147,'C_START')]:
        pwr.two('C',ref,val,x,y,net,'GND')
    pwr.two('R','R202','22k / 1%',45,174,'OC_ADJ','GND')
    pwr.two('R','R203','30k / 1%',112,174,'FREQ_ADJ','GND')
    pwr.text(174,174,'C209 / C210 at GVDD_AB / GVDD_CD separately.',1.4)
    pwr.text(174,181,'DVDD / AVDD / VBG: internal outputs, bypass only.',1.4)
    pwr.text(15,197,'INPUT SUPPLY / VMID',1.8)
    pwr.two('R','R204','10',45,216,'+12V','+12V_AUDIO')
    pwr.part('Flag','#FLG4','PWR_FLAG',83,235,{'1':'+12V_AUDIO'})
    pwr.part('Flag','#FLG5','PWR_FLAG',130,235,{'1':'VDD_FILTERED'})
    pwr.two('C','C215','100u / 25V',45,252,'+12V_AUDIO','GND')
    pwr.two('R','R205','10k / 1%',115,214,'+12V_AUDIO','VMID')
    pwr.two('R','R206','10k / 1%',115,252,'VMID','GND')
    pwr.two('C','C216','10u / 16V',180,214,'VMID','GND')
    pwr.two('C','C217','100n / 16V',180,252,'VMID','GND')
    for i,x in enumerate([238,310]):
        pwr.part('NE5532','U'+str(2+i),'NE5532',x,230,{'8':'+12V_AUDIO','4':'GND'},unit=3)
        pwr.two('C','C'+str(218+i),'100n / 25V',x,250,'+12V_AUDIO','GND')

    # Fourth sheet avoids cramming manual control into decoupling sheet.
    ctrl=Sheet('reset','4')
    ctrl.text(15,15,'MANUAL BENCH ENABLE / STATUS',2.5)
    ctrl.text(15,24,'Default: jumper absent => RESET low. This is not an automatic brownout supervisor.',1.5)
    ctrl.part('TLV76033','U4','TLV76033DBZR',95,62,{'2':'+12V','1':'+3V3_CTRL','3':'GND'})
    ctrl.two('C','C301','1u / 25V',38,93,'+12V','GND')
    ctrl.two('C','C302','1u / 16V',147,93,'+3V3_CTRL','GND')
    ctrl.part('Conn3','JP1','1-2 RUN / 2-3 RESET',240,62,{'1':'+3V3_CTRL','2':'ENABLE_LINK','3':'GND'})
    ctrl.two('R','R301','1k / 1%',305,67.08,'ENABLE_LINK','RESET_N')
    ctrl.two('R','R302','4.7k / 1%',305,104,'RESET_N','GND')
    ctrl.part('Conn4','J301','STATUS / INPUT ONLY',95,160,{'1':'GND','2':'FAULT_N','3':'CLIP_OTW_N','4':'RESET_N'})
    ctrl.text(170,150,'Status pins have internal pullups. Use high-impedance measurement.',1.5)
    ctrl.text(170,158,'No 5V pullup; no LED connected directly to status outputs.',1.5)
    ctrl.text(25,205,'1. Keep JP1 open or 2-3 shorted. Connect only dummy loads.',2)
    ctrl.text(25,218,'2. Apply 12V and PVDD. Confirm rails and wait >= 250ms after PVDD.',2)
    ctrl.text(25,231,'3. Move JP1 to 1-2 to run. Start with small input and low PVDD.',2)
    ctrl.text(25,244,'4. Return JP1 to 2-3 before switching power off.',2)
    ctrl.text(25,262,'Do not use with speakers until automatic supply supervision and shutdown are designed.',1.6)
    # Custom fourth child entry.
    core.items.append(f'(sheet(at 20 258)(size 60 15)(stroke(width 0.254)(type default))(fill(color 0 0 0 0))(uuid {uid("sheet/reset")})'+prop('Sheetname','reset',50,256)+prop('Sheetfile','reset.kicad_sch',50,275)+f'(instances(project {q(PROJECT)}(path {q("/"+uid(PROJECT))}(page "4")))))')
    sheets=[core,inp,pwr,ctrl]
    for sheet in sheets: sheet.save()
    (DEST/'Project.kicad_sym').write_text('(kicad_symbol_lib(version 20231120)(generator "diy_tpa3255")'+''.join(LIB.values())+')\n')
    (DEST/'sym-lib-table').write_text('(sym_lib_table\n  (version 7)\n  (lib (name "Project")(type "KiCad")(uri "${KIPRJMOD}/Project.kicad_sym")(options "")(descr "Project-owned review symbols")))\n')
    (DEST/(PROJECT+'.kicad_pro')).write_text('{}\n')
    with (DEST/'expected-connections.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n'); writer.writerow(['reference','pin','function','net','sheet'])
        for sheet in sheets: writer.writerows(sheet.manifest)
    print('Generated',len(sheets),'sheets in',DEST)


if __name__=='__main__': build()
