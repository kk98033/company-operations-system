# ADR-022：Session 公司範圍契約

- 狀態：Accepted
- 日期：2026-08-09
- 決策者：開發端，依 ADR-005 與 Slice 1.7 A／B 公司 PostgreSQL 驗證
- 相關 Slice：Phase 1 Slice 1.7、所有後續業務 Slice

## 1. 背景

第一家公司採獨立部署，但所有業務資料仍保存 `organization_id`。只在 Router 檢查一次公司或讓每個 service 自行處理，容易出現漏加 WHERE、先查到 B 公司資料才在 Python 拒絕、或信任 body `organization_id` 的越權漏洞。第一版尚不啟用 PostgreSQL RLS，因此需要一個所有後續業務模組都能重用且可測試的 application scope。

## 2. 決策

1. `OrganizationScope` 只能由 `require_organization_scope` 從已驗證 active Session 建立，包含 organization、membership 與 actor user。request body、query、header 或前端部署設定都不能覆蓋。
2. SELECT、UPDATE 與 DELETE 必須呼叫 `scope.constrain(statement, model=Model)`，由 model 的 `organization_id` 加入 predicate。缺少 organization contract 的 model 直接視為 application error。
3. CREATE request schema 不接受 `organization_id`；service 使用 `scope.create_values()` 注入。application code 若自行傳入該欄位，在執行 SQL 前拒絕。
4. 跨資源關聯先以 `require_same_organization()` 拒絕，再由可行的 organization 複合外鍵保護資料庫完整性。
5. 單筆 ID 屬於別家公司與真正不存在使用相同 not-found 語意，不向 client、error details 或 log 揭露另一家公司資料。
6. 每個後續 domain 至少保留一組 A／B 公司讀取與寫入拒絕測試；Slice 1.7 的共用 primitive 測試不能取代各 domain 驗收。
7. 本 Slice 不新增 migration 或 RLS。共用 SaaS 前依 ADR-005 啟用 PostgreSQL RLS，並使用非 owner、無 `BYPASSRLS` 的應用程式角色。

## 3. 結果

- 公司 context 有單一可信來源，CREATE 與 query/update 使用不同但明確的安全 primitive。
- A 公司猜到 B 公司 UUID 時，查不到也改不到；拒絕不依賴 UI 隱藏。
- 後續 service 仍必須明確接收 scope，code review 與 domain 測試可辨識是否漏用。
- application scope 不是 RLS；DB 管理者或繞過 application 的直接 SQL 仍需運維權限與未來 RLS 保護。

## 4. 必要驗收

- body、query、header 提供其他 organization 時，dependency 仍只回 Session 公司。
- A scope 查 B row 回空；更新／刪除 B row 影響 0 筆且不改內容。
- 新 row 由 scope 注入 A organization；caller override 在 SQL 前失敗且不留部分資料。
- scope error 不含 A／B organization UUID 或名稱。
- 每個業務模組在正式 API Slice 重跑 A／B read/write fixture。
