# Database migrations

這個目錄只管理新系統 schema 的可還原版本。`0001_empty_baseline` 是 Slice 0.5 的空白基線；`0002`／`0003` 是 Import infrastructure；`0004_identity_foundation` 建立公司、使用者、公司成員與 session schema，但不建立 seed、登入行為、角色或權限。

所有 migration 必須同時實作 `upgrade()` 與 `downgrade()`，並先在隔離的 test PostgreSQL 執行 `upgrade -> downgrade -> upgrade`。應用程式啟動不會自動執行 migration。

Alembic 由 `app.core.config` 取得經環境隔離驗證的 DSN；不可把連線字串或密碼寫入 `alembic.ini`、migration 或 log。
