# 資安、Session、稽核與備份計畫

> 文件版本：v1.2
> 日期：2026-08-21
> 狀態：Session 上限、管理 UI、安全事件與敏感讀取 audit 已完成；access log 與正式備份於後續 Slice 驗收

## 1. 現況結論

目前已完成 Argon2id、HttpOnly Cookie、SameSite、CSRF、可信 Origin、八小時 server Session、登入失敗限制、公司隔離、exact capability、Request ID、append-only 業務 audit 與敏感資料遮罩。

目前 Session 政策、管理與 11.4 事件完整性已完成，仍有兩個明確缺口：

1. 登入、登出、Session 取代／撤銷、權限拒絕與五類敏感讀取已由 Request ID 關聯；每個普通 HTTP request 的 structured access log、CSRF／Origin 拒絕與 5xx／慢請求查詢仍待 11.5。
2. 資料庫、附件、列印快照與 Secret 備份目前只有設計，尚未有可執行、自動告警及乾淨環境還原證據。

## 2. 帳號與多人登入政策

### 2.1 個人帳號

- 每位員工使用獨立帳號，禁止多人共用帳號或密碼；多人同時工作是多個帳號並行，不是共用一個帳號。
- 操作者離職、調職或停用時撤銷該 membership 的所有 Session，不刪除歷史 audit。
- 自動程式若未來需要帳號，使用不可互動登入的 service identity，不冒用員工帳號。

### 2.2 同帳號 Session

第一版每個 organization membership 只允許一個未撤銷互動 Session：

1. 新登入在同一資料庫交易鎖定 membership。
2. 密碼與狀態驗證成功後，撤銷該 membership 其他未到期 Session。
3. 建立新 Session、更新最後登入時間，並保存 `session.replaced`／`login.succeeded` 安全事件。
4. 舊瀏覽器下一次 request 收到統一 401，前端顯示「此帳號已在其他裝置重新登入」並回登入頁。
5. 不以覆蓋 Cookie 假裝撤銷；伺服器資料庫必須讓舊 token 真正失效。

若公司後續證明同一員工確實需要桌機與行動裝置並存，必須另立 ADR、風險與並行測試後才可改變上限；不得設定無上限。11.3 已讓使用者查看自己的登入歷史；`sessions.manage` 可查看目前公司尚未撤銷且未到期的 Session，附原因撤銷單一或該 membership 全部 Session。裝置欄只保存不含版本的瀏覽器／平台摘要，不保存 raw User-Agent 或 token。

## 3. 三層日誌，不把所有內容塞進同一張表

### 3.1 業務 audit（PostgreSQL、不可變）

保存會改變公司事實或取得敏感資料的動作：新增、修改、確認、取消、作廢、沖銷、權限／帳號異動、Import apply、附件／PDF／CSV 匯出下載、備份／還原管理操作。寫入與成功業務交易同 transaction；資料庫禁止一般 UPDATE／DELETE。

必要欄位：公司、user、membership、session reference、action、entity、文件號、結果、原因、必要 before／after、Request ID、時間。before／after 只保存必要欄位並雙重遮罩。

### 3.2 認證與資安事件（append-only）

保存登入成功／失敗／受限、登出、Session 取代、遠端撤銷、帳號／角色停用、CSRF／Origin／權限拒絕、備份失敗及重要設定變更。11.4 已完成目前 API 存在的登入、登出、Session 與權限事件；帳號停用 command、CSRF／Origin 的 request 級證據及備份事件分別由後續管理 API、11.5 與 11.9～11.12 接續。失敗事件不可依賴已 rollback 的業務 transaction 才寫入。

成功登入後可以保存 actor 與 Session reference；未知帳號登入失敗仍只保存 HMAC 指紋，不保存輸入帳號或密碼。來源網路只保存經正式 proxy 邊界取得的 HMAC 指紋；User-Agent 保存正規化摘要與 hash，不保存 Cookie 或 token。

### 3.3 HTTP access／application log（集中式結構化 log）

每個 request 保存 timestamp、Request ID、route template、method、status、duration、response size、organization／user／membership／session reference（已登入時）、來源與 User-Agent 指紋及錯誤類別。不得保存 request／response body、query 中的敏感值、Authorization、Cookie、CSRF、密碼、Secret、附件內容或完整 DSN。

這一層涵蓋查詢操作，但不把每次列表翻頁寫進 `audit_logs`。敏感讀取，例如下載附件、匯出 CSV、讀 audit、產生／下載正式 PDF，仍另寫業務 audit。

### 3.4 保存與查詢

- access／application log：建議線上 90 天，之後依容量加密封存或刪除。
- auth／security event：建議線上 180 天並保留至少一份加密封存。
- 業務 audit：跟正式業務文件保存年限一致；第一版先不自動刪除。
- 正式保存年限須由公司與會計／個資政策確認，不能只由程式自行決定。
- log 查詢需要獨立 capability；查詢本身也留下 audit。所有 log 依公司隔離且不可由一般使用者修改。

## 4. 備份範圍

一份可還原備份必須同時包含：

1. PostgreSQL schema、正式資料、audit、安全事件及 Import mapping。
2. 私人附件與不可變 PDF／列印快照，含 object manifest、size、SHA-256 與版本。
3. migration 版本、程式 Git commit／tag、production image digest 與非秘密設定。
4. Secret 名稱、版本與重建／輪替手冊；Secret 值不進 Git 或普通備份包。
5. 備份 manifest、建立時間、來源環境、加密方式、雜湊及還原相依版本。

## 5. 建議正式部署方案

### 5.1 推薦：Managed PostgreSQL

- App 放 GCE／等價主機；PostgreSQL 改用 Cloud SQL PostgreSQL。
- 開啟 automated backup 與 PITR；每天另產生可攜式 `pg_dump --format=custom` 加密備份。
- 附件使用私人 Cloud Storage，啟用 object versioning／retention，DB metadata 與 object manifest 每日對帳。
- Secret 使用 Secret Manager、最小 IAM、固定版本部署與輪替，不把 production `.env` 備份到 Git。

優點是 PITR、備份與磁碟故障處理較可靠；缺點是月費較高。這是正式公司資料的建議方案。

### 5.2 預算方案：VM 自管 PostgreSQL

- 使用 `pg_basebackup`＋WAL archive／成熟工具（例如 pgBackRest），不能只依賴每四小時 `pg_dump`。
- WAL、base backup 與每日 logical dump 加密傳到不同帳號／bucket；VM 磁碟快照只作輔助。
- 需要自行監控 WAL 中斷、空間、backup age、restore 失敗及 PostgreSQL 版本相容性。

只有完整還原演練穩定通過，才可採此省成本方案。

## 6. 備份頻率與恢復目標

- 採 3-2-1：正式資料加兩份備份、至少兩種媒體、至少一份異地；另保留一份公司可控制的離線／不可變副本。
- Managed 方案目標 RPO 不超過 15 分鐘、RTO 不超過 4 小時；自管方案若未做連續 WAL，RPO 不得宣稱優於最近一次成功備份。
- 每日自動備份、每週公司持有的加密副本、每月離線副本；高風險 migration、Import apply 與正式切換前建立具名 restore point。
- 每日自動驗證檔案存在、大小、雜湊、解密與 catalog；每月至少還原 DB 到隔離環境，每季做 DB＋附件＋Secret＋程式的完整乾淨環境演練。
- 備份失敗、超過時效、雜湊錯誤、物件缺檔或還原失敗必須通知維護者，不能只留下 log。

## 7. 實作順序與 Gate

1. Session 單一登入政策、同交易取代、本人／公司清單、遠端撤銷、公司隔離及管理 UI 已完成。
2. 下一步補齊認證／Session／權限事件，audit 加入 Session reference 並建立 completeness matrix。
3. HTTP structured access log、可信 proxy、遮罩、集中保存與告警。
4. 備份 inventory、加密、manifest、DB／附件工具與錯誤告警。
5. 從乾淨環境實際還原並跑登入、客戶、工單、附件、出貨、計價、收款與歷史 PDF smoke。

沒有實際還原報告、RPO／RTO 測量與公司持有的異地副本，不得把「備份已完成」標為 DONE。

## 8. 依據

- OWASP Session Management Cheat Sheet：並行登入政策、有效 Session 檢視／撤銷與活動歷史。
- OWASP Logging Cheat Sheet：安全、操作及業務 audit 分層，保存 who／what／when／where 並排除敏感資料。
- PostgreSQL 17 Backup／PITR 文件：base backup＋WAL 可作 point-in-time recovery，`pg_dump` 提供可攜式 logical backup。
- NIST 備份指引：備份必須建立、維護、測試並納入復原演練。
