# 單頁總圖合併檢查

- KiCad 10.0.6；A0 直式、單一原生頁面，無子頁。
- 180 個元件的編號、數值、符號來源、Footprint／Datasheet 與符號 UUID 均與八頁來源一致。
- 483 個電氣腳位、120 個網路群組與八頁來源及 `expected-connections.csv` 完全吻合。
- 保留自訂網路名稱；KiCad 自動產生的無標籤網路路徑隨合併改變，以腳位群組比較確認等價。
- 八頁來源及單頁總圖 ERC 均為 0 錯誤／0 警告，無排除項目；UUID 無重複。
- `overview-sources.json` 記錄來源及總圖 SHA-256；來源變動而未重建時，檢查會失敗。

只調整圖面排版，未改動電路，未新增性能或實機驗證。既有 PCB 仍對應八頁來源的階層路徑，請從 `tpa3255-v03.kicad_pro` 更新 PCB；單頁版供審閱及衍生編輯。

重建與檢查：

```sh
python3 tools/build_schematic_overview.py
python3 tools/verify_schematic_overview.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03-overview.kicad_sch --pdf-from-svg --png-width 4800
```
