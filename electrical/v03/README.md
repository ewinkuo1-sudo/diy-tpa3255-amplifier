# V0.3 電路圖：完整單頁整合電路

原八頁的所有元件已重新編排成 **一張 A0 橫式、連續接線的完整電路圖**，包含 XLR 平衡接收／RCA 選擇、PFFB、四顆 MA5172-AE，以及隔離 Trigger 控制與 48V 功率電源開關。180 個元件、483 個腳位、120 個網路與原版完全一致；音訊、四路回授與主要啟停控制以實際導線連接；電路功能未改。電路已有接線檢查及簡化模型驗證，亦有[未走線 PCB 配置草案](../pcb-draft/README.md)，尚無實機性能驗證。

整機採[機內電源、單一市電入口](../system-power/README.md)。總圖完整涵蓋原八頁的低壓音訊與控制；J201／J202 為機內供電接點，市電區另行規劃，沒有包含在本版 ERC／模型驗證內。

**[開啟／下載單頁 PDF](preview/tpa3255-v03-overview.pdf)** · [放大 SVG](preview/tpa3255-v03-overview.svg) · [高解析 PNG](preview/tpa3255-v03-overview.png) · [單頁 KiCad 圖檔](tpa3255-v03-overview.kicad_sch) · [合併檢查](overview-validation.md)

![完整單頁電路總圖](preview/tpa3255-v03-overview.png)

建議將單頁 PDF 傳給教授，放大看元件數值；列印以 A0 原尺寸為佳，縮到 A4 文字會太小。PDF／SVG 是可放大的向量圖；PNG 供快速預覽。供電、偏壓與部分狀態線仍以同名標籤表示相連；導線交叉有圓點才相接。

總圖閱讀順序：

1. 左側 XLR／RCA 輸入與選擇 → NE5532 差動驅動 → 中央 TPA3255 → 右側 LC 與喇叭。
2. 喇叭端的四路 PFFB 從功率級上下方繞回 SUM 加總點；回授阻容直接畫在回線上。
3. 左下方為 12V 待機、類比供電與 VMID；功率級 PVDD 去耦接在右側供電幹線。
4. 下方 Trigger 經隔離、模式選擇、電源監測與關機保持，控制 48V eFuse；延遲開聲線直接接回 TPA3255 的 RESET。

原八頁的方格分區已移除。U1／U601 的圖形腳位改按訊號流排列，實體腳號、名稱與電氣型態均保留；一個 IC 仍是一個 IC。

[中文設計說明](../../docs/V0.3_設計說明.md) · [電路／模型驗證](validation.md) · [BOM 草案](bom-draft.csv)

<details>
<summary>展開原八頁分區圖（維護與逐區查閱）</summary>

[下載原八頁 PDF](preview/tpa3255-v03.pdf)。以下為原版頁次；整合總圖已依訊號路徑重新安排。

## 1. 功率級與輸出電感

![功率級](preview/tpa3255-v03.png)

[放大 SVG](preview/tpa3255-v03.svg)

## 2. RCA 插座與選定訊號的差動驅動級

RCA 或 XLR 訊號由第八頁 J603／J604 選擇後，送入本頁的 C101／C121。

![輸入級](preview/tpa3255-v03-input.png)

[放大 SVG](preview/tpa3255-v03-input.svg)

## 3. 供電去耦

![供電去耦](preview/tpa3255-v03-power-control.png)

[放大 SVG](preview/tpa3255-v03-power-control.svg)

## 4. 濾波後回授 PFFB

![PFFB](preview/tpa3255-v03-feedback.png)

[放大 SVG](preview/tpa3255-v03-feedback.svg)

## 5. Trigger 接收與關機延遲

![Trigger](preview/tpa3255-v03-trigger.png)

[放大 SVG](preview/tpa3255-v03-trigger.svg)

## 6. 48V 功率電源開關與延遲開聲

![功率電源開關](preview/tpa3255-v03-dc-switch.png)

[放大 SVG](preview/tpa3255-v03-dc-switch.svg)

## 7. 待機控制供電

![待機控制供電](preview/tpa3255-v03-control-supply.png)

[放大 SVG](preview/tpa3255-v03-control-supply.svg)

## 8. XLR 平衡接收與輸入選擇

![XLR 平衡輸入](preview/tpa3255-v03-xlr-input.png)

[放大 SVG](preview/tpa3255-v03-xlr-input.svg)

左右聲道各一個 XLR 母座。J603／J604 均接 2–3 選 XLR，均接 1–2 選 RCA；切換前先將 J302 設為 OFF 待機。這版是板上跳線設定，機殼面板切換方式尚待機構與靜音設計。

</details>

## 原始檔、編輯與驗證

單頁總圖可用 KiCad 10 開啟 [tpa3255-v03-overview.kicad_pro](tpa3255-v03-overview.kicad_pro)，它是包含全部元件的原生單頁圖檔。由現行八頁來源讀取全部元件，再重新配置位置與實際導線；保留元件、數值、單元及符號 UUID。`Overview.kicad_sym` 保存 U1／U601 的功能排列圖形，其餘符號沿用 Project 庫。

維護時仍以八頁來源為準，再重建總圖。既有 PCB 對應原階層路徑，請繼續從原專案更新 PCB；總圖若另行編輯，不會自動回寫來源，重建也會覆寫總圖。`overview-sources.json` 記錄 SHA-256，驗證可偵測來源變動而總圖尚未更新。

只更新總圖時執行（不需重跑電路模型）：

```sh
python3 tools/build_schematic_overview.py
python3 tools/verify_schematic_overview.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03-overview.kicad_sch --pdf-from-svg --png-width 4800
```

驗證會比對元件、每個符號的電氣腳位、全部接線與 ERC，再暫時移除標籤，檢查音訊、回授及主要控制路徑仍靠導線完整連接。PDF 由 KiCad SVG 轉為靜態向量圖，保留 A0 尺寸、中文與細節。

KiCad 10 開啟 [tpa3255-v03.kicad_pro](tpa3255-v03.kicad_pro)，再開同名原理圖；自訂符號庫已隨附。電感料號已選，其餘 BOM 仍有待定項，全部 footprint 尚未定案。

在儲存庫根目錄執行：

```sh
python3 tools/verify_v03.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03.kicad_sch
```

`verify_v03.py` 檢查實際 KiCad 接線表，更新 BOM、AC 數據與控制時序規格模型。後者不是實際控制 IC 的 SPICE 模型，也沒有驗證真正的回授穩定裕度。

`tools/build_schematic_v03.py` 只供重建這版初始圖面，會覆寫本資料夾的原理圖、符號庫、預期接線表與專案檔。手動編輯後使用上述驗證與匯出指令，避免直接重建。V0.2 仍保留在[上層歷史圖面](../README.md)。
