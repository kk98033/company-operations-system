# ADR-025：個人帳號與同帳號 Session

> 日期：2026-08-20
> 狀態：Accepted（第一版每個 organization membership 最多 1 個未撤銷 Session）

## 背景

原本每次登入會建立一個新的八小時 Session，不會撤銷同一 membership 的舊 Session。若多人共用帳號，audit 雖記錄帳號，仍無法辨認真正操作者。

## 決策

1. 每位員工必須有獨立帳號，禁止以共用帳號支援多人同時操作。
2. 第一版每個 organization membership 最多一個未撤銷互動 Session；新登入成功時，在同一交易鎖定 membership、撤銷舊 Session、建立新 Session並留下事件。
3. 使用者可查看自己的 Session，管理者以專用 capability 查看及撤銷公司 Session；停用 user／membership／role 時撤銷相關 Session。
4. 舊 Session 被取代後統一回 401，不揭露新裝置內容；前端只顯示安全說明。
5. 如日後確有同一員工多裝置需求，必須另立 ADR、風險與並行測試後才可改變上限；不得用共用密碼取代帳號建立。

## 驗證

- 兩個不同帳號可同時操作；同一帳號第二次登入會使第一個 Session 失效。
- 並行登入最終只留下 1 個未撤銷 Session，資料庫部分唯一索引阻止服務層被繞過。
- 登入、取代、撤銷、登出與停用皆可由 Request ID、actor、Session reference 追查。
