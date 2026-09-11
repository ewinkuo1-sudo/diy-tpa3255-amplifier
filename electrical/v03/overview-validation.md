# 整合電路圖檢查

- KiCad 10.0.6；A0 橫式、單一原生頁面，無子頁；依訊號與控制路徑重新排列。
- 180 個元件的編號、數值、Footprint／Datasheet、單元與符號 UUID 均與八頁來源一致。
- U1／U601 使用獨立 Overview 圖形庫調整腳位排列；逐腳核對編號、名稱、電氣型態與所屬單元，其餘符號沿用原庫。
- 483 個電氣腳位、120 個網路群組與八頁來源及 `expected-connections.csv` 完全吻合。
- 額外移除所有標籤再匯出接線表：79 組音訊、四路回授及主要啟停控制網路仍完整相連，確認依靠實際導線連接。
- 保留自訂標籤文字；改用單頁局部標籤，匯出名稱增加 `/` 前綴；以腳位群組比較確認等價。
- 八頁來源及單頁總圖 ERC 均為 0 錯誤／0 警告，無排除項目；UUID 無重複。
- `overview-sources.json` 記錄來源及總圖 SHA-256；來源變動而未重建時，檢查會失敗。

只調整圖面排版，未改動電路，未新增性能或實機驗證。既有 PCB 仍對應八頁來源的階層路徑，請從 `tpa3255-v03.kicad_pro` 更新 PCB；單頁版供審閱及衍生編輯。

重建與檢查：

```sh
python3 tools/build_schematic_overview.py
python3 tools/verify_schematic_overview.py
python3 tools/export_schematic.py electrical/v03/tpa3255-v03-overview.kicad_sch --pdf-from-svg --png-width 4800
```
