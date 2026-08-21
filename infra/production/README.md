# 正式環境基線

本目錄只保存可提交 Git 的部署與復原契約，不保存任何 Secret、正式帳密、DSN、憑證或備份檔。

- `backup-inventory.json` 是 Phase 11.6 的機器可讀 inventory。
- 同一份程式 release 可提供 A、B 公司，但每家公司使用獨立 project／部署、資料庫、object storage、Secret 與備份。
- 目前沒有建立或計費任何雲端資源；真正 provisioning 留在 Phase 11.8，備份工作與還原演練留在 11.9～11.12。
- inventory 的 RPO／RTO 是目標，不是已達成結果；只有乾淨環境還原報告可把它改成 achieved。

完整決策與成本 Gate 見[正式部署與備份基線](../../docs/正式部署與備份基線.md)。
