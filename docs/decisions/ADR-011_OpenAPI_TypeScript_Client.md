# ADR-011：OpenAPI TypeScript Client 產生方式

- 狀態：Accepted
- 日期：2026-08-06
- 決策者：開發端，經獨立 Agent 維護性與安全審查
- 相關 Slice：0.9 與所有後續 API／前端 Slice

## 1. 背景

FastAPI OpenAPI 是 request、response 與統一 `ErrorResponse` 的唯一契約來源。前端若手寫 DTO，會在欄位、錯誤狀態或 API version 變更後漂移；但 client generator 也是供應鏈與長期維護依賴，不能只因目前可用就採用。

評估期間先驗證 `openapi-typescript`＋`openapi-fetch`，獨立 Agent 查出官方已宣布 `openapi-fetch` 在 2026 年進入 maintenance mode，因此不採用。`@hey-api/openapi-ts` 雖持續發布，但當時可取得的候選精確版本帶有未修補 high advisory，也不採用。最終採 Orval 8.23.0：MIT、持續發布、支援 OpenAPI→原生 Fetch client，精確鎖版後 `npm audit --audit-level=high` 為 0。

## 2. 決策

1. `scripts/generate-api-client.sh` 對 `backend/scripts/export_openapi.py` 注入固定 test-only 設定並離線匯出 JSON；不啟動 HTTP server，不連接 DB，不讀取正式資料。
2. snapshot 固定排序、UTF-8、兩格縮排與結尾換行，保存於 `frontend/openapi/`。
3. Orval 精確鎖版並產生單一 `frontend/src/api/generated/company-system.ts`；generated 檔案提交 Git 但禁止手改。
4. `npm run api:generate` 更新 snapshot 與 client；`npm run api:check` 在 `mktemp` 目錄重產並逐 byte 比較，任何 drift 都失敗。
5. OpenAPI path 已包含 `/api/v1`；`VITE_API_ORIGIN` 只代表 origin，同源開發預設空字串，禁止再存 API prefix。
6. generated Fetch function 的 non-2xx 由 `frontend/src/api/` 手寫 boundary 拋為 `ApiRequestError`，保留 HTTP status、穩定 error code 與 details，讓 TanStack Query 正確進入 error 狀態；業務程式不得解析 message。
7. UI 只顯示後端已定義的安全 message 或固定中文 fallback；不得顯示 raw fetch、JSON parser、DB 或 Secret 例外。

## 3. 影響與升級規則

- 正面：DTO 不重複、endpoint 與 response union 由 OpenAPI 約束；不用額外 runtime HTTP library。
- 成本：generator 帶來 dev dependency 與 generated diff；FastAPI／Pydantic 版本變更可能改變 snapshot。
- Orval 升級必須是獨立切片：先查授權、維護狀態及 advisories，再重產、review diff、跑完整型別／API／UI 測試。
- Python dependencies 目前仍是受控版本範圍而非 bit-for-bit lock；Phase 1 前評估導入 lockfile，期間由 snapshot drift check 防止未察覺契約變更。

## 4. 驗證

- 連續匯出 bytes 完全一致，operationId 唯一且為 snake_case。
- `api:check` 不修改工作樹。
- ready 200、503 envelope、離線、非 JSON 500、未知錯誤與敏感字串負向測試。
- 首頁 loading／ready／error／retry 與 axe、鍵盤、RWD 驗收。
- lint、typecheck、production build 與 `npm audit --audit-level=high` 通過。
