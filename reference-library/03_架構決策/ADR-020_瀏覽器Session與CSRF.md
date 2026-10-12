# ADR-020：瀏覽器 Session 與 CSRF

- 狀態：Accepted
- 日期：2026-08-09
- 決策者：開發端，經兩位獨立 Agent 安全與 migration 審查
- 相關 Slice：Phase 1 Slice 1.4～1.5

## 1. 背景

Slice 1.3 先以一次性 JSON Bearer transport 驗證 server Session 的建立、解析與撤銷，但正式 React 網頁不可把 raw token 暴露給 JavaScript 或保存至 Web Storage。改用瀏覽器 Cookie 後，瀏覽器會自動夾帶憑證，因此必須同時處理 CSRF、來源偽造、Cookie 注入與 production HTTPS 降級風險。

## 2. 決策

1. raw 256-bit Session token 只放入 host-only `company_system_session` Cookie；使用 `HttpOnly`、`SameSite=Strict`、`Path=/api/v1`，不設定 Domain、Max-Age 或 Expires。production 固定 `Secure`，development／test 才允許本機 HTTP。DB 的固定 8 小時到期仍是 server 權威上限。
2. `company_system_csrf` 是 React 可讀、`Path=/` 的 Cookie；它不含 raw Session，而是 `base64url(HMAC-SHA256(CSRF_HMAC_KEY, "csrf-v1\\0" + session_digest))`。unsafe request 必須同時提供 Cookie 與 `X-CSRF-Token`，先 constant-time 比對兩值，再核對伺服器簽章及 Session binding。
3. `CSRF_HMAC_KEY` 是至少 256-bit 的必要 Secret；無預設、範例值、錯誤訊息與 repr 不得洩漏。輪替會使既有 CSRF token 失效並要求重新登入；第一版不做多 key rotation。
4. `APP_PUBLIC_ORIGIN` 是單一完整 origin。登入、登出及後續所有 Cookie-auth unsafe method優先 exact-match Origin；Origin 缺少時才解析 Referer origin fallback。兩者都缺少、`null`、多值、userinfo、scheme／host／port不符或 suffix spoof 一律 fail closed。
5. 系統維持前後端同源與 Vite `/api` proxy，不加入寬鬆 CORS，也不從 Host 或 forwarded header 推導可信來源。
6. 登入 JSON、OpenAPI 與 generated client 移除 `session_token`、`token_type`、Bearer與 Authorization。只有 Cookie-only current Session dependency在本 Slice 建立；載入目前使用者 endpoint 與 React 登入頁留在 Slice 1.5。
7. 登出在有格式正確 Session Cookie 時必須先通過 signed CSRF，成功撤銷 DB Session後才清 Cookie。沒有或畸形 Session Cookie 視為已登出並清理；已撤銷、過期或未知但格式正確的 Session在提供正確 bound CSRF 時同樣回 204。資料庫失敗不得先清 Cookie。

## 3. 結果

- XSS 仍須由輸出編碼與 CSP 等措施防護，但一般 React JavaScript無法直接讀取 raw Session token。
- SameSite 只作 defense-in-depth；主要 CSRF 防線是 exact source check 與 server-signed、Session-bound token。
- 關閉瀏覽器會移除 client credential；重新整理分頁仍可登入，最長不超過 server Session 到期。
- 未新增 migration、CSRF DB 欄位或第三方安全套件；既有 `sessions.token_digest` 足以安全綁定。

## 4. 必要驗收

- development／production Cookie attributes、兩個 path、set／delete policy逐項測試。
- raw token 不進 JSON、OpenAPI、generated client、DB、log 或錯誤內容。
- forged matching token、跨 Session token、錯 key、缺 Cookie／Header全部拒絕。
- missing／foreign／null／多值 Origin，以及錯 Referer、port、scheme、suffix全部拒絕且不執行登入或撤銷。
- 正常登出、重送、未知／過期／已撤銷 Session與 DB failure皆維持已定交易及 Cookie清理順序。
