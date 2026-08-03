# Backend

預定使用 FastAPI＋SQLAlchemy 2＋Alembic＋PostgreSQL，負責權限、狀態、交易、流水、附件授權、文件快照與舊資料匯入。

目前尚未初始化框架。依計畫 Slice 0.1～0.5 建立後，業務模組必須逐個垂直實作與驗證。

核心規則：

- organization scope 由可信 session 注入。
- 核心數量及金額只由後端與資料庫保護。
- 高風險操作使用明確 command，不提供任意 status PATCH。
- 完工、出貨、計價、請款及收款在明確交易內處理。
- 作廢／沖銷保留原紀錄與 audit。
- 正式資料不進 seed 或測試 fixture。
