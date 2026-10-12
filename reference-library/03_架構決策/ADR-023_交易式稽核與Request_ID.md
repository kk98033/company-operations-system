# ADR-023：交易式稽核與 Request ID

- 狀態：Accepted
- 日期：2026-08-09
- 決策者：開發端，依 AUD-001、ADR-021／022 與 Slice 1.8 PostgreSQL 驗證
- 相關 Slice：Phase 1 Slice 1.8、所有後續修改型業務 Slice

## 1. 背景

工單、完工、庫存、出貨與帳務的關鍵異動必須知道誰在何時改了什麼、原因為何，且 A／B 公司紀錄不可混用。若業務資料先 commit、稽核再 best-effort 寫入，第二步失敗時會留下不可追溯的異動；若直接保存 request payload，又可能把密碼、Cookie、Token 或附件內容寫進永久紀錄。

## 2. 決策

1. `audit_logs` 屬單一 organization，user actor 必須以 organization＋membership＋user 複合外鍵證明為同公司成員；system actor 必須明確使用空 membership／user。
2. 修改型 application service 在自己的 transaction 內完成業務異動並呼叫 audit service stage event。audit service 不自行 flush／commit；交易成功一起保存，失敗一起 rollback。
3. 稽核資料 append-only。PostgreSQL trigger 拒絕 UPDATE／DELETE；正式 application role 不授予 TRUNCATE、DDL、停用 trigger 或修改歷史紀錄的權限。更正以新增反向／補充事件完成。
4. before／after 只傳必要 allowlisted 欄位。共用遞迴 sanitizer 限制深度、筆數與長度，遮罩 password／hash、Cookie、CSRF、Session、Token、Secret、API／private key、bytes 與檔案內容；唯讀 response 再做一次防禦性遮罩。
5. 每個 HTTP request 由 server 產生新的 UUID Request ID，忽略 client `X-Request-ID`。成功與錯誤 response、結構化 log、audit event 使用同一 ID；未預期錯誤不記 exception message。
6. 稽核查詢只能由 active Cookie Session 且具 `audit.read` 的成員使用，固定套用目前 organization scope、分頁上限與唯讀 API；React 導覽隱藏不能取代後端 403。
7. `event_status=failure` 只供明確定義且能安全持久化的安全事件 transaction。普通業務 command 若 rollback，不能誤稱同一 transaction 中的 failure audit 仍會留下；登入失敗事件留 Slice 1.9 定義。

## 3. 結果

- 關鍵資料不會出現「已修改但無稽核」的交易裂縫。
- A 公司無法查詢或偽造 B 公司 actor；未授權者連 API 都會被拒絕。
- Secret 遮罩有寫入與讀出兩層，但仍要求呼叫端只提供必要欄位，不能把 sanitizer 當成可保存整份 request 的理由。
- Request ID 可把使用者看到的錯誤、server log 與 audit event 關聯，client 不能注入誤導追蹤值。

## 4. 必要驗收

- 同 transaction 的業務異動與 audit 一起 commit／rollback；DB 拒絕 UPDATE／DELETE。
- actor 跨 organization 組合由真 PostgreSQL 外鍵拒絕。
- Secret、hash、Cookie、CSRF、Session、Token、key 與檔案 bytes 不出現在 DB、API response、log 或前端。
- client 傳入 Request ID 時 response 仍使用新的 server UUID；500 response 與安全 log ID 一致。
- `audit.read` allow／deny、A／B 公司 scope、分頁上限、React loading／empty／error／403 及 axe 全部通過。
