"""Create an unrouted placement study from the V0.3 schematic, not fabrication data.

KiCad 10 pcbnew is required. Standard footprints remain embedded in the board;
project-specific provisional footprints are kept in Placement.pretty.
Refuse to overwrite an edited board unless --force is explicitly supplied.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'electrical/pcb-draft'
LIB = OUT / 'Placement.pretty'
STD = Path('/usr/share/kicad/footprints')
BOARD = OUT / 'tpa3255-placement.kicad_pcb'
SCHEMATIC = ROOT / 'electrical/v03/tpa3255-v03.kicad_sch'
WIDTH, HEIGHT = 220, 160  # Initial space budget, not enclosure-approved dimensions.


def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def stable_id(key):
    return p.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL, 'diy-tpa3255/placement/' + key)))


def line(parent, x1, y1, x2, y2, layer, width=.12):
    s = p.PCB_SHAPE(parent)
    s.SetShape(p.SHAPE_T_SEGMENT)
    s.SetStart(xy(x1, y1)); s.SetEnd(xy(x2, y2))
    s.SetLayer(layer); s.SetWidth(p.FromMM(width)); parent.Add(s)


def rectangle(parent, x, y, w, h, layer):
    for a, b in [((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),
                 ((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]:
        line(parent, *a, *b, layer)


def text(board, label, x, y, size=1.3, layer=p.Dwgs_User):
    t = p.PCB_TEXT(board); t.SetText(label); t.SetPosition(xy(x,y))
    t.SetTextSize(xy(size,size)); t.SetTextThickness(p.FromMM(.18))
    t.SetLayer(layer); board.Add(t)


def custom_tht(name, w, h, pitch, drill, padsize, description):
    fp = p.FOOTPRINT(None); fp.SetFPIDAsString('Placement:'+name)
    fp.SetReference('REF**'); fp.SetValue(name); fp.SetAttributes(p.FP_THROUGH_HOLE)
    fp.SetLibDescription(description)
    rectangle(fp, -w/2, -h/2, w, h, p.F_Fab)
    rectangle(fp, -w/2-.5, -h/2-.5, w+1, h+1, p.F_CrtYd)
    rectangle(fp, -w/2, -h/2, w, h, p.F_SilkS)
    for n, x in [('1',-pitch/2),('2',pitch/2)]:
        pad = p.PAD(fp); pad.SetNumber(n); pad.SetPosition(xy(x,0))
        pad.SetAttribute(p.PAD_ATTRIB_PTH); pad.SetShape(p.PAD_SHAPE_CIRCLE)
        pad.SetSize(xy(padsize,padsize)); pad.SetDrillSize(xy(drill,drill))
        layers=p.LSET.AllCuMask(); layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask)
        pad.SetLayerSet(layers)
        fp.Add(pad)
    fp.Reference().SetPosition(xy(0,-h/2-1.4))
    fp.Value().SetVisible(False)
    p.PCB_IO_KICAD_SEXPR().FootprintSave(str(LIB), fp)


def make_library():
    LIB.mkdir(parents=True, exist_ok=True)
    custom_tht('MA5172_AE_Provisional',28.6,12.3,10,1.4,3,
               'Coilcraft Doc 943-1 body and pitch. 1.4mm finished hole and 3mm pad are provisional; tolerance and current review pending.')
    for d,pitch in [(8,3.5),(10,5)]:
        custom_tht(f'BP_Cap_D{d}_P{pitch}',d,d,pitch,.9,1.8,
                   'Non-polar capacitor space placeholder; exact MPN, body, lead and height not selected.')
    custom_tht('Fuse_P22_Provisional',30,12,22,1.5,3,
               'Unselected DC fuse and holder space reservation. No component compatibility or rating claimed.')
    # The schematic's axial diode convention is A=1, K=2. Preserve the band
    # location by renumbering the library's K=1, A=2 pads, not swapping nets.
    fp=p.FootprintLoad(str(STD/'Diode_THT.pretty'),'D_DO-35_SOD27_P7.62mm_Horizontal')
    for pad in fp.Pads(): pad.SetNumber({'1':'2','2':'1'}[pad.GetNumber()])
    fp.SetFPIDAsString('Placement:DO35_A1_K2_P7.62')
    fp.SetValue('DO35_A1_K2_P7.62')
    p.PCB_IO_KICAD_SEXPR().FootprintSave(str(LIB),fp)
    # Apply the same legacy THT writer correction to the reusable footprints.
    for path in LIB.glob('*.kicad_mod'):
        path.write_text(path.read_text().replace('(layers "*.Cu")','(layers "*.Cu" "*.Mask")'))
    (OUT/'fp-lib-table').write_text('(fp_lib_table\n  (lib (name "Placement")(type "KiCad")(uri "${KIPRJMOD}/Placement.pretty")(options "")(descr "Placement study; see README"))\n)\n')


def footprint(ref, value):
    """Footprint candidates are a space study; only named IC package mappings checked."""
    special={
        'U1':'Package_SO:HTSSOP-44_6.1x14mm_P0.635mm_TopEP4.14x7.01mm',
        'U401':'Package_SO:HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.96x2.96mm',
        'U601':'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
        'U301':'Package_SO:SSOP-4_4.4x2.6mm_P1.27mm',
        'U4':'Package_TO_SOT_SMD:SOT-23',
        'D303':'Package_TO_SOT_SMD:SOT-23',
        'D401':'Package_TO_SOT_SMD:TO-252-3_TabPin2',
        'F1':'Placement:Fuse_P22_Provisional',
    }
    if ref in special: return special[ref]
    if ref in ['U2','U3','U602']: return 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
    if ref in ['U303','U306']: return 'Package_TO_SOT_SMD:SOT-23-6'
    if ref.startswith('U'): return 'Package_TO_SOT_SMD:SOT-23-5'
    if ref in ['D301','D302']: return 'Placement:DO35_A1_K2_P7.62'
    if ref.startswith('L'): return 'Placement:MA5172_AE_Provisional'
    if ref.startswith('J'):
        if ref in ['J1','J2','J201','J202']:
            return 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-3-2-5.08_1x02_P5.08mm_Horizontal'
        n=4 if ref=='J303' else 3 if ref in ['J302','J601','J602','J603','J604'] else 2
        return f'Connector_PinHeader_2.54mm:PinHeader_1x0{n}_P2.54mm_Vertical'
    if ref.startswith('R'):
        pkg='2512_6332' if ref in ['R1','R2','R3','R4'] else '1206_3216' if ref=='R410' else '0805_2012'
        return f'Resistor_SMD:R_{pkg}Metric'
    if ref.startswith('C'):
        if 'BP' in value:
            return 'Placement:BP_Cap_D10_P5' if int(ref[1:])>=600 else 'Placement:BP_Cap_D8_P3.5'
        if ref in ['C205','C206']: return 'Capacitor_THT:CP_Radial_D18.0mm_P7.50mm'
        if ref in ['C215','C609']: return 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm'
        if ref in ['C5','C6','C7','C8','C304']:
            return 'Capacitor_THT:C_Rect_L18.0mm_W9.0mm_P15.00mm_FKS3_FKP3'
        if ref in ['C13','C14','C15','C16']:
            return 'Capacitor_THT:C_Rect_L13.0mm_W6.0mm_P10.00mm_FKS3_FKP3_MKS4'
        pkg='1206_3216' if value.startswith(('1u / 100V','10u /','180n','2.2u')) else '0805_2012'
        return f'Capacitor_SMD:C_{pkg}Metric'
    raise ValueError((ref,value))


def positions():
    # Positions in mm from the study's upper-left board corner. Through-hole
    # library origins vary; the verifier uses actual pad/courtyard geometry.
    pos={}
    def put(ref,x,y,angle=0,side='F'):
        assert ref not in pos,ref
        pos[ref]=(x,y,angle,side)
    fixed={
        'U1':(125,65),'U2':(86,37),'U3':(86,86),'U601':(52,45),'U602':(52,64),
        'J601':(12,23),'J602':(12,62),'J101':(12,10),'J102':(12,94),
        'J603':(70,26),'J604':(72,82),'J605':(12,112),'R608':(24,114),
        'C601':(38,25),'C602':(38,39),'C603':(38,61),'C604':(38,75),
        'R601':(26,22),'R602':(26,36),'R603':(26,58),'R604':(26,72),
        'C605':(62,27),'C606':(62,76),'R605':(60,20),'R606':(62,88),
        'R607':(46,88),'C609':(52,95),
        'C101':(77,26),'C121':(83,102),'R101':(77,20),'R121':(90,102),
        'R102':(78,35),'R103':(78,38),'R104':(78,41),'R105':(91,42),
        'R122':(78,85),'R123':(78,88),'R124':(78,91),'R125':(91,91),
        'C205':(135,21),'C206':(135,107),'R204':(65,93),'C215':(63,101),
        'R205':(74,99),'R206':(69,109),'C216':(74,105),'C217':(74,109),
        'J301':(12,128),'U301':(30,128),'D301':(18,132),'R303':(18,121),'R305':(30,121),
        'U302':(43,126),'R304':(43,121),'U303':(58,126),'R306':(58,114),'R307':(58,118),
        'U304':(69,126),'R308':(69,120),'R309':(73,132),'D302':(70,138),
        'U305':(82,126),'R310':(82,132),'C303':(82,136),'C304':(91,139),
        'U306':(96,126),'R311':(100,114),'R312':(100,118),'R313':(105,121),
        'C305':(104,131),'U307':(108,126),'R314':(108,131),
        'R301':(111,119),'R302':(113,116),'D303':(113,137),
        'U4':(65,148),'C301':(65,143),'C302':(65,152),
        'J302':(98,149),'J303':(112,148),
        'U401':(130,138),'D401':(148,142),'F1':(179,146),'C401':(148,130),'C402':(130,146),
        'R401':(120,132),'R402':(120,135),'R403':(120,138),'R404':(120,141),
        'R405':(140,132),'R406':(140,135),'R407':(130,130),'R408':(118,148),
        'R409':(118,151),'R410':(146,118),
    }
    for ref,(x,y) in fixed.items(): put(ref,x,y)
    for ref,x,y,a in [('J1',210,48,90),('J2',210,89,90),('J201',205,147,180),('J202',17,150,90)]:
        put(ref,x,y,a)
    for i,y in enumerate([35,55,75,95],1):
        put('L'+str(i),163,y)
        put('C'+str(i+4),182,y)
        put('C'+str(i+8),205,y)
        put('C'+str(i+12),184,y+9)
        put('R'+str(i),206,y-6 if i in [1,3] else y+9)
    for i,y in enumerate([50,60,72,82]):
        put('C'+str(150+i),97,y)
        put('R'+str(150+i),89,y)
        for ref,x,dy in [('C'+str(154+i),107,0),('R'+str(501+i),105,-4),
                         ('C'+str(501+i),100,-4),('C'+str(505+i),111,-4),('R'+str(505+i),111,-1)]:
            put(ref,x,y+dy,side='B')
    for ref,x,y in [('C607',57,44),('C608',57,64),('C218',86,40),('C219',86,89),
                    ('C102',92,34),('C103',92,38),('C122',92,86),('C123',92,90),
                    ('C1',135,57),('C2',135,60),('C3',135,74),('C4',135,77),
                    ('C201',131,62),('C202',131,65),('C203',131,68),('C204',131,71),
                    ('C208',118,55),('R201',117,59),('C207',117,63),('C209',125,55),
                    ('C210',117,74),('C211',117,67),('C212',117,70),('C213',117,78),
                    ('C214',121,80),('R202',113,73),('R203',112,85)]:
        put(ref,x,y,side='B')
    for ref,x in [('C310',43),('C311',58),('C312',69),('C313',82),('C314',96),('C315',108)]:
        put(ref,x,129,side='B')
    return pos


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force',action='store_true',help='Overwrite this generated placement study, losing manual PCB edits.')
    args=parser.parse_args()
    if BOARD.exists() and not args.force:
        parser.error('Board exists. Review manual changes first; --force rebuilds the placement study.')
    OUT.mkdir(parents=True,exist_ok=True)
    make_library()
    with tempfile.TemporaryDirectory(prefix='tpa-placement-') as td:
        netfile=Path(td)/'net.xml'
        subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadxml','-o',str(netfile),str(SCHEMATIC)],check=True)
        netlist=ET.parse(netfile).getroot()
    comps={c.attrib['ref']:c for c in netlist.findall('./components/comp')}
    places=positions()
    assert set(comps)==set(places),{'missing':sorted(set(comps)-set(places)),'extra':sorted(set(places)-set(comps))}
    board=p.BOARD(); board.SetCopperLayerCount(4)
    nets={}; pininfo={}
    for n in netlist.findall('./nets/net'):
        name=n.attrib['name']; net=p.NETINFO_ITEM(board,name); board.Add(net); nets[name]=net
        for node in n.findall('node'):
            pininfo[(node.attrib['ref'],node.attrib['pin'])]=(name,node.attrib)
    rows=[]
    for ref in sorted(comps,key=lambda r:(r.rstrip('0123456789'),int(''.join(filter(str.isdigit,r))))):
        comp=comps[ref]; value=comp.findtext('value'); fpname=footprint(ref,value)
        library,name=fpname.split(':')
        location=LIB if library=='Placement' else STD/(library+'.pretty')
        fp=p.FootprintLoad(str(location),name)
        if fp is None: raise ValueError(fpname)
        fp.SetFPIDAsString(fpname); fp.SetReference(ref); fp.SetValue(value)
        fp.SetUuid(stable_id(ref)); fp.SetBoardOnly(False)
        path=p.KIID_PATH()
        # Multi-unit parts export multiple space-separated symbol UUIDs. Link
        # to the first exported unit instead of passing an invalid UUID string.
        for part in (comp.find('sheetpath').attrib['tstamps']+comp.findtext('tstamps').split()[0]).split('/'):
            if part.strip(): path.push_back(p.KIID(part.strip()))
        fp.SetPath(path)
        fp.SetSheetname(comp.find('sheetpath').attrib['names'])
        fp.SetSheetfile(comp.find('sheetpath').attrib['names'].strip('/')+'.kicad_sch')
        expected={pin for (r,pin) in pininfo if r==ref}
        actual={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        assert actual==expected,(ref,fpname,actual,expected)
        for i,pad in enumerate(fp.Pads()):
            pad.SetUuid(stable_id(ref+'/pad/'+str(i)))
            if pad.GetAttribute()==p.PAD_ATTRIB_PTH:
                # Explicitly retain mask openings when KiCad 10 imports legacy
                # THT library footprints through pcbnew's standalone API.
                layers=pad.GetLayerSet(); layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask)
                pad.SetLayerSet(layers)
            if not pad.GetNumber(): continue  # stencil apertures are not electrical pads
            netname,attrs=pininfo[(ref,pad.GetNumber())]
            pad.SetNet(nets[netname]); pad.SetPinFunction(attrs.get('pinfunction',''))
            pad.SetPinType(attrs.get('pintype','passive'))
        board.Add(fp)
        x,y,angle,side=places[ref]; fp.SetPosition(xy(x,y))
        fp.SetOrientationDegrees(angle)
        if side=='B': fp.Flip(fp.GetPosition(),False)
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(xy(.9,.9)); fp.Reference().SetTextThickness(p.FromMM(.13))
        fp.Reference().SetLayer(p.F_Fab if side=='F' else p.B_Fab)
        source=location/(name+'.kicad_mod')
        status='package_candidate' if ref.startswith('U') or ref in ['D303','D401'] else 'provisional'
        rows.append([ref,value,fpname,status,x,y,angle,side,hashlib.sha256(source.read_bytes()).hexdigest()])
    for i,(x,y) in enumerate([(5,5),(WIDTH-5,5),(WIDTH-5,HEIGHT-5),(5,HEIGHT-5)],1):
        hole=p.FootprintLoad(str(STD/'MountingHole.pretty'),'MountingHole_3.2mm_M3')
        hole.SetReference('H'+str(i)); hole.SetUuid(stable_id('H'+str(i)))
        hole.SetBoardOnly(True); hole.SetPosition(xy(x,y)); hole.Value().SetVisible(False)
        board.Add(hole)
    rectangle(board,0,0,WIDTH,HEIGHT,p.Edge_Cuts)
    # Drawings only: these reservations are not a validated 3D keepout or a ground split.
    rectangle(board,113,37,27,57,p.Dwgs_User)
    text(board,'TOP HEATSINK SPACE TBD',126.5,39.5,.9)
    rectangle(board,22,140,32,15,p.Dwgs_User)
    text(board,'12V PROTECTION',38,145,1.2)
    text(board,'RESERVED / NOT DESIGNED',38,150,.8)
    text(board,'TPA3255  /  PLACEMENT ONLY  /  NOT FOR FABRICATION',110,7,1.8,p.F_SilkS)
    text(board,'NO TRACKS OR PLANES  -  COMPONENT MPNs / THERMAL DESIGN PENDING',111,11,1,p.F_SilkS)
    for label,x,y in [('XLR / RCA',36,9),('INPUT / PFFB',91,14),('POWER / LC',172,14),('TRIGGER / CONTROL',63,109),('48V SWITCH',161,124)]:
        text(board,label,x,y)
    board.BuildConnectivity()
    # Finalize the mask layers after all library loads, flips and connectivity.
    # The standalone KiCad API may normalize legacy THT padstacks during import.
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute()==p.PAD_ATTRIB_PTH:
                layers=p.LSET.AllCuMask(); layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask)
                pad.SetLayerSet(layers)
    p.SaveBoard(str(BOARD),board)
    # KiCad 10.0.6's standalone writer can omit *.Mask for legacy imported
    # THT padstacks despite GetLayerSet() reporting both mask layers. These
    # placement-study PTH pads all require exposed solder lands. Restore the
    # native pad layer declaration, then verify by reloading in the audit tool.
    data=BOARD.read_text()
    data=data.replace('(layers "*.Cu")','(layers "*.Cu" "*.Mask")')
    BOARD.write_text(data)
    libraries=sorted({row[2].split(':')[0] for row in rows} | {'MountingHole'})
    entries=[]
    for name in libraries:
        uri='${KIPRJMOD}/Placement.pretty' if name=='Placement' else '${KICAD10_FOOTPRINT_DIR}/'+name+'.pretty'
        entries.append(f'  (lib (name "{name}")(type "KiCad")(uri "{uri}")(options "")(descr ""))')
    (OUT/'fp-lib-table').write_text('(fp_lib_table\n'+'\n'.join(entries)+'\n)\n')
    with (OUT/'placement.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['reference','value','footprint','status','x_mm','y_mm','rotation_deg','side','footprint_sha256'])
        writer.writerows(rows)
    print(f'Created {BOARD.relative_to(ROOT)}: {len(comps)} electrical footprints, 4 mounting holes, {len(nets)} nets, no tracks.')


if __name__=='__main__': main()
