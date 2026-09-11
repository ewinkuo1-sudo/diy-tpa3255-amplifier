# TPA3255 接班進度

更新：2026-09-11，Codex。儲存庫 `ewinkuo1-sudo/diy-tpa3255-amplifier`；本次工作副本 `~/Projects/diy-tpa3255-amplifier`，原副本仍在 `~/.openclaw/workspace/diy-tpa3255-amplifier`。

## 使用者方向與同步約定

AI 應用課程，可含電路、材料、PCB 與 3D 設計；期限、預算、設備未定。前級為 Eversolo DAC-Z10，喇叭為 Usher BE-718，初期目標 2×50W / 8Ω。Purifi 在另一獨立儲存庫。

使用者要求每次完成並檢查後立即 commit / push 並回報，首頁同步可看的圖面。推送前確認遠端進度，不覆寫其他協作者。最近要求由設計端選電感、處理 PCB 注意事項、配合 Z10 Trigger 自動開關，並補上 XLR。

最新已確定：**電源內建，機背只接一條市電電源線**。取代先前外接兩路 DC 的成品方向；不需再詢問內建或外接。

使用者表示看不懂電路圖。後續說明先用成品接線、用途與操作介紹，再提供零件細節；首頁已先放 `docs/使用方式圖解.md` 的中文圖解（SVG／PNG），說明 Z10、後級、喇叭、機內電源與 Trigger。這是功能示意，不是定案面板、板數、配置或比例圖。

最新要求開始 PCB；已完成第一份未走線配置草案。可以先做配置與封裝審查，不需要等到實機音質量測後才能開始；正式走線／製板仍須處理下述電路與熱設計問題。

最新回饋：使用者要的是將八頁的所有內容重新編排成一張連續電路圖。前一版 A0 直式只是將八頁位置平移到 2×4 方格，不符合這個意思；已改成下述 **A0 橫式整合電路圖**。

## 新增：重新佈圖與連續接線的完整電路

- `electrical/v03/tpa3255-v03-overview.kicad_sch`／同名專案：保留原八頁全部 180 元件、192 符號單元（含電源旗標）。左右音訊由輸入經驅動、TPA3255 到 LC 與喇叭；四路 PFFB 直接沿回線繞回 SUM。下方串接 Trigger、隔離、啟停條件、48V eFuse 與 RESET。供電／偏壓及部分狀態線使用同名局部標籤。
- `tools/integrated_schematic_layout.py` 定義元件位置、導線與中文閱讀提示；`tools/build_schematic_overview.py` 為入口及原生格式共用函式。讀目前八頁來源，未呼叫會覆寫來源的初始電路生成器。
- U1／U601 的圖形腳位依訊號流重新排列，另存 `Overview.kicad_sym`；`sym-lib-table` 加入該庫，原 Project 庫未修改。元件 UUID、單元、實體腳號、名稱與電氣型態保留。其他符號仍使用 Project 庫。
- `tools/verify_schematic_overview.py` 比對原版／整合版實際匯出接線表與 `expected-connections.csv`：180 元件、483 腳位、120 網路群組。另比對每腳電氣定義、原生單元身份與屬性；移除標籤後再次匯出接線表，確認音訊、四路回授與主要啟停路徑確實由導線連通。兩版 ERC 要求 0 錯誤／0 警告，無排除。
- `overview-sources.json` 保存來源及總圖雜湊。局部標籤匯出時自訂名稱增加 `/` 路徑前綴；原未命名節點使用接線契約名稱。電氣等價以腳位群組判斷。
- A0 橫式向量 PDF／SVG 與 4800 像素 PNG 已同步至首頁；放大可看元件數值。原八頁 PNG 仍收在可展開區域。

**八頁來源仍是電路與既有 PCB 維護主檔**；板檔 UUID 路徑對應原階層，請從原專案更新 PCB。先改來源，再調整整合圖配置與接線並重建／驗證。總圖手改不會回寫來源，重建會覆寫衍生檔。這次未改電路功能、PCB 或性能模型，未新增實機驗證。

```sh
python3 tools/build_schematic_overview.py
python3 tools/verify_schematic_overview.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03-overview.kicad_sch --pdf-from-svg --png-width 4800
```

匯出工具仍只更新這次實際輸出的檔案，避免八頁原版與總圖共用檔名前綴時誤覆寫彼此的 PNG。

## 目前成果：V0.3 原理圖草案

- `electrical/v03/tpa3255-v03.kicad_pro`：八頁原理圖，依序為功率級、訊號驅動、類比供電、PFFB、Trigger、主電源開關、控制供電、XLR 輸入。
- `electrical/v03/README.md`：單頁總圖為預設看圖入口，原八頁 PNG／SVG／PDF 保留在可展開區域。180 個元件；原理圖 Footprint 欄位仍空白，PCB 封裝候選另列，尚未定料放行。
- `docs/V0.3_設計說明.md`：元件來源、訊號路徑、控制方式與限制；`docs/V0.3_PCB設計要求.md` 為下階段佈局要求。
- L1–L4 選 Coilcraft MA5172-AE：10µH，25°C 最大 DCR 26mΩ；45A 是典型 10% 電感下降條件，不是連續額定。
- 四路同臂 PFFB 採 TI SLAA788A TPA3255 範例起始值，SUM 在 AC 耦合前；輸出阻尼為 220nF + 1Ω，NE5532 回授補償 330pF。真實穩定裕度尚未驗證。
- XLR：U601 INA2137UA，實體 SOIC-14 腳位，約 0.5 倍差動接收；U602 兩個 NE5532 跟隨器提供低阻抗 REF。正負線各串 47Ω／0.1% 與 47µF BP，按聲道配對電容到 1%；輸出再隔直流。R607／C609 獨立濾波 12V 支路，C607／C608 本地去耦。
- J603／J604 各裝一個跳線帽：兩個都接 2–3 選 XLR，兩個都接 1–2 選 RCA，預定初裝 XLR。切換先將 J302 設為 OFF 待機；尚無面板切換／切換靜音電路。
- XLR pin 1／金屬外殼接 CHASSIS，R608 單點接 GND；RCA 插座絕緣。Trigger 的 TRIG_RETURN 維持隔離。
- Trigger 以 12V 名義、9–15V、tip 正／sleeve 負為待實測假設。Z10 手冊確認有 Trigger，但缺少完整電流、電平容差與極性資料。12V 設計負載約 1.6mA，不能引用其他機種 150mA 當成 Z10 規格。
- J302 外接 AUTO／OFF／ON 的 SPDT 中心斷開開關。TPS3808 監測輔助電源與 PVDD；開機先升功率電源，再延遲開聲；關機先 RESET 靜音，再延後停止 eFuse。
- 主電源以 TPS26631PWPR 切換、STPS5H100B 反接保護。eFuse 約 4.5A 名義限流，MODE 懸空選鎖定，軟啟動名義約 2.2s；F1 為 T5A／至少 80VDC 的規格占位，尚未選料號／協調曲線。
- PCB 封裝核對修正 D303 BAT54：原兩腳邏輯符號改為 SOT-23 實體 1=AUDIO_MR（A）、2=NC、3=AUX_GOOD（K），功能方向不變；原理圖、符號庫、接線契約與檢查已同步。D301／D302 仍採邏輯 A=1、K=2，專用 DO-35 封裝已反轉標準庫編號以維持陰極帶正確。
- 整機電源見 `electrical/system-power/README.md` 與方塊圖：單一 IEC 入口、交流保護／雙極總開關待選，機內 PS1 UHP-200-48 與 PS2 RS-15-12 為首輪候選，尚未採購。J201／J202 圖面文字已改為機內 DC 接點；音訊原理圖不含市電。
- Trigger 關機為待機：只切功率級 48V；兩組機內 AC/DC 及 12V 類比／控制仍有電。後方總開關撤除兩組 AC/DC 的輸入。待機耗電未測，功率電容不會立即放空。
- V0.2 圖面與模型保留於 `electrical/`、`simulation/` 上層，作為歷史基線。機殼仍是 V0.1 占位模型，尚未按電感／XLR／散熱器重新配置。

## 新增：PCB 初步配置

`electrical/pcb-draft/tpa3255-placement.kicad_pcb`／同名專案可直接用 KiCad 10 開啟。180 個電路元件（正面 127／背面 53）、4 個 NPTH 固定孔；暫用 220×160 mm、4 層、1.6 mm，尚無走線與覆銅。只包括低壓音訊與控制，機內 AC/DC 和市電線束另置。

`placement.csv` 記錄初始配置／封裝候選／來源 SHA-256。主要 IC 封裝族與腳序已核對；其餘電容、電阻、F1／座和板端接頭多為占位，全部仍未放行製造。面板 XLR／RCA／Trigger 插座不是這些排針，線束與防呆接頭待選。初始位置定義在 `tools/build_pcb_draft.py`；CSV 是輸出記錄，改板檔後需同步更新，不能把 CSV 當成自動匯入來源。

首頁已有中文 PCB 配置圖；`preview/top`、`bottom` 是 KiCad 原始預覽，背面以背面視角輸出。中文圖嵌入真實板檔匯出，不繪製虛構走線。散熱器與 12V 保護只預留框，尚未完成機構干涉／高度與熱路徑驗證。電源與訊號回路仍需縮短、重新微調配置。

## 驗證

`python3 tools/verify_v03.py` 通過：KiCad 10.0.6 ERC 0 錯誤／0 警告（無排除）；180 元件、483 腳、120 nets 群組吻合預期，另以獨立實體腳位檢查 XLR、PFFB、電源及控制。較前版多出 BAT54 實體 NC 腳及其獨立未接網路。

ngspice 47 執行 12 組 RCA／XLR AC 模型（4Ω、8Ω、空載 × 功率級無限頻寬／自訂 100kHz 極點）與 2 組共模模型。50W/8Ω 名義靈敏度約 RCA 2.126Vrms、XLR 差動 4.268Vrms；按 Z10 2.5／5Vrms 驅動，三個檢查頻率的輸出差異均小於 0.1dB。

9 個控制時序規格模型涵蓋正常開關、任一電源缺失、5ms Trigger 脈衝、主／輔助電源掉壓、eFuse 鎖定，以及新增的兩路電源啟動順序互換。後兩者用 1s／3s 階躍作測試刺激，非廠商波形。腳位與阻容核算不能當成實際半導體或市電驗證。數據及原始模型位於 `simulation/v03/`。

運放及 INA2137 內部比例仍理想化，TPA3255 只有線性增益源，100kHz 極點是自行假設；未驗證 PWM 延遲、真實 CMRR、噪聲、THD、迴路穩定裕度或偏壓建立爆音。已檢視圖面預覽；PCB 未走線，沒有 Gerber、整機 EMI／熱或實測。

`python3 tools/verify_pcb_draft.py` 通過：483 個電氣腳號／484 個編號銅焊盤（DPAK 腳與 tab 共用 2）、120 nets 與原理圖及接線契約吻合。符號 UUID、關鍵封裝腳位、通孔阻焊開口、焊盤位於板內均檢查；幾何／封裝 DRC 0 違規，**仍有 364 項未連接**，保留在 `drc.json`，不能稱為完整製造 DRC 通過。KiCad 10.0.6 獨立 Python API 對舊式 THT 封裝寫出阻焊層有差異，生成器已在原生檔案宣告中補回，驗證會重新載入確認；不得移除此檢查。

使用方式圖解僅更新文件與預覽，未改電路；檢查 SVG 格式、中文排版及文件連結，不重跑電路模型。

## 下一步

機箱仍優先現成鋁機箱＋客製面板，但需因機內電源重排。原 TAKACHI HY88-28-23／Hammond 1455U2801 小型候選尚未通過；UHP-200 本體雖小，其指定散熱底板參考為 300×300×3 mm，需審查降額或換用適合的電源／機箱。不得只看本體尺寸就宣稱裝得下。V0.1 空間圖仍保留歷史。

市電入口、交流保險絲／雙極總開關、湧流與端子防觸碰、機殼 PE 固定、12V 入口保護均未完成；R608 不是保護接地導體。原廠資料已核對並附來源，但整機配線、絕緣、EMI、噪聲與熱驗證尚未完成。市電裝配與初次上電需具相應經驗的人員檢查。

1. 驗證 PFFB 在實際 TPA3255、運放頻寬、電感容差與開路／不同喇叭負載下的穩定裕度。不可憑目前 AC 模型直接製板。
2. 審查 XLR 單電源擺幅／共模範圍、配對電容及訊源阻抗影響、REF 雜訊、上電偏壓建立與插拔／切換靜音；選 XLR 母座與後板佈局。
3. 確認 Z10 Trigger 電壓、極性與帶載能力，驗證正常及突然掉電時序；關機 RC 的 0.071–0.983s 是工程包絡，不是保證閾值。
4. 核定 48V 穩壓供電、12V 輸入保護、保險絲協調、eFuse／反接二極體散熱、電感磁芯損耗、其他料號與全部 footprint。
5. 以現有 PCB 配置為起點；定料後回填原理圖 Footprint，核對與板檔同步方式，再逐區佈線與覆銅，同步安排機箱、散熱器和面板線束。預留 XLR、RCA、絕緣 Trigger 與 AUTO／OFF／ON 操作介面。

## 工具與更新方法

本機已有 KiCad 10.0.6、kicad-library、ngspice 47、rsvg-convert；尚未安裝 OpenSCAD／FreeCAD。原廠資料表暫存在 `/tmp/tpa3255-reference`，持久連結列於設計文件，未將原廠 PDF 放進儲存庫。

```sh
python3 tools/verify_v03.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03.kicad_sch
python3 tools/verify_pcb_draft.py
python3 tools/export_pcb_draft.py
```

`tools/build_schematic_v03.py` 可重建 V0.3 初始圖面，但會覆寫專案、八頁圖面、符號庫及預期接線表；人工修改後避免直接執行。更改生成器後需審查新接線，再驗證／匯出。KiCad 10 `sym-lib-table` 必須保留標準多行格式。

舊 `tools/build_schematic.py`／`verify_electrical.py` 僅處理 V0.2；匯出工具未給參數時亦保留 V0.2 行為。

`tools/build_pcb_draft.py` 只生成初始配置；已有板檔時預設拒絕覆寫，`--force` 會丟棄人工改動。正式接續 PCB 工作前先讀草案 README，避免重新生成覆寫。`Placement.pretty` 內 DO-35 衍生封裝沿用 KiCad CC BY-SA 4.0 與附加例外，附授權文件；其餘專案自訂占位沿用 MIT。
