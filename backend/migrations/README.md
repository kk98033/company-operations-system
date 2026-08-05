# Database migrations

這個目錄只管理新系統 schema 的可還原版本。`0001_empty_baseline` 是 Slice 0.5 的空白基線，不建立業務表、Import staging schema 或 seed data。

所有 migration 必須同時實作 `upgrade()` 與 `downgrade()`，並先在隔離的 test PostgreSQL 執行 `upgrade -> downgrade -> upgrade`。應用程式啟動不會自動執行 migration。

Alembic 由 `app.core.config` 取得經環境隔離驗證的 DSN；不可把連線字串或密碼寫入 `alembic.ini`、migration 或 log。
