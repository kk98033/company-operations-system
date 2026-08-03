# Infrastructure

本目錄將保存：

- 本機及正式 Compose。
- Caddy 設定。
- GCE 部署腳本與文件。
- PostgreSQL、附件及快照備份工具。
- 還原與驗證工具。
- 健康檢查及監控設定。

正式環境要求：

- 對外只開 80／443，80 轉 HTTPS。
- PostgreSQL 不公開。
- Secret 不進 Git。
- 客戶公司持有 Google Cloud project、網域及付款資料。
- 附件使用私人 Cloud Storage。
- 備份必須通過乾淨環境還原，不只檢查檔案存在。
