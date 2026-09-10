# TPA3255 DIY 立體聲後級

使用 TI TPA3255 自畫電路與 PCB，搭配材料選用、3D 機構與量測，完成一台練習機／備用後級，記錄 AI 協作過程供課堂展示。

## 目前進度

V0.2 已完成四頁 KiCad 原理圖草案、接線核對及輸入／LC 區塊模擬。暫定外接 48V 與 12V、雙聲道 BTL，以 2×50W / 8Ω 為第一階段目標。尚無 PCB、加工圖或實測；手動控制及 LC 仍待下一版完善。

## 電路圖

![V0.2 RCA 輸入級](electrical/preview/tpa3255-v02-input.png)

**[查看全部四頁原理圖](electrical/README.md)** · [下載 PDF](electrical/preview/tpa3255-v02.pdf) · [中文設計說明](docs/V0.2_電路設計.md) · [驗證報告](electrical/validation.md)

## 機殼空間預覽

![V0.1 機殼空間配置草案](mechanical/enclosure-preview.png)

[放大看圖與說明](mechanical/README.md) · [系統方塊圖](docs/V0.1_設計規格.md#系統方塊圖)

綠色為 PCB 占位，橘色為散熱器占位。尺寸仍是假設，尚未驗證加工與散熱。

## 文件

| 文件 | 用途 |
|---|---|
| [V0.2 電路設計](docs/V0.2_電路設計.md) | 供電、輸入級、控制與待確認事項 |
| [音質改善評估](docs/V0.2_音質改善評估.md) | 回授、電感、供電與輸入級的改善優先順序 |
| [BOM 草案](electrical/bom-draft.csv) | 由原理圖匯出，料號／footprint 待選 |
| [V0.1 設計規格](docs/V0.1_設計規格.md) | 系統、選材條件與測試流程 |
| [電路設計筆記](docs/01_電路設計.md) | 已修正的腳位、供電與設計注意事項 |
| [功率估算](docs/V0.1_功率估算.md) | 可重算的需求情境 |
| [原始規劃](docs/00_專案總覽.md) | 歷史成本與構想，待重核 |
| [接班進度](HANDOFF.md) | 下一步與驗證程度 |
| [拆分紀錄](MIGRATION.md) | 舊版本與歷史來源 |

## 下一步

依音質改善評估，先比較濾波後回授（PFFB）與 LC 組合，再決定輸入增益；加入自動電源監測與啟停，完成電源輸入保護及元件選型，再確定 footprint、板形和散熱器。

重新產生計算報告：

```sh
python3 tools/power_budget.py > docs/V0.1_功率估算.md
```

預覽更新方式見 [看圖說明](mechanical/README.md)。
Purifi 主力機位於 [獨立專案](https://github.com/ewinkuo1-sudo/diy-purifi-amplifier)，本專案的檔案與測試不依賴它。

## License

MIT（沿用來源專案的授權聲明）。
