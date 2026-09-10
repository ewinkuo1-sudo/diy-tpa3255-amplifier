"""Export the current KiCad schematic to PDF, SVG and GitHub PNG previews."""
from pathlib import Path
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / 'electrical/tpa3255-v02.kicad_sch'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schematic',nargs='?',type=Path,default=SCHEMATIC)
    schematic=parser.parse_args().schematic.resolve()
    preview=schematic.parent/'preview'
    preview.mkdir(exist_ok=True)
    subprocess.run([
        'kicad-cli', 'sch', 'export', 'svg', '-o', str(preview) + '/',
        str(schematic),
    ], check=True)
    subprocess.run([
        'kicad-cli', 'sch', 'export', 'pdf', '-o',
        str(preview / (schematic.stem+'.pdf')), str(schematic),
    ], check=True)
    for svg in sorted(preview.glob(schematic.stem+'*.svg')):
        # KiCad appends whitespace to SVG XML lines; keep exports diff-clean.
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
        subprocess.run([
            'rsvg-convert', '-w', '2400', '-o', str(svg.with_suffix('.png')),
            str(svg),
        ], check=True)


if __name__ == '__main__':
    main()
