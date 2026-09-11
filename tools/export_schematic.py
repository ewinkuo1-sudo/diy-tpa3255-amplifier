"""Export the current KiCad schematic to PDF, SVG and GitHub PNG previews."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / 'electrical/tpa3255-v02.kicad_sch'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schematic',nargs='?',type=Path,default=SCHEMATIC)
    parser.add_argument('--png-width',type=int,default=2400,help='PNG preview width in pixels')
    parser.add_argument('--pdf-from-svg',action='store_true',help='Compact static vector PDF; single-sheet drawings only')
    args=parser.parse_args()
    if args.png_width<=0:
        parser.error('--png-width must be positive')
    schematic=args.schematic.resolve()
    preview=schematic.parent/'preview'
    preview.mkdir(exist_ok=True)
    # Collect only files from this export, since source and derived overview
    # previews share a prefix and directory.
    with tempfile.TemporaryDirectory(prefix='schematic-export-') as temp:
        subprocess.run([
            'kicad-cli', 'sch', 'export', 'svg', '-o', temp + '/', str(schematic),
        ], check=True)
        svgs=[]
        for generated in sorted(Path(temp).glob('*.svg')):
            svg=preview/generated.name
            svg.write_text('\n'.join(line.rstrip() for line in generated.read_text().splitlines())+'\n')
            svgs.append(svg)
    pdf=preview/(schematic.stem+'.pdf')
    if args.pdf_from_svg:
        if len(svgs)!=1 or svgs[0].stem!=schematic.stem:
            parser.error('--pdf-from-svg requires exactly one schematic page')
        subprocess.run(['rsvg-convert','-f','pdf','-o',str(pdf),str(svgs[0])],check=True)
    else:
        subprocess.run([
            'kicad-cli', 'sch', 'export', 'pdf', '-o',str(pdf),str(schematic),
        ], check=True)
    for svg in svgs:
        subprocess.run([
            'rsvg-convert', '-w', str(args.png_width), '-o', str(svg.with_suffix('.png')),
            str(svg),
        ], check=True)


if __name__ == '__main__':
    main()
