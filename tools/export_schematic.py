"""Export the current KiCad schematic to PDF, SVG and GitHub PNG previews."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / 'electrical/tpa3255-v02.kicad_sch'
PREVIEW = ROOT / 'electrical/preview'


def main():
    PREVIEW.mkdir(exist_ok=True)
    subprocess.run([
        'kicad-cli', 'sch', 'export', 'svg', '-o', str(PREVIEW) + '/',
        str(SCHEMATIC),
    ], check=True)
    subprocess.run([
        'kicad-cli', 'sch', 'export', 'pdf', '-o',
        str(PREVIEW / 'tpa3255-v02.pdf'), str(SCHEMATIC),
    ], check=True)
    for svg in sorted(PREVIEW.glob('tpa3255-v02*.svg')):
        # KiCad appends whitespace to SVG XML lines; keep exports diff-clean.
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
        subprocess.run([
            'rsvg-convert', '-w', '2400', '-o', str(svg.with_suffix('.png')),
            str(svg),
        ], check=True)


if __name__ == '__main__':
    main()
