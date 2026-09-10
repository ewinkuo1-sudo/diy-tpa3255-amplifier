# TPA3255 接班進度

更新：2026-09-10，Codex。

儲存庫：`ewinkuo1-sudo/diy-tpa3255-amplifier`。本機：`~/.openclaw/workspace/diy-tpa3255-amplifier`。

## 使用者方向

課程主題是用 AI 做任何事情，可包含 PCB、材料選用與 3D 設計；尚未表示老師強制要求實機。本專案為自畫 TPA3255 練習機；Purifi 自用主力後級已拆至另一儲存庫。期限、預算、設備未定。

## 提交與同步約定

使用者於 2026-09-10 明確要求：之後每次完成並檢查過的專案變更，立即 commit 並 push 到 GitHub，不需再次詢問。推送前確認遠端進度，保留其他協作者的提交；推送後確認同步成功並回報 commit。若推送失敗，明確回報尚未同步。

## 本輪成果

- `docs/V0.1_設計規格.md`：暫定 48V 外接電源、雙 BTL、先以 2×50W/8Ω 為目標，全部仍待驗證。
- 修正 `docs/01_電路設計.md` 中供電／增益等會誤導原理圖的描述；完整審查尚未結束。
- `tools/power_budget.py` 與生成報告：可重算的理想需求估算。
- `mechanical/enclosure-concept.scad`：參數化空間草案，未渲染、未驗證加工。
- 新增 `mechanical/README.md` 看圖入口與 PNG／SVG 投影預覽，首頁已嵌圖。`tools/enclosure_preview.py` 讀取 SCAD 的尺寸產生矩形空間配置示意，不是 OpenSCAD 渲染；幾何形狀改動時需同步更新腳本。

## 下一步

1. 工具盤點：PATH 中未找到 kicad-cli、ngspice、FreeCAD/freecad、openscad；尚未安裝。
2. 完整閱讀 TI 的 Typical Application 與 Layout Guidelines，對照原始 PDF 圖面核對符號腳號；PDF 文字擷取順序不可直接轉成 netlist。
3. 建立 KiCad 原理圖，先確定供電、模式與控制，再做前端和濾波。
4. 取得實際料號與尺寸，回填 BOM 與機構模型。
5. `docs/00_專案總覽.md` 保留的舊預算與性能比較尚未重核。V0.1 目標不是已驗證性能。

## 完成度邊界

驗證完成：`git diff --check` 通過；50W/8Ω 的電壓、電流、功率平衡與生成報告一致性核對通過。此為計算核對，非硬體測試。

尚未做 SPICE、ERC、DRC、PCB、Gerber、實體測試或下單。BTL 保護不能直接沿用其他拓撲；機構占位尺寸不能當實際料件尺寸。
