# TPA3255 接班進度

更新：2026-09-11，Codex。儲存庫 `ewinkuo1-sudo/diy-tpa3255-amplifier`；本機 `~/.openclaw/workspace/diy-tpa3255-amplifier`。

## 使用者方向與同步約定

AI 應用課程，可含電路、材料、PCB 與 3D 設計；期限、預算、設備未定。前級為 Eversolo DAC-Z10，喇叭為 Usher BE-718，初期目標 2×50W / 8Ω。Purifi 在另一獨立儲存庫。

使用者要求每次完成並檢查後立即 commit / push 並回報，首頁同步可看的圖面。推送前確認遠端進度，不覆寫其他協作者。最近要求由設計端選電感、處理 PCB 注意事項、配合 Z10 Trigger 自動開關，並補上 XLR。

## 目前成果：V0.3 原理圖草案

- `electrical/v03/tpa3255-v03.kicad_pro`：八頁原理圖，依序為功率級、訊號驅動、類比供電、PFFB、Trigger、主電源開關、控制供電、XLR 輸入。
- `electrical/v03/README.md`：八頁 PNG／SVG／PDF 看圖入口；首頁放 XLR 頁。180 個元件，全部 footprint 尚未指定。
- `docs/V0.3_設計說明.md`：元件來源、訊號路徑、控制方式與限制；`docs/V0.3_PCB設計要求.md` 為下階段佈局要求。
- L1–L4 選 Coilcraft MA5172-AE：10µH，25°C 最大 DCR 26mΩ；45A 是典型 10% 電感下降條件，不是連續額定。
- 四路同臂 PFFB 採 TI SLAA788A TPA3255 範例起始值，SUM 在 AC 耦合前；輸出阻尼為 220nF + 1Ω，NE5532 回授補償 330pF。真實穩定裕度尚未驗證。
- XLR：U601 INA2137UA，實體 SOIC-14 腳位，約 0.5 倍差動接收；U602 兩個 NE5532 跟隨器提供低阻抗 REF。正負線各串 47Ω／0.1% 與 47µF BP，按聲道配對電容到 1%；輸出再隔直流。R607／C609 獨立濾波 12V 支路，C607／C608 本地去耦。
- J603／J604 各裝一個跳線帽：兩個都接 2–3 選 XLR，兩個都接 1–2 選 RCA，預定初裝 XLR。切換先將 J302 設為 OFF 待機；尚無面板切換／切換靜音電路。
- XLR pin 1／金屬外殼接 CHASSIS，R608 單點接 GND；RCA 插座絕緣。Trigger 的 TRIG_RETURN 維持隔離。
- Trigger 以 12V 名義、9–15V、tip 正／sleeve 負為待實測假設。Z10 手冊確認有 Trigger，但缺少完整電流、電平容差與極性資料。12V 設計負載約 1.6mA，不能引用其他機種 150mA 當成 Z10 規格。
- J302 外接 AUTO／OFF／ON 的 SPDT 中心斷開開關。TPS3808 監測輔助電源與 PVDD；開機先升功率電源，再延遲開聲；關機先 RESET 靜音，再延後停止 eFuse。
- 主電源以 TPS26631PWPR 切換、STPS5H100B 反接保護。eFuse 約 4.5A 名義限流，MODE 懸空選鎖定，軟啟動名義約 2.2s；F1 為 T5A／至少 80VDC 的規格占位，尚未選料號／協調曲線。
- 關機為待機：只切功率級 48V；外部電源及 12V 類比／控制仍有電。功率電容不會立即放空，不是市電隔離。
- V0.2 圖面與模型保留於 `electrical/`、`simulation/` 上層，作為歷史基線。機殼仍是 V0.1 占位模型，尚未按電感／XLR／散熱器重新配置。

## 驗證

`python3 tools/verify_v03.py` 通過：KiCad 10.0.6 ERC 0 錯誤／0 警告（無排除）；180 元件、482 腳、119 nets 群組吻合預期，另以獨立實體腳位檢查 XLR、PFFB、電源及控制。

ngspice 47 執行 12 組 RCA／XLR AC 模型（4Ω、8Ω、空載 × 功率級無限頻寬／自訂 100kHz 極點）與 2 組共模模型。50W/8Ω 名義靈敏度約 RCA 2.126Vrms、XLR 差動 4.268Vrms；按 Z10 2.5／5Vrms 驅動，三個檢查頻率的輸出差異均小於 0.1dB。

7 個控制時序規格模型涵蓋正常開關、任一電源缺失、5ms Trigger 脈衝、主／輔助電源掉壓與 eFuse 鎖定。腳位與阻容核算支持設計邏輯，不能當成實際半導體暫態驗證。數據及原始模型位於 `simulation/v03/`。

運放及 INA2137 內部比例仍理想化，TPA3255 只有線性增益源，100kHz 極點是自行假設；未驗證 PWM 延遲、真實 CMRR、噪聲、THD、迴路穩定裕度或偏壓建立爆音。已檢視圖面預覽；尚無 PCB、DRC、Gerber、整機 EMI／熱或實測。

## 下一步

1. 驗證 PFFB 在實際 TPA3255、運放頻寬、電感容差與開路／不同喇叭負載下的穩定裕度。不可憑目前 AC 模型直接製板。
2. 審查 XLR 單電源擺幅／共模範圍、配對電容及訊源阻抗影響、REF 雜訊、上電偏壓建立與插拔／切換靜音；選 XLR 母座與後板佈局。
3. 確認 Z10 Trigger 電壓、極性與帶載能力，驗證正常及突然掉電時序；關機 RC 的 0.071–0.983s 是工程包絡，不是保證閾值。
4. 核定 48V 穩壓供電、12V 輸入保護、保險絲協調、eFuse／反接二極體散熱、電感磁芯損耗、其他料號與全部 footprint。
5. 完成以上審查後進入 PCB 與機構，預留 XLR、RCA、絕緣 Trigger 與 AUTO／OFF／ON 操作介面。

## 工具與更新方法

本機已有 KiCad 10.0.6、kicad-library、ngspice 47、rsvg-convert；尚未安裝 OpenSCAD／FreeCAD。原廠資料表暫存在 `/tmp/tpa3255-reference`，持久連結列於設計文件，未將原廠 PDF 放進儲存庫。

```sh
python3 tools/verify_v03.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03.kicad_sch
```

`tools/build_schematic_v03.py` 可重建 V0.3 初始圖面，但會覆寫專案、八頁圖面、符號庫及預期接線表；人工修改後避免直接執行。更改生成器後需審查新接線，再驗證／匯出。KiCad 10 `sym-lib-table` 必須保留標準多行格式。

舊 `tools/build_schematic.py`／`verify_electrical.py` 僅處理 V0.2；匯出工具未給參數時亦保留 V0.2 行為。
