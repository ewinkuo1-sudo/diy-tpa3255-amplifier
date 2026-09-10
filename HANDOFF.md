# TPA3255 接班進度

更新：2026-09-10，Codex。儲存庫 `ewinkuo1-sudo/diy-tpa3255-amplifier`；本機 `~/.openclaw/workspace/diy-tpa3255-amplifier`。

## 使用者方向與同步約定

AI 應用課程，可含電路、材料與 3D 設計；期限、預算、設備未定。Purifi 在另一獨立專案。
使用者要求每次完成並檢查後立即 commit / push 並回報；圖面一併提供首頁可看的預覽。推送前確認遠端進度，不覆寫其他協作者的提交。

## 目前成果：V0.2 原理圖草案

- `electrical/tpa3255-v02.kicad_pro`：KiCad 10 專案，四頁原理圖（功率級、RCA 輸入、供電去耦、手動控制）。
- `electrical/README.md`：PNG、SVG 與四頁 PDF 看圖入口，首頁已放 RCA 圖。
- `electrical/Project.kicad_sym`：自建元件符號。U1 44-pin 已對照原廠圖面；BST 及重複功率輸出腳採 passive ERC 類型，另以 netlist 檢查連接。
- `electrical/bom-draft.csv`：94 個元件的草案，全部 footprint 尚未定案；F1、功率元件額定與料號仍待選。
- `simulation/`：由實際 KiCad netlist 建立的輸入級及 LC AC 模型、數據；不是 TPA3255 開關模型。
- `docs/V0.2_電路設計.md`：來源、設計選擇、限制與後續工作。
- 機殼仍是原 V0.1 占位模型，尚未依實際零件重新配置。

## 驗證

`python3 tools/verify_electrical.py` 通過：KiCad 10.0.6 ERC 0 錯誤／0 警告（無排除）；94 元件、246 腳、56 nets 群組完全吻合預期；主／輔助電源、模式、bootstrap、內部穩壓與重複輸出腳已核對。ngspice 47 區塊模型與 RESET 漏電／電阻餘裕核算通過。

RCA 目標靈敏度約 2.106Vrms（理想前端 + 晶片典型增益，未含 LC 損耗）。目前 LC 的 8Ω / 20kHz 為 +0.809dB，待調整；每顆電感 DCR 0.05Ω 是模型假設。

已檢視四頁 KiCad 圖面輸出。尚無 PCB、DRC、Gerber、元件封裝、整機 THD／EMI／熱或實測。

## 下一步

1. 調整 LC／確定頻響驗收，選定電感（含偏磁後電感、過流門檻與熱）及輸出電容。
2. 完成自動供電監測、啟停及掉電靜音；現有 JP1 為實驗手動控制，不能保證 brownout 靜音。
3. 設計電源輸入保護、湧流處理，選 F1、接頭與實際料號。
4. 核對 footprint 與散熱器，再進入 PCB 與機構；目前不應直接製板。

## 工具與更新方法

本機已安裝 KiCad 10.0.6、kicad-library、ngspice 47；尚未安裝 OpenSCAD / FreeCAD。原廠資料表本機暫存於 `/tmp/tpa3255-reference`，持久來源連結列於設計文件。
`tools/build_schematic.py` 可重建初始原理圖，但會覆寫 `.kicad_pro`、四頁圖面、自建符號與預期接線表；手動修改後使用 `tools/verify_electrical.py` 檢查並匯出，更新接線基線需另行審查。
KiCad 10 的 `sym-lib-table` 採標準多行格式；壓成單行曾導致 library type UNINITIALIZED。`tools/export_schematic.py` 同步匯出 PDF、SVG、PNG 並整理行尾空白；指令見看圖入口。
