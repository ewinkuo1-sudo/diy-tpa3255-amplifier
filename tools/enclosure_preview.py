"""Project the rectangular space study to SVG; this is not an OpenSCAD renderer.

Reads scalar dimensions from the SCAD source. If its geometry is changed beyond
the current rectangular layout, update this preview implementation as well.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "mechanical/enclosure-concept.scad").read_text()
    p = {key: float(value) for key, value in re.findall(
        r"^([a-z_]+)\s*=\s*([0-9.]+);", source, re.M)}
    w, d, h = (p[k] for k in ("case_w", "case_d", "case_h"))
    wall = p["wall"]
    pw, pd, pt, pz = (p[k] for k in ("pcb_w", "pcb_d", "pcb_t", "pcb_z"))
    sw, sd, sh, sz = (p[k] for k in ("sink_w", "sink_d", "sink_h", "sink_base_z"))
    if not (wall > 0 and min(p.values()) > 0 and
            pw < w - 2 * wall and pd < d - 2 * wall and
            pz > wall and pz + pt < sz and sz + sh < h - wall):
        raise ValueError("Space-study dimensions overlap or exceed the enclosure")
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">',
           '<title>TPA3255 V0.1 機殼空間配置草案</title>',
           '<desc>左側為開蓋斜視示意，右側為俯視配置。灰色為機殼，綠色為 PCB 占位，橘色為散熱器占位。尚未完成 PCB 佈局、固定孔及熱設計。</desc>',
           '<rect width="1200" height="700" fill="#f4f6fa"/>',
           '<g font-family="Noto Sans CJK TC, sans-serif" fill="#172b46">']

    def text(x, y, label, size=18, color="#172b46"):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(label)}</text>')

    def rect(x, y, width, height, fill, stroke="none", opacity=1):
        out.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill}" stroke="{stroke}" fill-opacity="{opacity}"/>')

    def project(v):
        x, y, z = v
        return 310 + 1.1 * x - 0.8 * y, 260 + 0.50 * x + 0.36 * y - 1.6 * z

    def polygon(vertices, fill, opacity=1, stroke="#64748b"):
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in map(project, vertices))
        out.append(f'<polygon points="{points}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="1.2" stroke-linejoin="round"/>')

    def box(x, y, z, a, b, c, fill, opacity=1, stroke="#64748b"):
        polygon([(x,y,z),(x+a,y,z),(x+a,y,z+c),(x,y,z+c)], fill, opacity, stroke)
        polygon([(x,y,z),(x,y+b,z),(x,y+b,z+c),(x,y,z+c)], fill, opacity, stroke)
        polygon([(x+a,y,z),(x+a,y+b,z),(x+a,y+b,z+c),(x+a,y,z+c)], fill, opacity, stroke)
        polygon([(x,y+b,z),(x+a,y+b,z),(x+a,y+b,z+c),(x,y+b,z+c)], fill, opacity, stroke)
        polygon([(x,y,z+c),(x+a,y,z+c),(x+a,y+b,z+c),(x,y+b,z+c)], fill, opacity, stroke)

    text(48, 57, "TPA3255 / V0.1 機殼空間配置", 30)
    text(48, 91, "外接電源方案 · 機殼、PCB 與散熱空間的第一版假設", 18, "#52647a")
    rect(40, 120, 620, 355, "#ffffff")
    rect(680, 120, 480, 355, "#ffffff")
    text(64, 155, "01  開蓋斜視示意", 21)
    text(704, 155, "02  俯視配置", 21)

    # Transparent shell segments reproduce the current SCAD difference() shape.
    box(0, 0, 0, w, d, wall, "#d7e0e9", 0.7)
    box(0, 0, wall, w, wall, h-wall, "#b5c6d5", 0.10)
    box(0, wall, wall, wall, d-2*wall, h-wall, "#b5c6d5", 0.10)
    box((w-pw)/2, (d-pd)/2, pz, pw, pd, pt, "#23a17b", 0.9, "#137256")
    box((w-sw)/2, (d-sd)/2, sz, sw, sd, sh, "#efab57", 0.85, "#986120")
    box(w-wall, wall, wall, wall, d-2*wall, h-wall, "#b5c6d5", 0.10)
    box(0, d-wall, wall, w, wall, h-wall, "#b5c6d5", 0.10)
    text(75, 452, f"外形 {w:g} × {d:g} × {h:g} mm；壁厚 {wall:g} mm", 18)

    scale = min(320 / w, 220 / d)
    tx, ty = 760, 188
    rect(tx, ty, w*scale, d*scale, "#d7e0e9", "#64748b")
    rect(tx+wall*scale, ty+wall*scale, (w-2*wall)*scale, (d-2*wall)*scale, "#f8fafc", "#94a3b8")
    rect(tx+(w-pw)/2*scale, ty+(d-pd)/2*scale, pw*scale, pd*scale, "#b6e7d8", "#137256")
    rect(tx+(w-sw)/2*scale, ty+(d-sd)/2*scale, sw*scale, sd*scale, "#f5ce9e", "#986120")
    text(738, 450, f"PCB {pw:g} × {pd:g} mm / 散熱區 {sw:g} × {sd:g} mm", 17)

    rect(55, 510, 18, 18, "#c2d0dd")
    text(86, 525, "機殼空間")
    rect(290, 510, 18, 18, "#23a17b")
    text(321, 525, "PCB 占位（尚無走線）")
    rect(650, 510, 18, 18, "#efab57")
    text(681, 525, f"散熱器占位（高 {sh:g} mm）")
    text(55, 573, "所有尺寸均為占位假設；接頭、固定孔、通風、元件高度與加工公差尚待設計。", 18)
    text(55, 607, "圖中散熱區尚未建立與晶片的實際接觸；此圖不能作為製造或散熱驗證依據。", 18)
    text(55, 656, "依 enclosure-concept.scad 尺寸繪製的投影示意 · 非 OpenSCAD 渲染", 15, "#52647a")
    out.append('</g></svg>')
    target = ROOT / "mechanical/enclosure-preview.svg"
    target.write_text("\n".join(out) + "\n")
    print(target)


if __name__ == "__main__":
    main()
