"""Generate the reviewable V0.3 eight-sheet KiCad schematic.

Project-owned symbols use pin numbers checked against TI PDFs. KiCad exports and
the netlist audit are required after generation. No PCB or footprints are assigned.
"""
import csv
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'electrical' / 'v03'
PROJECT = 'tpa3255-v03'


def uid(key):
    return str(uuid5(NAMESPACE_URL, 'diy-tpa3255/v03/' + key))


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

# Added device pin numbers are checked against the linked manufacturer PDFs.
def box_symbol(name,left,right,reference='U'):
    height=max(len(left),len(right))*5.08
    pins=[]
    for side,rows in [(-1,left),(1,right)]:
        for i,(n,pname,typ) in enumerate(rows):
            pins.append((str(n),pname,typ,side*17.78,height/2-i*5.08,0 if side==-1 else 180))
    symbol(name,pins,f'(rectangle(start -15.24 {height/2+2.54})(end 15.24 {-height/2+2.54})(stroke(width 0.254)(type default))(fill(type background)))',reference)
    LIB[name]+=')'

box_symbol('VOS618A',[(1,'A','passive'),(2,'K','passive')],[(4,'C','open_collector'),(3,'E','passive')])
box_symbol('PowerDiode',[(1,'A','passive'),(3,'NC','no_connect')],[(2,'K_TAB','passive')],'D')
for name in ['LVC1G14','LVC1G17']:
    box_symbol(name,[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in')],[(5,'VCC','power_in'),(4,'Y','output')])
box_symbol('TPS3808',[(6,'VDD','power_in'),(5,'SENSE','input'),(3,'MR_N','input')],[(1,'RESET_N','open_collector'),(4,'CT','passive'),(2,'GND','power_in')])
box_symbol('INA2137',[(1,'NC','no_connect'),(2,'IN_A-','input'),(3,'IN_A+','input'),(4,'V-','power_in'),(5,'IN_B+','input'),(6,'IN_B-','input'),(7,'NC','no_connect')],
           [(14,'REF_A','input'),(13,'OUT_A','output'),(12,'SENSE_A','input'),(11,'V+','power_in'),(10,'SENSE_B','input'),(9,'OUT_B','output'),(8,'REF_B','input')])
box_symbol('TPS26631',[(1,'IN','power_in'),(2,'IN','power_in'),(3,'IN','power_in'),(6,'IN_SYS','power_in'),(4,'B_GATE','output'),(5,'DRV','output'),(7,'UVLO','input'),(8,'OVP','input'),(13,'SHDN','input'),(9,'GND','power_in'),(21,'PAD','power_in')],
           [(20,'OUT','power_out'),(19,'OUT','passive'),(18,'OUT','passive'),(17,'PGOOD','open_collector'),(16,'PGTH','input'),(15,'FLT_N','open_collector'),(14,'IMON','output'),(12,'MODE','input'),(11,'ILIM','passive'),(10,'dVdT','passive')])
# Logical A/K symbol. Package pin mapping must be checked when assigning footprint.
symbol('Diode',[('1','A','passive',-5.08,0,0),('2','K','passive',5.08,0,180)],
       line(-2.54,2.54,2.54,0)+line(2.54,0,-2.54,-2.54)+line(-2.54,-2.54,-2.54,2.54)+line(2.54,-2.54,2.54,2.54),'D')
LIB['Diode']+=')'


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
        if kind in ['TPS3808','LVC1G14','LVC1G17','VOS618A','TPS26631','PowerDiode','INA2137']:
            h=max(abs(p[4]) for p in PINS[kind][unit])
            properties=prop('Reference',ref,x,y-h-8)+prop('Value',value,x,y-h-5)
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

    def child(self,name,x,y,page):
        self.items.append(f'(sheet(at {x} {y})(size 60 20)(stroke(width 0.254)(type default))(fill(color 0 0 0 0))(uuid {uid("sheet/"+name)})'
                          +prop('Sheetname',name,x+30,y-2)+prop('Sheetfile',name+'.kicad_sch',x+30,y+22)
                          +f'(instances(project {q(PROJECT)}(path {q("/"+uid(PROJECT))}(page {q(str(page))})))))')

    def save(self):
        lib=''.join(LIB[k].replace('(symbol '+q(k), '(symbol '+q('Project:'+k),1) for k in sorted(self.used))
        content=f'(kicad_sch(version 20250114)(generator "diy_tpa3255")(uuid {self.uuid})(paper "A3")(title_block(title {q("TPA3255 V0.3 / "+self.name)})(date "2026-09-11")(rev "0.3 REVIEW")(comment 1 "Electrical draft - no PCB / footprints / hardware validation"))(lib_symbols {lib})'
        content+=''.join(self.items)
        if self.name==PROJECT: content+='(sheet_instances(path "/"(page "1")))'
        (DEST/(self.name+'.kicad_sch')).write_text(content+')\n')


def build():
    DEST.mkdir(parents=True,exist_ok=True)
    core=Sheet(PROJECT,'1')
    core.text(15,15,'POWER STAGE / STEREO BTL / BENCH PROTOTYPE',2.5)
    core.text(15,22,'Global net names connect all eight sheets. Same labels are electrically connected.',1.5)
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
    for i,ch in enumerate('ABCD'):
        yy=45+i*38.1
        core.two('C','C'+str(1+i),'33n / 100V',155,yy,'BST_'+ch,'OUT_'+ch)
        core.two('L','L'+str(1+i),'10u / MA5172-AE',218,yy,'OUT_'+ch,'SPK_'+ch)
        core.two('C','C'+str(5+i),'1u / 100V film',274,yy,'SPK_'+ch,'GND')
        core.two('C','C'+str(9+i),'1n / 100V',350,yy,'SPK_'+ch,'GND')
        core.two('C','C'+str(13+i),'220n / 100V film',300,yy+17.78,'SPK_'+ch,'Z_'+ch)
        core.two('R','R'+str(1+i),'1 / 1W',365,yy+17.78,'Z_'+ch,'GND')
    core.part('Conn2','J1','LEFT BTL',222,216,{'1':'SPK_A','2':'SPK_B'})
    core.part('Conn2','J2','RIGHT BTL',300,216,{'1':'SPK_C','2':'SPK_D'})
    core.text(190,236,'Speaker terminals float: never join B or D to GND.',1.5)
    core.text(190,244,'PFFB + LC: hardware loop stability still needs testing.',1.5)
    core.child('input',20,222,2)
    core.child('power-control',100,222,3)

    inp=Sheet('input','2')
    inp.text(15,15,'RCA / XLR SELECTED SIGNAL TO DIFFERENTIAL DRIVER',2.5)
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
        inp.two('C','C'+str(base+1),'10u / 25V BP',70,y,ch+'_SELECTED',ch+'_AC')
        inp.two('R','R'+str(base+2),'11.5k / 0.1%',110,y,ch+'_AC',ch+'_INV1')
        inp.part('NE5532',u,'NE5532',175,y-2.54,{'3':'VMID','2':ch+'_INV1','1':ch+'_NEG'},unit=1)
        inp.two('R','R'+str(base+3),'10k / 0.1%',175,y-25.4,ch+'_INV1',ch+'_NEG')
        inp.two('C','C'+str(base+2),'330p / C0G',175,y-43.18,ch+'_INV1',ch+'_NEG')
        inp.two('R','R'+str(base+4),'10k / 0.1%',245,y-2.54,ch+'_NEG',ch+'_INV2')
        inp.part('NE5532',u,'NE5532',310,y-5.08,{'5':'VMID','6':ch+'_INV2','7':ch+'_POS'},unit=2)
        inp.two('R','R'+str(base+5),'10k / 0.1%',310,y-27.94,ch+'_INV2',ch+'_POS')
        inp.two('C','C'+str(base+3),'330p / C0G',310,y-45.72,ch+'_INV2',ch+'_POS')
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
    inp.text(15,199,'PFFB summing resistors BEFORE AC coupling; Z10 RCA 2.5Vrms target',1.8)
    for i,(ch,arm,dest) in enumerate([('L','NEG','A'),('L','POS','B'),('R','NEG','C'),('R','POS','D')]):
        x=48+i*96.52
        inp.two('R','R'+str(150+i),'2.7k / 0.1%',x,214,ch+'_'+arm,'SUM_'+dest)
        inp.two('C','C'+str(150+i),'10u / 50V BP',x,232,'SUM_'+dest,'INPUT_'+dest)
        inp.two('C','C'+str(154+i),'100p / C0G',x,250,'INPUT_'+dest,'GND')

    pwr=Sheet('power-control','3')
    pwr.text(15,15,'12V STANDBY / LOCAL DECOUPLING',2.5)
    pwr.text(15,23,'PVDD comes from dc-switch sheet. 12V standby remains on; no mains wiring on this PCB.',1.5)
    pwr.part('Conn2','J202','INTERNAL 12V INPUT',30,82,{'1':'+12V','2':'GND'})
    for i,net in enumerate(['+12V','GND']):
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

    # V0.3 control and feedback sheets.
    return core,inp,pwr

def finish():
    core,inp,pwr=build()
    fb=Sheet('feedback','4')
    fb.text(15,15,'POST-FILTER FEEDBACK / TI SLAA788A TPA3255 STARTING VALUES',2.3)
    fb.text(15,24,'Same-arm negative feedback: SPK_A to SUM_A, etc. Summing node is BEFORE the input coupling capacitor.',1.4)
    for i,ch in enumerate('ABCD'):
        y=52+i*50.8
        fb.two('R','R'+str(501+i),'33k / 0.1%',95,y,'SUM_'+ch,'SPK_'+ch)
        fb.two('C','C'+str(501+i),'220p / 100V C0G',210,y,'SUM_'+ch,'FB_MID_'+ch)
        fb.two('C','C'+str(505+i),'220p / 100V C0G',330,y,'FB_MID_'+ch,'SPK_'+ch)
        fb.two('R','R'+str(505+i),'10k / 0.1%',270,y+22.86,'FB_MID_'+ch,'GND')
    fb.text(15,258,'PFFB, input bandwidth and LC are one loop: reduced model is NOT hardware stability proof.',1.5)
    fb.text(15,267,'Fit all four feedback branches; do not substitute R/C values without a loop review.',1.5)

    ctrl=Sheet('trigger','5')
    ctrl.text(15,15,'ISOLATED TRIGGER / AUXILIARY MONITOR / POWER-OFF HOLD',2.3)
    ctrl.text(15,23,'Design input: 9-15V DC, nominal 12V. Verify Z10 voltage, polarity and drive capability before connecting.',1.3)
    ctrl.part('Conn2','J301','TRIGGER TIP / SLEEVE',45,53,{'1':'TRIG_TIP','2':'TRIG_RETURN'})
    ctrl.two('R','R303','6.8k / 1%',100,50,'TRIG_TIP','TRIG_LED')
    ctrl.part('VOS618A','U301','VOS618A-3T',181,59,{'1':'TRIG_LED','2':'TRIG_RETURN','4':'TRIG_N','3':'GND'})
    ctrl.two('Diode','D301','1N4148',100,77,'TRIG_RETURN','TRIG_LED')
    ctrl.two('R','R304','22k / 1%',266,47,'+3V3_CTRL','TRIG_N')
    ctrl.part('LVC1G14','U302','SN74LVC1G14DBVR',345,60,{'1':None,'2':'TRIG_N','3':'GND','4':'AUTO_REQUEST','5':'+3V3_CTRL'})
    ctrl.text(15,97,'TRIG_RETURN is isolated from GND and chassis. Use an insulated jack; no trigger-powered relay coil.',1.4)
    ctrl.part('Conn3','J302','AUTO / COMMON / ON',46,131,{'1':'AUTO_REQUEST','2':'RUN_REQUEST','3':'+3V3_CTRL'})
    ctrl.text(15,162,'External SPDT centre-OFF switch.',1.3)
    ctrl.two('R','R305','100k',129,133,'RUN_REQUEST','GND')
    ctrl.part('TPS3808','U303','TPS3808G01DBVR',230,138,{'6':'+3V3_CTRL','5':'SENSE_12V','3':'RUN_REQUEST','1':'AUX_GOOD','4':None,'2':'GND'})
    ctrl.two('R','R306','267k / 0.1%',345,119,'+12V','SENSE_12V')
    ctrl.two('R','R307','10k / 0.1%',345,140,'SENSE_12V','GND')
    ctrl.two('C','C303','1n / C0G',345,161,'SENSE_12V','GND')
    ctrl.two('R','R308','10k',231,176,'+3V3_CTRL','AUX_GOOD')
    ctrl.part('LVC1G17','U304','SN74LVC1G17DBVR',63,220,{'1':None,'2':'AUX_GOOD','3':'GND','4':'AUX_BUFFER','5':'+3V3_CTRL'})
    ctrl.two('R','R309','1k',142,209,'AUX_BUFFER','HOLD_CHARGE')
    ctrl.two('Diode','D302','1N4148',221,209,'HOLD_CHARGE','HOLD_CAP')
    ctrl.two('R','R310','100k / 1%',146,246,'HOLD_CAP','GND')
    ctrl.two('C','C304','4.7u / 16V film 5%',245,246,'HOLD_CAP','GND')
    ctrl.part('LVC1G17','U305','SN74LVC1G17DBVR',345,223,{'1':None,'2':'HOLD_CAP','3':'GND','4':'EFUSE_ENABLE','5':'+3V3_CTRL'})
    ctrl.text(15,271,'AUX_GOOD falls first to mute. HOLD_CAP keeps main DC on briefly; verify timing on hardware.',1.4)

    dc=Sheet('dc-switch','6')
    dc.text(15,15,'SWITCHED 48V DC / SLEW LIMIT / POWER-GOOD / AUDIO RESET',2.2)
    dc.text(15,23,'Internal AC/DC modules share one mains inlet. Trigger-off disconnects PVDD; 12V standby remains on.',1.3)
    dc.part('Conn2','J201','INTERNAL 48V INPUT',30,48,{'1':'PVDD_IN','2':'GND'})
    dc.two('Fuse','F1','T5A / >=80VDC TBD MPN',104,45,'PVDD_IN','FUSED_48V')
    dc.part('PowerDiode','D401','STPS5H100B',192,48,{'1':'FUSED_48V','2':'DC_PROTECTED','3':None})
    dc.two('C','C401','1u / 100V X7R',293,42,'DC_PROTECTED','GND')
    dc.part('Flag','#FLG6','PWR_FLAG',359,46,{'1':'DC_PROTECTED'})
    dcnets={1:'DC_PROTECTED',2:'DC_PROTECTED',3:'DC_PROTECTED',6:'DC_PROTECTED',4:None,5:None,
            7:'EFUSE_UV',8:'EFUSE_OV',13:'EFUSE_SHDN',9:'GND',21:'GND',20:'PVDD',19:'PVDD',18:'PVDD',
            17:'AUDIO_MR',16:'EFUSE_PGTH',15:'EFUSE_FAULT_N',14:None,12:None,11:'EFUSE_ILIM',10:'EFUSE_DVDT'}
    dc.part('TPS26631','U401','TPS26631PWPR',88,108,{str(k):v for k,v in dcnets.items()})
    # MODE open selects latched overload fault. B_GATE/DRV unused: external diode protects polarity.
    for ref,val,x,y,a,z in [
        ('R401','324k / 0.1%',195,69,'DC_PROTECTED','EFUSE_UV'),('R402','10k / 0.1%',300,69,'EFUSE_UV','GND'),
        ('R403','412k / 0.1%',195,93,'DC_PROTECTED','EFUSE_OV'),('R404','10k / 0.1%',300,93,'EFUSE_OV','GND'),
        ('R405','316k / 0.1%',195,117,'PVDD','EFUSE_PGTH'),('R406','10k / 0.1%',300,117,'EFUSE_PGTH','GND'),
        ('R407','4.02k / 1%',195,141,'EFUSE_ILIM','GND'),('R408','1k',300,141,'EFUSE_ENABLE','EFUSE_SHDN'),
        ('R409','22k',365,163,'EFUSE_SHDN','GND'),('R410','22k / 0.5W',280,163,'PVDD','GND')]:
        dc.two('R',ref,val,x,y,a,z)
    dc.two('C','C402','2.2u / 10V X7R',193,164,'EFUSE_DVDT','GND')
    dc.text(15,159,'MODE open: latch fault; cycle Trigger to retry.',1.2)
    dc.text(15,166,'No external reverse-block FET. Surge testing pending.',1.2)
    dc.part('TPS3808','U306','TPS3808G01DBVR',85,221,{'6':'+3V3_CTRL','5':'SENSE_PVDD','3':'AUDIO_MR','1':'AUDIO_GOOD','4':'AUDIO_DELAY','2':'GND'})
    dc.two('R','R311','1M / 0.1%',40,182,'PVDD','SENSE_PVDD')
    dc.two('R','R312','10k / 0.1%',144,182,'SENSE_PVDD','GND')
    dc.two('C','C305','180n / 5% C0G',54,258,'AUDIO_DELAY','GND')
    dc.two('R','R313','10k',196,185,'+3V3_CTRL','AUDIO_MR')
    dc.two('Diode','D303','BAT54',302,185,'AUDIO_MR','AUX_GOOD')
    dc.two('R','R314','10k',192,211,'+3V3_CTRL','AUDIO_GOOD')
    dc.part('LVC1G17','U307','SN74LVC1G17DBVR',274,227,{'1':None,'2':'AUDIO_GOOD','3':'GND','4':'RESET_DRIVE','5':'+3V3_CTRL'})
    dc.two('R','R301','1k / 1%',371,216,'RESET_DRIVE','RESET_N')
    dc.two('R','R302','4.7k / 1%',371,243,'RESET_N','GND')
    dc.text(153,266,'PVDD >40.9V, then ~1.03s delay.',1.3)
    ctlpower=Sheet('control-supply','7')
    ctlpower.text(15,15,'STANDBY CONTROL SUPPLY / LOCAL DECOUPLING / STATUS',2.3)
    ctlpower.part('TLV76033','U4','TLV76033DBZR',90,55,{'2':'+12V','1':'+3V3_CTRL','3':'GND'})
    ctlpower.two('C','C301','1u / 25V',210,47,'+12V','GND')
    ctlpower.two('C','C302','1u / 16V',320,47,'+3V3_CTRL','GND')
    # These decouplers use global labels for clarity; place one at each U30x supply pin.
    for i in range(6):
        ctlpower.two('C','C'+str(310+i),'100n / 16V',60+(i%3)*125,110+(i//3)*45,'+3V3_CTRL','GND')
    ctlpower.text(15,85,'C310-C315: one at each U302-U307 VCC/VDD pin on PCB.',1.5)
    # Extra status connector intentionally high-impedance only.
    ctlpower.part('Conn4','J303','STATUS',65,212,{'1':'GND','2':'FAULT_N','3':'CLIP_OTW_N','4':'EFUSE_FAULT_N'})
    ctlpower.text(140,209,'High-impedance monitoring only; no external 5V pullups.',1.4)
    ctlpower.text(140,220,'TPA fault protection remains internal; no automatic fault retry loop.',1.4)
    ctlpower.text(140,231,'Trigger OFF enters standby, not AC mains isolation.',1.4)

    xlr=Sheet('xlr-input','8')
    xlr.text(15,15,'TRUE BALANCED XLR / INA2137 GAIN 0.5 / RCA SELECTION',2.3)
    xlr.text(15,23,'XLR female: 1 shield, 2 hot, 3 cold. Both signal legs are AC coupled; do not ground pin 3.',1.4)
    for idx,ch in enumerate(('L','R')):
        base=601+idx*2
        yy=53+idx*68.58
        xlr.part('Conn3','J'+str(601+idx),ch+' XLR FEMALE',42,yy,{'1':'CHASSIS','2':ch+'_XLR_HOT','3':ch+'_XLR_COLD'})
        for leg,offset in [('HOT',0),('COLD',1)]:
            y=yy+offset*25.4
            xlr.two('R','R'+str(base+offset),'47 / 0.1%',112,y,ch+'_XLR_'+leg,ch+'_LINE_'+leg)
            xlr.two('C','C'+str(base+offset),'47u / 25V BP',182,y,ch+'_LINE_'+leg,ch+'_RX_'+leg)
        xlr.two('C','C'+str(605+idx),'47u / 25V BP',357,44+idx*96.52,ch+'_RX_OUT',ch+'_XLR')
        xlr.two('R','R'+str(605+idx),'100k',357,63+idx*96.52,ch+'_XLR','GND')
        xlr.part('Conn3','J'+str(603+idx),ch+' RCA / COM / XLR',205+idx*105,177,{'1':ch+'_RCA','2':ch+'_SELECTED','3':ch+'_XLR'})
    xlr.part('INA2137','U601','INA2137UA',264,103,{
        '1':None,'2':'L_RX_COLD','3':'L_RX_HOT','4':'GND','5':'R_RX_HOT','6':'R_RX_COLD','7':None,
        '14':'L_RX_REF','13':'L_RX_OUT','12':'L_RX_OUT','11':'+12V_XLR','10':'R_RX_OUT','9':'R_RX_OUT','8':'R_RX_REF'})
    xlr.text(15,91,'C601/C602 and C603/C604: match pairs to 1% measured capacitance.',1.15)
    xlr.text(15,161,'J603/J604: fit 2-3 for XLR, 1-2 for RCA. Change both only in standby.',1.3)
    xlr.part('Conn2','J605','CHASSIS BOND',43,183,{'1':'CHASSIS','2':'CHASSIS'})
    xlr.two('R','R608','0 / SINGLE BOND',112,184,'CHASSIS','GND')
    # The precision receiver REF pins need low impedance (<10 ohm per TI).
    # Two separate voltage followers avoid loading the existing VMID divider.
    xlr.part('NE5532','U602','NE5532',85,226,{'3':'VMID','2':'L_RX_REF','1':'L_RX_REF'},unit=1)
    xlr.part('NE5532','U602','NE5532',163,226,{'5':'VMID','6':'R_RX_REF','7':'R_RX_REF'},unit=2)
    xlr.part('NE5532','U602','NE5532',233,226,{'8':'+12V_XLR','4':'GND'},unit=3)
    xlr.two('R','R607','10',301,219,'+12V','+12V_XLR')
    xlr.two('C','C609','100u / 25V',372,219,'+12V_XLR','GND')
    xlr.two('C','C607','100n / 25V',301,246,'+12V_XLR','GND')
    xlr.two('C','C608','100n / 25V',372,246,'+12V_XLR','GND')
    xlr.part('Flag','#FLG7','PWR_FLAG',233,251,{'1':'+12V_XLR'})
    xlr.text(15,254,'Buffered REF; C607 at U601, C608 at U602. Pin 1 / shells bond to chassis at entry.',1.25)
    xlr.text(15,265,'Internal balanced-to-single-ended receiver; this is not a fully differential end-to-end amplifier.',1.25)
    core.child('feedback',20,253,4)
    core.child('trigger',100,253,5)
    core.child('dc-switch',180,253,6)
    core.child('control-supply',20,190,7)
    core.child('xlr-input',100,190,8)
    sheets=[core,inp,pwr,fb,ctrl,dc,ctlpower,xlr]
    for sheet in sheets: sheet.save()
    (DEST/'Project.kicad_sym').write_text('(kicad_symbol_lib(version 20231120)(generator "diy_tpa3255")'+''.join(LIB.values())+')\n')
    (DEST/'sym-lib-table').write_text('(sym_lib_table\n  (version 7)\n  (lib (name "Project")(type "KiCad")(uri "${KIPRJMOD}/Project.kicad_sym")(options "")(descr "Project-owned review symbols")))\n')
    (DEST/(PROJECT+'.kicad_pro')).write_text('{}\n')
    with (DEST/'expected-connections.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n'); writer.writerow(['reference','pin','function','net','sheet'])
        for sheet in sheets: writer.writerows(sheet.manifest)
    print('Generated',len(sheets),'sheets in',DEST)

if __name__=='__main__': finish()
