# ADR-025：個人帳號與同帳號 Session

> 日期：2026-08-20
> 狀態：Proposed（建議預設 1 個有效 Session，待公司確認精確上限）

## 背景

目前每次登入會建立一個新的八小時 Session，不會撤銷同一 membership 的舊 Session。若多人共用帳號，audit 雖記錄帳號，仍無法辨認真正操作者。

## 建議決策

1. 每位員工必須有獨立帳號，禁止以共用帳號支援多人同時操作。
2. 第一版建議每個 organization membership 最多一個有效互動 Session；新登入成功時，在同一交易鎖定 membership、撤銷舊 Session、建立新 Session並留下事件。
3. 使用者可查看自己的 Session，管理者以專用 capability 查看及撤銷公司 Session；停用 user／membership／role 時撤銷相關 Session。
4. 舊 Session 被取代後統一回 401，不揭露新裝置內容；前端只顯示安全說明。
5. 若公司確認同一員工需兩台裝置，可將上限改為 2；不得無上限，也不得以共用密碼取代帳號建立。

## 驗證

- 兩個不同帳號可同時操作；同一帳號第二次登入會使第一個 Session 失效。
- 並行登入最終只留下允許數量的 active Session。
- 登入、取代、撤銷、登出與停用皆可由 Request ID、actor、Session reference 追查。
