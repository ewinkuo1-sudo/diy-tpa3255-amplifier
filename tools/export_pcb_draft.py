"""Export native board layers and a Chinese annotated overview from the same board."""
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'electrical/pcb-draft/preview'
BOARD=ROOT/'electrical/pcb-draft/tpa3255-placement.kicad_pcb'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for side,layers in [('top','F.Cu,F.SilkS,F.Fab,Edge.Cuts,Dwgs.User'),
                        ('bottom','B.Cu,B.SilkS,B.Fab,Edge.Cuts')]:
        target=OUT/(side+'.svg')
        args=['kicad-cli','pcb','export','svg','--layers',layers,'--page-size-mode','2',
              '--exclude-drawing-sheet','--mode-single','-o',str(target),str(BOARD)]
        if side=='bottom':args.insert(6,'--mirror')
        subprocess.run(args,check=True)
        # Normalize timestamp/whitespace; replace only the exported background
        # for legible standalone PNGs, retaining native board geometry.
        svg=target.read_text()
        svg=re.sub(r'<title>.*?</title>',f'<title>TPA3255 placement study: {side}</title>',svg,flags=re.S)
        svg='\n'.join(line.rstrip() for line in svg.splitlines())+'\n'
        target.write_text(svg)
        subprocess.run(['rsvg-convert','-b','#143c36','-w','2200','-o',str(target.with_suffix('.png')),str(target)],check=True)
    # Embed the real KiCad export; no invented routing or component geometry.
    raw=(OUT/'top.svg').read_text()
    start=raw.index('<g '); end=raw.rindex('</svg>')
    inner=raw[start:end].replace('#C83434','#e5b85d').replace('#FFFFFF','#ecf4ee').replace('#000000','#143c36')
    root=ET.parse(OUT/'top.svg').getroot(); view=root.attrib['viewBox']
    svg=['''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1320" viewBox="0 0 1800 1320" role="img" aria-labelledby="title desc">
<title id="title">PCB 第一版：先安排零件的位置</title>
<desc id="desc">真正 KiCad 電路板檔案的正面配置預覽。180 個元件已放入，尚未走線。右側以中文介紹輸入、回授、功率輸出、Trigger 與電源保護。</desc>
<style>text{font-family:"Noto Sans CJK TC","Noto Sans TC",sans-serif;fill:#1b3447}.title{font-size:42px;font-weight:700}.head{font-size:27px;font-weight:700}.body{font-size:23px}.small{font-size:21px;fill:#52687b}</style>
<rect width="1800" height="1320" fill="#f2f5f7"/>
<text x="42" y="65" class="title">PCB 第一版：先安排零件的位置</text>
<text x="44" y="108" class="body">180 個元件已放入；尚未走線，不能送廠製作。板子暫抓 22 × 16 公分，還會配合機箱調整。</text>
<text x="44" y="145" class="small">這是正面配置，背面也有零件。金色是焊接位置；兩個電源模組放在機箱其他位置。</text>
<rect x="38" y="176" width="1324" height="964" rx="14" fill="#143c36"/>
''']
    svg.append(f'<svg x="40" y="178" width="1320" height="960" viewBox="{view}">{inner}</svg>')
    sections=[('1','音樂入口','接 Z10 的 XLR／RCA。','面板插座另以短線連接。',28,18,200),
              ('2','輸入與回授','處理音樂訊號，','並取回輸出訊號做修正。',88,18,365),
              ('3','放大與輸出','主晶片搭配四顆大電感，','把訊號送到左右喇叭。',174,20,530),
              ('4','自動開關控制','接收前級的 Trigger，','控制開聲與待機順序。',45,113,695),
              ('5','電源保護','控制主電源的進入。','12V 保護區仍需補電路。',166,126,860)]
    for n,title,a,b,x,y,cy in sections:
        bx,by=40+x*6,178+y*6
        svg.append(f'<circle cx="{bx}" cy="{by}" r="19" fill="#fff3ce" stroke="#233d48" stroke-width="2"/><text x="{bx}" y="{by+8}" text-anchor="middle" class="head">{n}</text>')
        svg.append(f'<rect x="1390" y="{cy}" width="370" height="139" rx="15" fill="white"/><text x="1410" y="{cy+38}" class="head">{n}　{title}</text><text x="1410" y="{cy+77}" class="body">{a}</text><text x="1410" y="{cy+111}" class="body">{b}</text>')
    svg.append('''<text x="1395" y="1053" class="small">中央框：散熱器待配置</text>
<text x="1395" y="1089" class="small">左下框：12V 保護待補</text>
<rect x="40" y="1170" width="1720" height="106" rx="17" fill="white"/>
<text x="65" y="1211" class="head">接下來：補保護、定料件和散熱，再細調零件位置與走線。</text>
<text x="65" y="1250" class="body">這張板只處理低壓音訊與控制；配置通過幾何檢查，仍不代表音質、散熱或整機設計已驗證。</text>
</svg>''')
    target=OUT/'placement-explained.svg'; target.write_text('\n'.join(svg)+'\n')
    subprocess.run(['rsvg-convert','-o',str(target.with_suffix('.png')),str(target)],check=True)


if __name__=='__main__':main()
