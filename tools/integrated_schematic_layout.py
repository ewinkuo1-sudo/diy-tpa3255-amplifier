"""Re-layout native source symbols into one electrically integrated schematic.

Coordinates below use a 2.54 mm drawing grid. Main audio, PFFB and enable/reset
paths are wires; repeated supply/bias connections use ordinary same-sheet labels.
Only the overview's TPA3255/INA2137 pin positions are rearranged for signal flow.
Pin numbers, names, types, unit identities and all source component data survive.
"""
import collections
import copy
import csv
import hashlib
import json
import math
from uuid import NAMESPACE_URL, uuid5
from build_schematic_overview import (EL, NAME, OUTPUT, MANIFEST, UUID, SOURCE_NAMES,
    parse, dump, child, children, walk, q, number, annotation)

G = 2.54

def mm(v):
    return number(v * G)

def ident(key):
    return str(uuid5(NAMESPACE_URL, NAME + '/integrated/' + key))

class Drawing:
    def __init__(self):
        self.sources = {n: parse((EL/(n+'.kicad_sch')).read_text()) for n in SOURCE_NAMES}
        expected = {'tpa3255-v03'} | {json.loads(next(p[2] for p in children(s,'property') if p[1]=='"Sheetfile"'))[:-10] for s in children(self.sources['tpa3255-v03'], 'sheet')}
        assert expected == set(self.sources), 'Unmapped source sheet'
        self.lib, self.source, self.parts, self.pins = {}, {}, {}, {}
        self.items, self.lines, self.used, self.labels = [], [], set(), []
        self.nets = {(r['reference'],r['pin']):r['net'] for r in csv.DictReader((EL/'expected-connections.csv').open())}
        for n, net in [(1,'+12V'),(2,'GND'),(4,'+12V_AUDIO'),(5,'VDD_FILTERED'),(6,'DC_PROTECTED'),(7,'+12V_XLR')]:
            self.nets[('#FLG'+str(n),'1')] = net
        for t in self.sources.values():
            for s in children(child(t,'lib_symbols'),'symbol'):
                if s[1] in self.lib:
                    assert self.lib[s[1]] == s
                self.lib[s[1]] = copy.deepcopy(s)
            for s in children(t,'symbol'):
                ref = json.loads(next(p[2] for p in children(s,'property') if p[1]=='"Reference"'))
                key = (ref,int(child(s,'unit')[1]))
                assert key not in self.source
                self.source[key] = s
        self.reshape()

    def reshape(self):
        # The single TPA symbol remains one unit; pin placement follows four
        # signal lanes. No package pin is added, removed or renumbered.
        left = {5:57,6:87,16:125,17:155,1:66,2:69,7:98,8:101,
                11:104,14:107,15:110,20:113,3:116,4:119,9:134,10:137,
                18:140,19:143,21:146,22:149,12:160,13:163}
        right = {44:51,40:57,39:59,42:63,41:65,38:69,37:71,36:73,
                 43:81,35:87,34:93,33:95,32:125,31:103,30:105,29:107,
                 24:119,28:155,27:157,26:133,25:135,23:149}
        self.box('Project:TPA3255', (-28, -57, 28, 60),
                 {str(p):(-30,y-106,0) for p,y in left.items()} |
                 {str(p):(30,y-106,180) for p,y in right.items()})
        self.box('Project:INA2137', (-8,-40,8,48), {
            '1':(-10,-38,0),'2':(-10,-28,0),'3':(-10,-34,0),
            '4':(0,50,90),'5':(-10,34,0),'6':(-10,40,0),'7':(-10,44,0),
            '14':(10,-22,180),'13':(10,-34,180),'12':(10,-30,180),
            '11':(0,-42,270),'10':(10,38,180),'9':(10,34,180),'8':(10,46,180)})

    def box(self, name, bounds, pins):
        lib = self.lib[q(name)]
        unit = children(lib,'symbol')[0]
        oldpins = children(unit,'pin')
        assert set(pins) == {json.loads(child(p,'number')[1]) for p in oldpins}
        x1,y1,x2,y2=bounds
        unit[:] = [unit[0], unit[1], parse(f'(rectangle (start {mm(x1)} {mm(-y1)}) (end {mm(x2)} {mm(-y2)}) (stroke (width 0.254)(type default))(fill(type background)))')]
        for p in oldpins:
            n=json.loads(child(p,'number')[1]); x,y,a=pins[n]
            child(p,'at')[:] = ['at',mm(x),mm(-y),str(a)]
            child(p,'length')[1] = mm(2)
            unit.append(p)

    def place(self, ref, x, y, angle=0, unit=1, mirror=False):
        key=(ref,unit)
        assert key not in self.parts, key
        s=copy.deepcopy(self.source[key]); self.parts[key]=s
        child(s,'at')[:] = ['at',mm(x),mm(y),str(angle)]
        s[:] = [v for v in s if not(isinstance(v,list) and v[0]=='mirror')]
        if mirror: s.append(['mirror','y'])
        props={json.loads(p[1]):p for p in children(s,'property')}
        for p in props.values(): child(p,'at')[:] = ['at',mm(x),mm(y), '0']
        kind=json.loads(child(s,'lib_id')[1]).split(':')[1]
        # Keep readable horizontal properties even on rotated vertical passives.
        if kind in {'R','C','L','Diode','Fuse'} and angle in {90,270}:
            positions=[(x+1.6,y-0.5),(x+1.6,y+0.7)]
            justify='left'
        elif kind in {'R','C','L','Diode','Fuse'}:
            positions=[(x,y-2.0),(x,y-0.95)]; justify=''
        elif kind.startswith('Conn'):
            positions=[(x,y-4),(x,y-2.7)]; justify=''
        elif kind=='TPA3255':
            positions=[(x+15,106-54),(x+15,106-52.5)]; justify=''
        elif kind=='INA2137':
            positions=[(x,y-44),(x,y-42.8)]; justify=''
        else:
            positions=[(x,y-5.8),(x,y-4.6)]; justify=''
        if kind in {'TPS26631'}: positions=[(x,y-15),(x,y-13.7)]
        if kind in {'BAT54','PowerDiode'}: positions=[(x,y-7),(x,y-5.7)]
        for name,pos in zip(['Reference','Value'],positions):
            p=props[name]; child(p,'at')[:] = ['at',mm(pos[0]),mm(pos[1]),'0']
            # Only property styling changes; original text remains exact.
            p[4:] = []
            p[3] = ['at',mm(pos[0]),mm(pos[1]),'90' if angle in {90,270} else '0']
            p.append(parse('(effects (font (size 1.27 1.27))'+(' (justify left)' if justify else '')+')'))
        inst=child(s,'instances'); project=child(inst,'project'); path=child(project,'path')
        inst[:]=['instances',['project',q(NAME),['path',q('/'+UUID),copy.deepcopy(child(path,'reference')),copy.deepcopy(child(path,'unit'))]]]
        lib=self.lib[child(s,'lib_id')[1]]
        for sub in children(lib,'symbol'):
            u=int(json.loads(sub[1]).split('_')[-2])
            if u not in {0,unit}: continue
            for p in children(sub,'pin'):
                n=json.loads(child(p,'number')[1]); at=child(p,'at')
                px=float(at[1])/G; py=-float(at[2])/G
                direction=(int(at[3])+180)%360
                dx=math.cos(math.radians(direction)); dy=-math.sin(math.radians(direction))
                if mirror: px=-px; dx=-dx
                c=round(math.cos(math.radians(angle))); sn=round(math.sin(math.radians(angle)))
                px,py=c*px+sn*py,-sn*px+c*py
                dx,dy=c*dx+sn*dy,-sn*dx+c*dy
                self.pins[(ref,n)]=((round(x+px,6),round(y+py,6)),(round(dx),round(dy)))
        self.items.append(s)

    def pt(self, p):
        if isinstance(p[0],str):
            key=(p[0],str(p[1])); self.used.add(key); return self.pins[key][0]
        return tuple(p)

    def wire(self, net, *points):
        for p in points:
            if isinstance(p[0],str): assert self.nets[(p[0],str(p[1]))]==net, (net,p)
        pts=[self.pt(p) for p in points]
        for a,b in zip(pts,pts[1:]):
            if a==b: continue
            assert a[0]==b[0] or a[1]==b[1], ('diagonal',net,a,b)
            self.lines.append((net,a,b))

    def join(self, *pins, via=None):
        net=self.nets[(pins[0][0],str(pins[0][1]))]
        pts=[self.pt(p) for p in pins]
        for a,b in zip(pts,pts[1:]):
            self.wire(net,a, *(([(via,a[1]),(via,b[1])]) if via is not None else [(b[0],a[1])]),b)

    def label(self, net, point, right=True):
        p=self.pt(point)
        self.labels.append((net,p,right))

    def stub(self, ref, pin, length=3):
        key=(ref,str(pin)); p,(dx,dy)=self.pins[key]; net=self.nets[key]
        self.used.add(key)
        if net=='NC':
            self.items.append(parse(f'(no_connect (at {mm(p[0])} {mm(p[1])})(uuid {ident("nc/"+ref+"/"+str(pin))}))'))
            return
        b=(p[0]+dx*length,p[1]+dy*length)
        self.wire(net,p,b); self.label(net,b,dx>=0)

    def text(self, text, x, y, size=2):
        item=annotation(text,x*G,y*G,size)
        child(item,'uuid')[1]=ident('text/'+str((text,x,y)))
        self.items.append(item)

    def shunt(self, ref,x,y,top=None):
        self.place(ref,x,y,270)
        if top is not None: self.wire(self.nets[(ref,'1')],top,(x,top[1]),(ref,1))
        self.stub(ref,2,2)

    def bank(self, refs, xs, y, net):
        for ref,x in zip(refs,xs):
            self.shunt(ref,x,y,(x,y-6))
        self.wire(net,(xs[0],y-6),(xs[-1],y-6))
        self.label(net,(xs[0],y-6))

    def finish(self):
        assert set(self.parts)==set(self.source), ('Unplaced',set(self.source)-set(self.parts))
        assert set(self.pins)==set(self.nets), ('Pin coverage',set(self.pins)^set(self.nets))
        for ref,pin in self.pins:
            if (ref,pin) not in self.used: self.stub(ref,pin)
        # Name all manually drawn nets. Local labels share one sheet; unlike the
        # old global arrows they do not obscure the continuous signal wires.
        for net in {n for n,_,_ in self.lines}:
            horizontal=[(a,b) for n,a,b in self.lines if n==net and a[1]==b[1]]
            if horizontal:
                a,b=max(horizontal,key=lambda ab:abs(ab[0][0]-ab[1][0]))
                x1,x2=sorted((a[0],b[0])); self.label(net,((x1+x2)/2,a[1]))
            else:
                _,a,b=next(s for s in self.lines if s[0]==net); self.label(net,a)
        # Split at same-net branch points and junctions. Crossings of different
        # nets remain unconnected; source/exported netlist comparison is decisive.
        vertices=collections.defaultdict(set)
        for n,a,b in self.lines: vertices[n].update((a,b))
        for (ref,pin),(p,_) in self.pins.items():
            if self.nets[(ref,pin)]!='NC': vertices[self.nets[(ref,pin)]].add(p)
        for n,p,_ in self.labels: vertices[n].add(p)
        for n,a,b in self.lines:
            for m,c,e in self.lines:
                if n!=m or a[0]!=b[0] or c[1]!=e[1]: continue
                p=(a[0],c[1])
                if min(a[1],b[1])<=p[1]<=max(a[1],b[1]) and min(c[0],e[0])<=p[0]<=max(c[0],e[0]): vertices[n].add(p)
        segments=set()
        for n,a,b in self.lines:
            pts=sorted(p for p in vertices[n] if min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1]))
            segments.update((n,p1,p2) for p1,p2 in zip(pts,pts[1:]) if p1!=p2)
        degrees=collections.Counter()
        for n,a,b in sorted(segments):
            self.items.append(parse(f'(wire (pts (xy {mm(a[0])} {mm(a[1])})(xy {mm(b[0])} {mm(b[1])}))(stroke(width 0)(type default))(uuid {ident(str((n,a,b)))}))'))
            degrees[n,a]+=1; degrees[n,b]+=1
        for (n,p),deg in degrees.items():
            if deg>=3:
                self.items.append(parse(f'(junction (at {mm(p[0])} {mm(p[1])})(diameter 0)(color 0 0 0 0)(uuid {ident("j/"+str((n,p)))}))'))
        for net,p,right in sorted(set(self.labels)):
            self.items.append(parse(f'(label {q(net)} (at {mm(p[0])} {mm(p[1])} {0 if right else 180})(effects(font(size 1.0 1.0))(justify left bottom))(uuid {ident("label/"+str((net,p,right)))}))'))
        # Avoid ambiguous touching endpoints even where KiCad currently treats
        # a crossing without a junction as separate. Interior crossings are OK.
        def on(point, a, b):
            return (min(a[0],b[0]) <= point[0] <= max(a[0],b[0]) and
                    min(a[1],b[1]) <= point[1] <= max(a[1],b[1]) and
                    (a[0] == b[0] == point[0] or a[1] == b[1] == point[1]))
        ordered = sorted(segments)
        for i, (net,a,b) in enumerate(ordered):
            for other,c,e in ordered[i+1:]:
                if net != other:
                    assert not any(on(p,c,e) for p in (a,b)), (net,other,a,b,c,e)
                    assert not any(on(p,a,b) for p in (c,e)), (net,other,a,b,c,e)
            for key,(point,_) in self.pins.items():
                assert self.nets[key] == net or not on(point,a,b), (net,key,point)


def audio(d):
    d.place('U601',65,91); d.place('U1',290,106)
    for k,(side,dy) in enumerate([('L',0),('R',68)]):
        base=601+2*k; J=601+k; outcap=605+k; select=603+k; op='U'+str(2+k); b=100+20*k
        row=57+dy
        d.place('J'+str(J),12,55+dy,mirror=True)
        for j in range(2):
            r='R'+str(base+j); c='C'+str(base+j); y=row+6*j
            d.place(r,28,y); d.place(c,44,y)
            pin=2+j; rxpin=([3,2] if k==0 else [5,6])[j]
            d.wire(side+'_XLR_'+('HOT' if j==0 else 'COLD'),('J'+str(J),pin),(19,55+dy+pin*2-2),(19,y),(r,1))
            d.join((r,2),(c,1)); d.join((c,2),('U601',rxpin))
        sense,out,refpin=([12,13,14] if k==0 else [10,9,8])
        d.wire(side+'_RX_OUT',('U601',sense),(79,row+4),(79,row),('U601',out))
        d.place('C'+str(outcap),85,row); d.join(('U601',out),('C'+str(outcap),1))
        d.shunt('R'+str(outcap),93,row+6,(93,row))
        d.place('J'+str(select),103,row-2)
        d.wire(side+'_XLR',('C'+str(outcap),2),(97,row),(97,row+2),('J'+str(select),3))
        d.wire(side+'_XLR',(93,row),(97,row))
        d.place('J'+str(101+k),88,row-12,mirror=True)
        d.shunt('R'+str(b+1),96,row-6,(96,row-12))
        d.wire(side+'_RCA',('J'+str(101+k),1),(96,row-12),(99,row-12),(99,row-2),('J'+str(select),1))
        d.place('C'+str(b+1),113,row); d.place('R'+str(b+2),130,row)
        d.wire(side+'_SELECTED',('J'+str(select),2),(98,row),(98,row+5),(107,row+5),(107,row),('C'+str(b+1),1))
        d.join(('C'+str(b+1),2),('R'+str(b+2),1))
        for unit,x,y,ri,ci,ip,opn in [(1,140,row-1,b+3,b+2,2,1),(2,182,row-2,b+5,b+3,6,7)]:
            d.place(op,x,y,unit=unit)
            d.place('R'+str(ri),x,y-13); d.place('C'+str(ci),x,y-19)
            inv=side+'_INV'+str(unit); negpos=side+('_NEG' if unit==1 else '_POS')
            d.wire(inv,(op,ip),(x-7,y+1),(x-7,y-19),('C'+str(ci),1))
            d.wire(inv,(x-7,y-13),('R'+str(ri),1))
            d.wire(negpos,(op,opn),(x+8,y),(x+8,y-19),('C'+str(ci),2))
            d.wire(negpos,(x+8,y-13),('R'+str(ri),2))
        d.join(('R'+str(b+2),2),(op,2))
        d.place('R'+str(b+4),165,row-1)
        d.join((op,1),('R'+str(b+4),1)); d.join(('R'+str(b+4),2),(op,6))
        # REF buffers sit beside the receiver and are wired back to its REF pin.
        d.place('U602',92,row+23,unit=k+1)
        plus,minus,output=([3,2,1] if k==0 else [5,6,7])
        d.wire(side+'_RX_REF',('U602',output),(102,row+23),(102,row+29),(86,row+29),(86,row+24),('U602',minus))
        d.wire(side+'_RX_REF',(102,row+23),(106,row+23),(106,row+12),('U601',refpin))
        d.text(('左' if k==0 else '右')+'聲道：XLR / RCA → 差動驅動',10,row-27,2.4)
        d.text('跳線 1–2：RCA；2–3：XLR',88,row+36,1.8)
    for i,row in enumerate([57,87,125,155]):
        letter='ABCD'[i]; op='U'+str(2+i//2); side='L' if i<2 else 'R'
        d.place('R'+str(150+i),202,row); d.place('C'+str(150+i),230,row)
        d.shunt('C'+str(154+i),244,row+7,(244,row))
        if i%2==0:
            d.wire(side+'_NEG',(op,1),(153,row-1),(153,row+17),(194,row+17),(194,row),('R'+str(150+i),1))
        else:
            d.wire(side+'_POS',(op,7),(190,row-32),(190,row),('R'+str(150+i),1))
        sx=214 if i%2==0 else 218
        d.join(('R'+str(150+i),2),('C'+str(150+i),1))
        d.join(('C'+str(150+i),2),('U1',[5,6,16,17][i]))
        # Bootstrap, filter and speaker branches now share actual wires.
        d.place('C'+str(1+i),327,row-6); d.place('L'+str(1+i),342,row)
        out='OUT_'+letter; spk='SPK_'+letter
        d.join(('U1',[44,43,24,23][i]),('C'+str(1+i),1))
        d.wire(out,('C'+str(1+i),2),(332,row-6),(332,row),('L'+str(1+i),1))
        d.join(('U1',[40,35,32,28][i]),('L'+str(1+i),1))
        if i in [0,3]: d.wire(out,('U1',39 if i==0 else 27),(332,row+2),(332,row))
        d.shunt('C'+str(5+i),355,row+7,(355,row)); d.shunt('C'+str(9+i),380,row+7,(380,row))
        d.place('C'+str(13+i),402,row+6,270); d.shunt('R'+str(1+i),402,row+16)
        d.join(('C'+str(13+i),2),('R'+str(1+i),1))
        d.wire(spk,('L'+str(1+i),2),(435 if i%2==0 else 437,row))
        d.wire(spk,(402,row),('C'+str(13+i),1))
        # Complete PFFB loops run around the IC, with the four networks on
        # those wires instead of in a separate feedback page/panel.
        fy=[11,31,177,197][i]; fx=410 if i%2==0 else 414
        d.place('R'+str(501+i),290,fy)
        d.place('C'+str(501+i),278,fy+6); d.place('C'+str(505+i),304,fy+6)
        d.shunt('R'+str(505+i),291,fy+13,(291,fy+6))
        d.wire('SUM_'+letter,(sx,row),(sx,fy),('R'+str(501+i),1))
        d.wire('SUM_'+letter,(268,fy),(268,fy+6),('C'+str(501+i),1))
        d.join(('C'+str(501+i),2),('C'+str(505+i),1))
        d.wire(spk,(fx,row),(fx,fy),('R'+str(501+i),2))
        d.wire(spk,(312,fy),(312,fy+6),('C'+str(505+i),2))
    for k,base in enumerate([57,125]):
        ref='J'+str(k+1); d.place(ref,444,base+14)
        d.wire('SPK_'+'AC'[k],(435,base),(435,base+14),(ref,1))
        d.wire('SPK_'+'BD'[k],(437,base+30),(437,base+16),(ref,2))
        d.text(('左' if k==0 else '右')+'喇叭',438,base+23,2.4)
    d.text('濾波後回授 PFFB：由喇叭端返回 SUM_A / SUM_B',245,6,2)
    d.text('濾波後回授 PFFB：由喇叭端返回 SUM_C / SUM_D',260,173,2)
    d.text('LC 輸出濾波',346,48,2.4)
    d.text('BTL 浮接輸出：喇叭兩端均不接 GND',335,166,2)


def supplies(d):
    d.place('J202',12,184,mirror=True); d.place('R204',35,184)
    d.wire('+12V',('J202',1),('R204',1)); d.place('#FLG1',25,184)
    d.place('#FLG2',20,191); d.label('GND',('#FLG2',1))
    d.wire('GND',('J202',2),(20,186),('#FLG2',1))
    d.shunt('C215',45,192,(45,184)); d.place('R205',65,190,270); d.shunt('R206',65,202)
    d.wire('+12V_AUDIO',('R204',2),(171,184))
    d.wire('+12V_AUDIO',(65,184),('R205',1))
    d.join(('R205',2),('R206',1)); d.label('VMID',(65,196))
    for ref,x in [('C216',80),('C217',96)]: d.shunt(ref,x,202,(x,196))
    d.wire('VMID',(65,196),(96,196))
    for ref,x,c in [('U2',135,'C218'),('U3',160,'C219')]:
        d.place(ref,x,195,unit=3)
        d.wire('+12V_AUDIO',(x,184),(ref,8)); d.stub(ref,4,2)
        d.shunt(c,x+11,195,(x+11,184))
    d.place('#FLG4',52,184)
    d.place('R607',35,214); d.wire('+12V',(25,184),(25,214),('R607',1))
    for ref,x in [('C609',45),('C607',68),('C608',90)]: d.shunt(ref,x,221,(x,214))
    d.wire('+12V_XLR',('R607',2),(113,214)); d.place('U602',113,221,unit=3)
    d.wire('+12V_XLR',(113,214),('U602',8)); d.place('#FLG7',52,214)
    d.place('J605',12,211,mirror=True); d.place('R608',19,211)
    d.wire('CHASSIS',('J605',1),(17,211),('R608',1))
    d.wire('CHASSIS',('J605',2),(17,213),(17,211))
    d.stub('R608',2,2)
    d.place('R201',201,204)
    for ref,x in [('C207',217),('C208',235)]: d.shunt(ref,x,211,(x,204))
    d.wire('VDD_FILTERED',('R201',2),(235,204)); d.place('#FLG5',209,204)
    for ref,x in [('C209',201),('C210',223)]: d.shunt(ref,x,224)
    for ref,x in zip(['C211','C212','C213','C214','R202','R203'],[266,287,308,329,350,371]): d.shunt(ref,x,219)
    # The power-stage capacitor bank connects to the same PVDD trunk as U1 and
    # the eFuse, midway between the left and right output networks.
    for ref,x in zip(['C201','C202','C203','C204','C205','C206'],[344,361,378,395,417,439]): d.shunt(ref,x,110,(x,99))
    d.wire('PVDD',(334,99),(456,99),(456,267))
    for pin,y in [(38,69),(37,71),(36,73),(31,103),(30,105),(29,107)]:
        d.wire('PVDD',('U1',pin),(334,y),(334,99))
    d.place('U4',30,235); d.shunt('C301',16,243,(16,235)); d.shunt('C302',46,243,(46,235))
    d.wire('+12V',(25,214),(10,214),(10,235),(16,235),('U4',2))
    d.wire('+3V3_CTRL',('U4',1),(46,235)); d.stub('U4',3,2)
    d.text('12V 待機供電 → 類比驅動、XLR 與 3.3V 控制',10,175,2.5)
    d.text('類比中點 VMID',65,179,2)
    d.text('TPA3255 偏壓、設定與本地去耦（同名標籤相連）',260,212,2)


def control(d):
    d.place('J301',12,253,mirror=True); d.place('R303',28,253); d.place('U301',50,255)
    d.join(('J301',1),('R303',1)); d.join(('R303',2),('U301',1))
    d.place('D301',32,263,180)
    d.wire('TRIG_RETURN',('J301',2),(19,255),(19,267),(36,267),(36,263),('D301',1))
    d.wire('TRIG_RETURN',(19,255),('U301',2))
    d.wire('TRIG_LED',('D301',2),(30,253))
    d.place('R304',64,247,270); d.place('U302',80,254)
    d.join(('U301',4),('U302',2)); d.wire('TRIG_N',('R304',2),(64,253))
    d.place('J302',104,253); d.join(('U302',4),('J302',1))
    d.shunt('R305',114,273,(114,267))
    d.place('U303',153,255); d.place('R306',130,240,270); d.shunt('R307',130,252); d.shunt('C303',138,252,(138,246))
    d.join(('R306',2),('R307',1))
    d.wire('SENSE_12V',(130,246),(142,246),(142,254),('U303',5))
    d.wire('RUN_REQUEST',('J302',2),(96,255),(96,267),(142,267),(142,256),('U303',3))
    d.place('R308',166,245,270); d.place('U304',183,253)
    d.join(('U303',1),('U304',2)); d.wire('AUX_GOOD',('R308',2),(166,252))
    d.place('R309',203,252); d.place('D302',216,252)
    d.join(('U304',4),('R309',1)); d.join(('R309',2),('D302',1))
    d.shunt('R310',229,259,(229,252)); d.shunt('C304',244,259,(244,252)); d.place('U305',264,253)
    d.join(('D302',2),('U305',2))
    d.place('R408',284,252); d.join(('U305',4),('R408',1))
    d.place('U401',318,278); d.shunt('R409',299,291,(299,283))
    d.wire('EFUSE_SHDN',('R408',2),(294,252),(294,283),('U401',13))
    # 48 V series supply path, including real fuse and reverse-polarity diode.
    d.place('J201',238,276,mirror=True); d.place('F1',254,276); d.place('D401',276,278)
    d.join(('J201',1),('F1',1)); d.join(('F1',2),('D401',1))
    d.shunt('C401',291,285,(291,276)); d.place('#FLG6',289,276)
    d.wire('DC_PROTECTED',('D401',2),(306,276),(306,267),('U401',1))
    for pin,y in [(2,269),(3,271),(6,273)]: d.wire('DC_PROTECTED',('U401',pin),(306,y))
    d.wire('PVDD',('U401',20),(456,267))
    for pin,y in [(19,269),(18,271)]: d.wire('PVDD',('U401',pin),(331,y),(331,267))
    d.shunt('R410',444,274,(444,267))
    # Local protection thresholds and timing components.
    for top,bottom,x,y,net,pin,rail in [('R401','R402',266,303,'EFUSE_UV',7,'DC_PROTECTED'),('R403','R404',287,303,'EFUSE_OV',8,'DC_PROTECTED'),('R405','R406',342,282,'EFUSE_PGTH',16,'PVDD')]:
        d.place(top,x,y-6,270); d.shunt(bottom,x,y+6)
        d.join((top,2),(bottom,1)); d.label(net,(x,y))
        if pin==16: d.wire(net,('U401',pin),(335,275),(335,y),(x,y))
    d.shunt('R407',342,300); d.shunt('C402',361,300)
    d.wire('EFUSE_ILIM',('U401',11),(336,283),(336,296),(342,296),('R407',1))
    d.wire('EFUSE_DVDT',('U401',10),(333,285),(333,294),(361,294),('C402',1))
    # Immediate mute and delayed power-off share the same AUX_GOOD decision.
    d.place('D303',364,288); d.place('R313',351,280,270)
    d.wire('AUX_GOOD',(166,252),(170,252),(170,234),(372,234),(372,286),('D303',3))
    d.wire('AUDIO_MR',('U401',17),(355,273),(355,286),('D303',1))
    d.wire('AUDIO_MR',('R313',2),(351,286),(355,286))
    d.place('U306',392,294); d.place('R311',405,267,270); d.shunt('R312',405,277)
    d.join(('R311',2),('R312',1))
    d.wire('SENSE_PVDD',(405,271),(378,271),(378,293),('U306',5))
    d.wire('AUDIO_MR',(355,286),(355,296),(380,296),(380,295),('U306',3))
    d.shunt('C305',407,302)
    d.wire('AUDIO_DELAY',('U306',4),(404,293),(404,300),('C305',1))
    d.place('R314',409,284,270); d.place('U307',425,292)
    d.join(('U306',1),('U307',2)); d.wire('AUDIO_GOOD',('R314',2),(409,291))
    d.place('R301',441,291); d.join(('U307',4),('R301',1))
    d.shunt('R302',448,298,(448,291))
    d.wire('RESET_N',('R301',2),(459,291),(459,230),(254,230),(254,140),('U1',18))
    for ref,x,y in [('C310',80,270),('C311',153,273),('C312',183,273),('C313',264,270),('C314',392,310),('C315',425,310)]: d.shunt(ref,x,y)
    d.place('J303',209,301)
    d.text('Trigger → 光耦隔離 → AUTO / OFF / ON → 電源條件判斷 → 關機保持 → 48V 開關',10,289,2.4)
    d.text('12V 供電成立',139,239,1.8); d.text('延後切斷 48V',210,242,1.8)
    d.text('48V 機內電源 → 保險絲 → 反接保護 → eFuse → 功率級 PVDD',238,318,2)
    d.text('48V 成立與延遲開聲 → RESET_N',380,257,2)
    d.text('前級 Trigger 回路隔離；TRIG_RETURN 不接 GND',10,281,1.8)
    d.text('AUTO / 中間 OFF / ON',90,280,1.8)


def build_integrated():
    d=Drawing(); audio(d); supplies(d); control(d)
    d.text('TPA3255 V0.3｜整合電路圖',10,9,5)
    d.text('音訊由左向右；四路回授繞回輸入；下方為供電與啟停控制。',10,16,2.2)
    d.text('所有 180 個元件皆保留。相同電源／偏壓標籤表示相連；導線交叉僅有圓點才相接。',10,307,2)
    d.text('低壓音訊與控制草案；機內市電區另圖。尚未走線及實機驗證。',10,314,2)
    d.finish()
    drawing=parse(f'(kicad_sch (version 20250114)(generator "diy_tpa3255_integrated")(uuid {UUID})(paper "A0")(title_block (title "TPA3255 V0.3 / INTEGRATED CIRCUIT") (date "2026-09-11")(rev "0.3 REVIEW")(comment 1 "Re-laid-out native circuit; source netlist equivalence checked")))')
    # Separate presentation library keeps ERC library checks enabled while the
    # maintained source keeps its original physical-pin-order symbols.
    overview_lib=[]
    for old in ['Project:TPA3255','Project:INA2137']:
        lib=d.lib.pop(q(old)); lib[1]=q(old.replace('Project:','Overview:'))
        d.lib[lib[1]]=lib
        external=copy.deepcopy(lib); external[1]=q(old.split(':')[1]); overview_lib.append(external)
        for s in d.parts.values():
            if child(s,'lib_id')[1]==q(old): child(s,'lib_id')[1]=lib[1]
    (EL/'Overview.kicad_sym').write_text('(kicad_symbol_lib (version 20231120)(generator "diy_tpa3255_overview")\n'+'\n'.join(dump(s) for s in overview_lib)+'\n)\n')
    table=parse((EL/'sym-lib-table').read_text())
    if not any(child(v,'name')[1]=='"Overview"' for v in children(table,'lib')):
        table.append(parse('(lib(name "Overview")(type "KiCad")(uri "${KIPRJMOD}/Overview.kicad_sym")(options "")(descr "Integrated overview pin placement; identical electrical pins"))'))
        (EL/'sym-lib-table').write_text('(sym_lib_table\n  '+'\n  '.join(dump(v) for v in table[1:])+'\n)\n')
    drawing.append(['lib_symbols', *[d.lib[k] for k in sorted(d.lib)]])
    drawing.extend(d.items); drawing.append(['sheet_instances',['path',q('/'),['page',q('1')]]])
    OUTPUT.write_text('(kicad_sch\n'+'\n'.join('  '+dump(v) for v in drawing[1:])+'\n)\n')
    (EL/(NAME+'.kicad_pro')).write_text('{}\n')
    MANIFEST.write_text(json.dumps({'sources':{n+'.kicad_sch':hashlib.sha256((EL/(n+'.kicad_sch')).read_bytes()).hexdigest() for n in sorted(d.sources)},'overview_sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),'layout':'integrated-signal-flow'},indent=2)+'\n')
    print(f'Integrated {len(d.source)} native symbol units into {OUTPUT.name}')

if __name__=='__main__': build_integrated()
