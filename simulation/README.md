# V0.2 區塊模擬

由 `python3 tools/verify_electrical.py` 從 KiCad 匯出接線表產生，使用 ngspice 47。

| 檔案 | 範圍 | CSV first / second |
|---|---|---|
| `input-ac.cir` / `input-ac.csv` | 左右輸入級 AC，理想有限增益運放 | 左聲道 / 右聲道的晶片輸入差動電壓 |
| `filter-ac.cir` / `filter-ac.csv` | 左聲道 BTL 輸出濾波，4Ω 和 8Ω 比較 | 4Ω / 8Ω 的差動電壓 |

CSV 頻率單位 Hz，電壓是相對 1V AC 激勵的複數結果。數值不是 THD、噪音、熱或實機性能。模型與假設見 [設計說明](../docs/V0.2_電路設計.md)，摘要見 [驗證報告](../electrical/validation.md)。

在本目錄可用 `ngspice -b input-ac.cir` 或 `ngspice -b filter-ac.cir` 重跑，生成 `.dat`。正式 CSV 與驗證報告由根目錄的驗證腳本統一更新。
