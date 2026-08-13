# 公司管理系統翻新專案

> 本檔案是整個專案的主要入口、目前進度與下一步的唯一即時摘要。
> 每次開始工作前必須先讀本 README；每完成一個實作切片，必須先更新本檔案與進度紀錄，再提交 Git。

## 1. 專案目標

將公司目前在 Windows XP 上使用的 PowerBuilder 6 桌面系統，依照公司實際操作流程重做為現代化內部網頁系統。

第一階段在開發者電腦完成 React、FastAPI 與 PostgreSQL 的本機實作及測試；公司驗收後才部署正式環境。系統必須保留舊流程真正需要的功能，同時完成 Gmail 新需求、操作改善、資料追溯、權限、備份及舊資料移轉。

## 2. 開工前必讀文件

文件效力依下列順序排列；內容衝突時，必須先更新上層文件，不可由程式自行猜測：

1. [01_公司流程與新版改進.md](01_公司流程與新版改進.md)
2. [02_最終系統架構.md](02_最終系統架構.md)
3. [03_最終實作計畫.md](03_最終實作計畫.md)
4. [04_開工前確認清單.md](04_開工前確認清單.md)
5. [UI 設計系統與通用版型](docs/UI設計系統與通用版型.md)
6. [程式碼與檔案命名規範](docs/程式碼與檔案命名規範.md)
7. [需求追蹤矩陣](docs/需求追蹤矩陣.md)
8. [Gmail 附件需求逐項對照](docs/Gmail附件需求逐項對照.md)
9. [資料模型與業務規則](docs/資料模型與業務規則.md)
10. [測試與驗收計畫](docs/測試與驗收計畫.md)
11. [舊資料移轉計畫](docs/舊資料移轉計畫.md)
12. [舊系統資料 Import 對照與分批計畫](docs/舊系統資料Import對照與分批計畫.md)
13. [舊資料來源基線報告](docs/舊資料來源基線報告.md)
14. [本機開發與 Git 備份規範](docs/本機開發與Git備份規範.md)
15. [風險與決策紀錄](docs/風險與決策紀錄.md)
16. [詳細實作進度紀錄](docs/progress/實作進度紀錄.md)

原始分析證據保留在專案外層的 `../analysis/` 與 `../extraction/`。新版程式不得直接修改這些原始分析或匯出資料。

## 3. 強制執行規則

1. 嚴格依照 `03_最終實作計畫.md` 的 Phase 與 Slice 順序實作；可把相鄰且同一功能的 Slice 合成一個垂直交付批次，但不可跳過中間業務依賴。
2. 預設以可實際操作的垂直功能批次交付（schema＋API＋UI＋測試＋文件），降低反覆切換與溝通成本；只有高風險規則、資料移轉或無法安全一起回滾的工作才拆成更小批次。
3. 批次內每個 Slice 仍須通過原定自動測試與必要人工驗證，全部通過後才能一起標記完成與建立 checkpoint。
4. 未列在計畫內的新功能，必須先加入需求追蹤矩陣與計畫，必要時新增決策紀錄，才可實作。
5. 業務規則必須由後端與資料庫保護；前端檢查只能改善操作體驗，不能作為唯一保護。
6. 正式資料不得放進開發 seed、測試檔、Git、螢幕截圖或公開問題紀錄。
7. 所有數量、價格、狀態、作廢及重新開啟等關鍵操作必須可追溯。
8. 不得用刪除原紀錄的方式修正完工、庫存、出貨、計價、請款或收款；必須作廢或沖銷。
9. 未通過測試、文件未更新或 README 進度未更新，該切片視為未完成。
10. 不可因趕進度略過 Git 提交與中型進度備份。
11. 所有正式 React 頁面必須選用 [ADR-010 通用版型](docs/UI設計系統與通用版型.md) 與 `frontend/src/ui/` 共用元件；禁止自行建立另一套頁首、卡片、表格、表單、狀態或按鈕視覺。
12. 現有版型無法滿足需求時，不得直接在 feature 內做一次性 UI；必須先證明缺口，再擴充成跨模組可用的共用元件，沿用既有 Tokens，補齊 RWD、鍵盤、狀態及測試後才可使用。
13. `npm run lint` 必須同時通過 UI conformance check；禁止 inline style、舊版 UI class、玻璃模糊、浮卡陰影及未使用 token 的圓角。`/style-preview` 是唯一歷史比較例外，不是正式 UI。
14. 程式碼、檔案、API、資料庫、測試、CSS、文件與 Import 必須遵守命名規範及單檔責任門檻；禁止新增巨型 `utils`、`helpers`、`types` 或把多個 domain 塞進同一檔案。
15. 前端遇到表單、schema 驗證、日期、資料取得、表格、無障礙元件等通用問題時，必須先評估現有依賴與成熟 npm 套件，不重造基礎輪子；新增套件前仍要確認維護活躍度、授權、安全紀錄、TypeScript 支援、bundle 影響、無障礙及是否與現有套件重疊。業務規則不得藏進第三方 UI 套件。

## 4. 目前進度

| 項目 | 目前狀態 |
|---|---|
| 最後更新日期 | 2026-08-13 |
| 計畫版本 | v1.19（Phase 4 Slice 4.0a～4.14 全部完成） |
| 架構版本 | v1.20（案件、工單、報價轉換、私人附件與 A4 列印同步） |
| 目前階段 | Phase 4 案件與工單工程完成（18／18）；等待公司工單版面／印表機 UAT |
| 目前切片 | Phase 4 收尾：案件＋單品工單、報價多明細轉換、同頁建檔、附件與 A4 直向列印已完成 |
| 實作完成度 | Phase 0：完成；Import I-0：3／3；Phase 1：9／9；Phase 2：10／10；Phase 3：8／8；Phase 4：18／18；下一階段為 Phase 5 生產／完工／庫存 |
| 規劃文件完成度 | 100% |
| 最新中型進度備份 | 本次提交後建立 Git tag `checkpoint-phase-4` 與專案外 bundle |
| 正式遠端 Git 備份 | 尚未設定；R-11 維持 Open，正式部署前必須建立私人 repository |

### 已完成

- 讀取公司流程影片、操作圖片及 Private & Shared 流程說明。
- 解析舊 PowerBuilder 系統的視窗、DataWindow、功能關聯與資料表。
- 提取舊系統資料，確認可取得客戶及部分歷史業務資料。
- 整理 Gmail 新需求、刪減功能、報價與工單版面要求。
- 統整公司實際流程與新版改進項目。
- 完成最終技術架構、資料規則、細粒度實作計畫、測試、移轉與 Git 規範。
- 完成真實舊表對照、分批 dry-run、核對門檻及與各功能同步的 Import 工作線。
- 建立新版專案目錄及第一個本機 Git 計畫基準。
- 完成 Import I-0.1、I-0.2：106 個 CSV 的唯讀 manifest／SHA-256／CSV 邏輯筆數／編碼異常基線；同一來源重跑報告完全一致。
- 正式確認 `cust.csv` 為 221 筆客戶資料；222 是包含表頭的 CSV 邏輯行數，未把客戶欄位值寫進報告或 Git。
- 完成 Import I-0.3：建立 `import_runs`、`import_source_files`、通用 `import_staging_records`、`import_errors` 與 `legacy_mappings`；原始／清理 payload 可比較，來源檔、表、列與 key 由複合外鍵保護，跨 run mapping 唯一鍵阻止重複正式套用。98 個一般後端測試與 12 個隔離 PostgreSQL integration 通過，仍未建立或寫入正式客戶表。
- 完成 Slice 0.1：鎖定 Node 24、npm 11、Python 3.12、PostgreSQL 17，初始化 React 與 FastAPI 專案。
- 完成 Slice 0.3：PostgreSQL Compose healthy、只綁 localhost，容器重啟後測試資料仍存在。
- 完成 Slice 0.6：React、TanStack Router、TanStack Query、Error Boundary、首頁與 404；lint、typecheck、4 個測試、build、`npm audit` 與實際瀏覽器檢查通過。
- 完成 Slice 0.4：FastAPI app、runtime／OpenAPI 統一錯誤契約、安全 validation details／logging、production 文件關閉、live／ready 語意，以及分頁、排序白名單、關鍵字／日期 primitive 與列表 metadata；真實 DB readiness 明確留待 Slice 0.5。
- 完成 Slice 0.5：採用 SQLAlchemy 2、Alembic 與 psycopg 3，建立 bounded connection pool、request session lifecycle、真實 `SELECT 1` readiness、app shutdown dispose、空白 migration baseline，以及 localhost／tmpfs 隔離 test DB；92 個一般後端測試與 3 個真實 DB integration 通過。
- 建立 `.env.example`、工具鏈檢查、統一 Make 指令與桌面版操作殼層；分別由 Slice 0.2、0.7、0.10 完成並驗證。
- 因 2026-08-04 React Router 修補版尚未發布，依 ADR-009 改採安全版本 TanStack Router；乾淨 lockfile 的 `npm audit` 為 0。
- 完成 DESIGN-PREVIEW-001：`/style-preview` 可用同一組假工單資料切換 A 平面工業 ERP、B 現代桌面 ERP、C Bootstrap 企業版；5 個前端測試、build 與三種實際瀏覽器檢查通過。
- 依 ADR-010 正式選定「A 平面工業架構＋C 表單清晰度；B 只保留操作習慣」，未導入 Bootstrap，Ant Design 改為未來可選底層元件而非視覺基準。
- 完成 UI-BASELINE-001：單一 248px／72px 側欄、平面 Design Tokens、首頁，以及 `/ui-patterns` 的總覽、清單查詢、新增／編輯、詳細資料四種可操作版型；共用 PageHeader、KPI、Section、FilterBar、Field、DataTableFrame、StatusLabel 與 DefinitionGrid。
- 建立完整 [UI 設計系統與通用版型](docs/UI設計系統與通用版型.md)：包含八類版型、狀態、列印、響應式、鍵盤、URL 狀態、Do／Don't 與逐頁驗收清單；4 個前端測試檔、8 個測試、lint、typecheck、build、文件檢查及實際 1366／1280／390px 瀏覽器驗證通過。
- 完成 UI-GOVERNANCE-001：404、路由錯誤與 React 崩潰頁改用共用 `SystemState`；新增 `check:ui` 並接入 `npm run lint`，自動阻擋脫離 ADR-010 的正式頁面、舊 class、inline style、玻璃模糊、浮卡陰影、非 token 圓角及缺少 RWD 基準。
- 完成 Slice 0.2：後端設定拆為 `config/models.py`、`loader.py`、`database_guard.py`；必要變數與非法值 fail-fast，development／test／production 的 DB 名稱及帳號雙向隔離，Secret 與驗證錯誤不洩漏 DSN；37 個後端測試與 branch coverage 100% 通過。
- 建立 [程式碼與檔案命名規範](docs/程式碼與檔案命名規範.md)：定義 React／TypeScript、FastAPI／Python、SQL／Alembic、API／JSON、測試、CSS、文件及 Import 命名，加入單檔責任、拆檔門檻與 review checklist。
- 完成 Slice 0.7a：保留 `UiPatterns.tsx` 為正式 public boundary，將共用元件依頁面、表單、資訊與系統狀態責任拆成 4 個內部 TSX，將 607 行共用 CSS 拆成 5 個責任樣式檔；conformance 會檢查 200／500 行門檻、public boundary、完整樣式 manifest／載入順序、RWD 與 sticky 識別欄。10 個前端測試、lint、typecheck、build、CSS 語意比對及 7 種實際瀏覽器尺寸通過，畫面、DOM、public API 與 RWD 行為不變。
- 完成 Slice 0.7b：採用精確鎖版 `axe-core` 4.13.0 建立首頁、404 與四種 UI 版型的 WCAG A／AA＋best-practice 自動基線；版型頁維持單一 H1，頁籤具備 tablist／tab／tabpanel、aria-selected／controls、roving tabIndex 與方向鍵／Home／End 操作，跳轉連結會移動焦點至 main，必填文字與 reduced-motion 降級完整。6 個前端測試檔、15 個測試、lint、typecheck、build、`npm audit` 及 7 種實際瀏覽器尺寸通過。
- 完成 Slice 0.8：以 `workflowModules.ts` 集中定義主模組；P0-CASE-DECISION-001 後擴充為客戶、報價、案件、工單、生產、庫存、出貨、計價、請款／對帳、收款十個模組。同一份定義產生路由、側欄及公司流程導覽；頁面明確標示為展示資料／功能尚未啟用，未連接 API、資料庫或正式公司資料。

- 完成 Slice 0.9：FastAPI 可離線、deterministic 匯出 OpenAPI snapshot，Orval 8.23.0 由契約產生原生 Fetch TypeScript client；`api:check` 以暫存目錄逐 byte 阻擋 snapshot／client drift。API origin 預設同源且不重複 `/api/v1`；首頁實際顯示 loading、ready、503、離線與重試，non-2xx 會成為 TanStack Query error，安全中文訊息不洩漏底層例外。獨立 Agent 攔下已進入 maintenance mode 的 `openapi-fetch` 與帶 high advisory 的替代版本，最終 lockfile 的 npm high advisory 為 0。
- 完成 Slice 0.10：根目錄提供 `make bootstrap/dev/test/lint/build/down`，另有 `audit/check`；Ruff、ESLint／UI conformance、OpenAPI drift、99 個一般後端測試、12 個隔離 PostgreSQL integration、39 個前端測試、build 與乾淨目錄安裝／啟停流程均通過。`make down` 不使用 `-v`，development volume 在停止後仍保留。
- 完成 UX-CLARIFICATION-001：依 Gmail 原稿把 `/work-orders` 修正為工單查詢清單，保留關鍵字及單價／版費／刀模費結果欄；`/work-orders/new` 是客戶、訂單、價格、備紙、印刷、13 道製程、備註與圖片都在同一 form 的假資料原型。畫面使用既有 ADR-010 元件，內部拆成 7 個單一責任 TSX 與 1 個 RWD 樣式檔；頁內錨點同步 hash 並移動焦點，沒有 KPI、正式資料、API 寫入或業務 migration。當時製版、單號、浪紙欄位等 P0 未決規則沒有被硬編；製版後續已由 P0-DECISION-001 定案。
- 完成 P0-DECISION-001：重新逐頁核對 9 份 Gmail PDF 與 `系統修改.jpg`，確認 P0-08 保留製版協力廠／說明、新舊版與輪轉方向，並把版本與輪轉實作為兩組獨立單選。P0-10 確認不限年份的全量匯入目標，每筆來源都必須有正式匯入、只讀封存、合併 mapping 或例外待處理的可核對去向。
- 完成 REQ-ATTACHMENT-TRACE-001：建立 [Gmail 附件需求逐項對照](docs/Gmail附件需求逐項對照.md)，把四份報價、五份工單 PDF 與 `系統修改.jpg` 分成建檔結構、註解規則、UAT 範例及列印契約；補齊 QUO-007～008、WO-013～016，並修正 Phase 3／4 的逐欄小切片與驗收條件。範例內容不作系統預設值；當時 P0-01／02／09 尚未決，P0-01／02 後續已由 ADR-014 定案。
- 完成 P0-CASE-DECISION-001：公司確認「案件 → 工單 → 製程任務」；N 筆報價明細建立一個案件與 N 張單品工單，直接建工單會自動建立單工單案件。新增 ADR-014、CASE-001～005、`/cases` 假資料原型與子工單表格；舊 `b_replay1`／`b_replay2` 納入 Import 計畫且不臆造舊報價工單關聯。
- 完成 P0-EVIDENCE-AUDIT-001：以 9 份 PDF／系統修改圖及直接 PowerBuilder 原始碼核對 P0-03～P0-07、P0-09，建立 [P0 待決策證據核對](docs/P0待決策證據核對.md)。確認舊運送 gate、正式量／備品扣庫、舊系統未可靠阻止超量、舊稅額／取整與單一對帳單證據；使用者的英文前綴＋舊號原樣觀看已記為 P0-09 部分方向，不把問句誤報成最終簽認。
- 完成 P0-DECISION-SYNC-002：公司簽認 P0-03 運送前置＋獨立完工核定、P0-04 正式／備品都扣庫且基礎計價預設只用正式量、P0-06 對帳可選計稅預設關閉、P0-07 單一對帳單＋請款狀態、P0-09 七類新號＋舊號原樣保留；建立 ADR-015～018。
- 完成 P0-FINAL-DECISION-001：P0-05 定案為「已有有效運送完成事件後，專用權限者同交易補登真實完工再出貨且永不負庫存」，建立 ADR-019。P0 10／10；公司同意 PDF 的欄位、分區、順序、單頁操作及列印內容為 UI 契約，外觀採現代工業 ERP 與 RWD，不複製 XP 像素外觀。
- 完成 Phase 1 Slice 1.1：新增 `organizations`、`users`、`organization_members`、`sessions` 正式 identity schema。登入沿用舊系統「使用者代號」概念但不沿用舊密碼；帳號去除前後空白且不分大小寫比對後必須全域唯一。Session 只保存 SHA-256 digest 並綁定公司成員，不保存 raw cookie token。21 個隔離 PostgreSQL 測試已驗證 constraint、外鍵、索引、前版 Import 資料保留及 `upgrade → downgrade → upgrade`；尚未建立 seed、登入 API、Cookie、角色或權限。
- 完成 Phase 1 Slice 1.2：採用 `argon2-cffi` 25.x 的明確 Argon2id profile，建立只允許 development／test 的顯式 identity seed。首次建立一間標示虛構的公司、`test.admin`、`test.operator` 及兩筆 membership；兩密碼只由隱藏提示或程序環境取得且必須不同，沒有預設值、CLI 參數或 Git 明文。重跑會驗證既有 hash 並保持逐 byte 不變；密碼、固定 ID、正規化 login 或 membership 衝突時整批 rollback。管理員／操作員目前只是名稱，角色留在 Slice 1.6；沒有建立 Session 或登入 API。本次 audit 另發現 Orval 8.23.0 的間接 `js-yaml` high advisory，已升級精確鎖版 Orval 8.24.0／`js-yaml` 4.3.1，重產 client 並恢復 0 vulnerabilities。
- 完成 Phase 1 Slice 1.3：新增 `POST /api/v1/auth/login` 與 `POST /api/v1/auth/logout`。登入必須指定公司並驗證使用者、公司與 membership 皆啟用；所有帳密／停用失敗使用相同 401，未知帳號仍執行 Argon2 dummy verify。每次登入建立不同的 8 小時 server Session，raw 256-bit token 只在成功 response 回傳一次，資料庫只存 SHA-256 digest；登出只設 `revoked_at`，已撤銷、過期或未知但格式正確的 token 一律相同 204。登入建立 Session 與 `last_login_at` 更新同交易，衝突會完整 rollback；尚未加入 Cookie、CSRF、Origin、React 登入頁、角色或限流。
- 完成 Phase 1 Slice 1.4：移除公開 Bearer transport，raw Session token 只放 host-only HttpOnly Cookie；JSON、OpenAPI、generated client、log 與資料庫都不含 raw token。Cookie 採 SameSite=Strict、production 固定 Secure、不設瀏覽器持久期限；CSRF token 由伺服器 HMAC 簽章並綁定 Session digest。登入與登出 exact-match `APP_PUBLIC_ORIGIN`，缺 Origin 時只接受同源 Referer；錯來源、偽造 token 與跨 Session token 均拒絕。已建立 Cookie-only current Session dependency，但登入頁與載入目前使用者 endpoint 留在 Slice 1.5。
- 完成 Phase 1 Slice 1.5：新增 `GET /api/v1/auth/session`、ADR-010 平面工業風格 React 登入頁與受保護路由。重新整理會以 HttpOnly Cookie 向後端恢復使用者／公司資訊，Session 無效或過期回登入頁；登出送出 signed CSRF header、撤銷後清除 query cache。瀏覽器不使用 `localStorage`或保存密碼；公司 UUID 是公開部署設定，由 `VITE_ORGANIZATION_ID` 提供。
- 完成 Phase 1 Slice 1.6：新增可逆 `0005_authorization_foundation`，建立 permissions、公司 roles、role grants 與 membership role assignment；兩組複合外鍵直接拒絕跨公司角色。後端 exact capability dependency 預設拒絕並回穩定 403，current Session 回傳啟用中的 capability；React 提供通用 `CapabilityGate`。P1-02 正式角色 mapping 尚待公司簽認，migration 沒有寫入候選業務權限。
- 完成 Phase 1 Slice 1.7：新增 Session-only `OrganizationScope` dependency；SELECT／UPDATE／DELETE 由 model scope 加入公司條件，CREATE 由後端注入 ownership，caller 偽造 organization 會在 SQL 前失敗。A／B 公司真 PostgreSQL 測試證明 A 查不到也改不到 B，且 cross-company error 不暴露公司 ID。沒有新增 migration、RLS 或業務表。
- 完成 Phase 1 Slice 1.8：新增可逆 `0006_audit_foundation`、交易式 audit service、遞迴敏感欄位遮罩及伺服器產生的 Request ID。稽核資料與業務異動由同一 transaction 提交或回滾，資料庫拒絕一般 UPDATE／DELETE；`GET /api/v1/audit-logs` 以 `audit.read`、Cookie Session 與公司 scope 保護。React `/audit-logs` 使用既有清單版型，具 loading、空資料、錯誤、無權限、RWD 與 axe 基線；A／B 公司真 PostgreSQL 測試確認紀錄不混用。
- 完成 Phase 1 Slice 1.9：新增可逆 `0007_login_security`、公司範圍 HMAC 登入 bucket、15 分鐘內第五次失敗起限制 15 分鐘，以及 append-only 安全事件。已知／未知帳號使用相同門檻；成功登入會清除失敗狀態。資料庫不保存 raw 帳號、密碼或 IP，A／B 公司不共用計數。184 個非 DB、77 個 PostgreSQL integration 與 69 個 React 測試通過。
- 完成 Phase 2 Slice 2.1：以可逆 `0008_organization_profile` 擴充公司名稱、統編、負責人、電話、傳真、Email、地址與完整 Logo metadata；Logo object key 不對前端公開，也不能在表單手填。`GET／PUT /api/v1/organizations/current/profile` 只使用 Session 公司、`settings.manage`、signed CSRF、樂觀衝突與同交易 audit。React `/settings/company` 沿用 ADR-010 表單版型，具即時文件頁首預覽、無權限／loading／錯誤狀態及 RWD；185 個非 DB、80 個 PostgreSQL integration 與 72 個 React 測試通過。
- 完成 Phase 2 Slice 2.2：新增可逆 `0009_organization_settings`，每家公司只有一筆設定；對帳單計稅預設關閉，啟用後稅率、取整範圍與小數位才必須完整。ADR-018 的七類單號格式及公司 PDF 已確認的報價 A4 橫向、工單 A4 直向九製程以唯讀政策版本呈現，不允許 UI 改寫。`GET／PUT /api/v1/organizations/current/settings` 受公司 scope、`settings.manage`、signed CSRF、更新衝突與同交易 audit 保護；React `/settings/defaults` 已通過 RWD、axe 與實際桌面存檔驗證。正式稅額計算、單號配發、文件與列印仍留在對應 Phase；186 個非 DB、84 個 PostgreSQL integration 與 76 個 React 測試通過。
- 完成 Phase 2 Slice 2.3～2.5 客戶管理垂直功能：可逆 `0010_customers` 建立公司範圍客戶主檔，保存代號、名稱、簡稱、統編、主要聯絡與地址；同公司代號 trim＋不分大小寫唯一，停用不刪除。`GET／POST／PUT /api/v1/customers` 與狀態 API 使用 Cookie Session、`customers.read／manage`、公司 scope、signed CSRF、樂觀衝突及同交易 audit。React `/customers`、`/customers/new`、`/customers/:id` 完成查詢、新增、編輯、停用、唯讀權限、loading／empty／error、RWD 與 axe；186 個非 DB、86 個 PostgreSQL integration 與 78 個 React 測試通過。舊稅務／取整、付款條件及 221 筆舊客戶 Import 仍留在 Slice 2.6／I-1.1。
- 完成 Phase 2 Slice 2.6～2.10：客戶加入付款條件與舊稅額／取整唯讀證據；建立廠商、紙質、紙廠、固定 13 道製程及客戶常用工作項目 schema、公司隔離 API、權限、稽核與正式 React 頁面。Import I-1.1～I-1.3 已執行 aggregate-only dry-run，沒有 apply 正式資料；`cust` 221 筆有 109 個替代字元，`wpa` 9,831 筆中 189 筆客戶代號未對上且 6 筆缺客戶代號，必須先修復／簽認 mapping。
- 完成 Phase 3 Slice 3.1～3.8：可逆 `0014_document_sequences`／`0015_quotations`、每公司每日 `QUO-YYYYMMDD-SS`、客戶與抬頭快照、報價明細、草稿更新、確認凍結、另存新號、具原因的作廢及 legacy 舊號查詢。React 正式提供查詢、同頁建檔與 A4 橫向列印；頁首／頁尾維持公司稿「另存新檔、存檔、取消、列印」，新報價沒有稅額欄。Import I-1.4 aggregate-only dry-run 已核對 4 主檔／10 明細；3 筆缺明細主鍵，其餘 7 筆也未對上主檔，故未 apply 且列為來源回查 blocker。
- 完成 Phase 4 Slice 4.0a～4.14：可逆 `0016_production_cases`／`0017_work_orders`、案件與工單每日單號、直接建工單自動建案件、已確認報價多明細原子轉換、確認／另存／作廢、私人附件及 legacy 舊號查詢。React 正式提供案件清單／詳情、工單查詢／單頁建檔及 A4 直向列印；建檔依公司稿保存 13 道製程，列印固定 9 道並可帶圖片。Import I-2.1 dry-run 已核對 `subpoena` 1,431 筆與 `quote` 1,451 筆，但現有匯出父鍵 0 筆可直接相連，因此未 apply 且禁止猜測關聯。

### 進行中

- Phase 0～Phase 4 工程已完成；公司資料、客戶、主檔、報價、案件與工單已形成可操作垂直流程。舊資料目前只有 dry-run，尚未正式 apply；報價／工單 A4 仍需公司實際印表機簽認不截字。
- 工單查詢、單頁建檔、案件分組、正式儲存／編輯／確認／另存／作廢、私人附件及 A4 列印皆已接正式 API／資料表；生產事件、最終完工與庫存仍屬 Phase 5。
- 介面正式方向已定案；`/style-preview` 只保留為歷史比較與 ADR-010 決策證據，不是正式業務頁。
- 公司 P0 已確認 10／10。正式 migration、API 與舊客戶資料 apply 仍只會在對應 Phase／Import Slice 通過測試後逐批建立，不因 Gate 通過而提前寫入。
- `import_staging_records` 目前只是 raw／normalized 通用 envelope；客戶 typed mapping、dry-run、apply、個資 access／retention 與錯誤訊息遮罩留在 I-1.x，不得提前把 JSONB 當正式業務模型。

### 接下來要做

1. 下一個垂直批次進入 Phase 5：建立 13 道製程事件、運送完成前置、獨立最終完工核定與不可負庫存的成品流水。
2. 回查 `quote.subpoenaid` 與工單父鍵；現有匯出 1,451 筆全部無法直接相連，在取得舊程式 join 或可核對匯出前不得 apply。
3. 舊資料 apply 前同時處理 `cust` 轉碼替代字元及 `wpa` 的 189 筆孤兒／6 筆缺客戶代號；修復後重跑相同 dry-run，不能跳過公司抽查。
4. 以公司實際印表機驗收報價 A4 橫向及工單 A4 直向；程式端欄位、列印 CSS、隱藏操作、快照與圖片測試已完成。

### 後續 Phase／UAT 仍待確認

- 角色對 capability 的實際 mapping、出貨／對帳實際樣張、印表機及未由附件指定的欄位必填／上限；這些不回頭阻擋 P0，但必須在對應 Slice 前定案。

## 5. 每個垂直批次的固定工作循環

```text
確認批次涵蓋的相鄰 Slice 與需求編號
→ 更新或新增測試
→ 完成 schema、API、UI 的必要垂直路徑
→ 執行自動測試
→ 執行人工驗證
→ 更新文件與 README 進度
→ 更新 docs/progress/實作進度紀錄.md
→ Git commit
→ 達中型進度時建立 tag、Git bundle 並推送遠端
```

批次完成必須同時滿足：

- 功能符合需求追蹤矩陣。
- 單元、整合或 E2E 測試依風險通過。
- 錯誤情境與權限情境已驗證。
- 沒有使用正式公司資料作為測試資料。
- README 的「目前進度」「已完成」「進行中」「接下來要做」已更新。
- 詳細進度紀錄已追加本次日期、結果、測試與 commit。
- 形成一個可回復的 Git commit。

## 6. Git 與備份規則

- 每完成一個可操作的垂直批次：至少建立一個清楚、可單獨回復的 commit；高風險 migration 可另拆 checkpoint。
- 每完成一個中型進度：更新 README、提交、建立 annotated tag，再執行 `scripts/create-checkpoint.sh <名稱>`。
- 中型進度定義：一個 Phase 完成，或連續完成 3～5 個相關切片且形成可展示成果。
- 每個中型進度建立 Git bundle 到專案外的 `../git-backups/`。
- 設定私人遠端 repository 後，每個中型進度必須推送目前分支及 tag。
- 本機 commit 只是版本紀錄，不等於異機備份；正式開發不得長期維持「沒有遠端」的狀態。
- 不得提交 `.env`、密碼、Cloud 金鑰、正式資料、附件、資料庫 dump 或個資。

完整規則請見[本機開發與 Git 備份規範](docs/本機開發與Git備份規範.md)。

## 7. 預定技術與目錄

### 本機前置需求

- Docker Desktop（daemon 必須已啟動）與 Docker Compose。
- Python 3.12（專案基準）、Git、GNU Make、ripgrep。
- Node 24／npm 11；未安裝正確版本時，專案 wrapper 可透過 npm cache／網路取得隔離工具鏈。
- 第一次安裝需可連線 npm registry 與 PyPI；`make audit` 也需要網路。

### 統一操作指令

本機第一次安裝：

```bash
make toolchain-check
make bootstrap
# 編輯 .env：更換 POSTGRES_PASSWORD，以 secrets.token_urlsafe(32) 分別產生兩把不同的 CSRF_HMAC_KEY／AUTH_SECURITY_HMAC_KEY，並設定 VITE_ORGANIZATION_ID
make env-check
```

產生本機 CSRF key 的範例指令（產生後貼到 `.env`，不要把輸出貼到 issue、log 或 Git）：

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
chmod 600 .env
```

若 `.env` 是 Slice 1.9 前建立的舊檔，需同步目前 `.env.example` 的 `APP_PUBLIC_ORIGIN`、`CSRF_HMAC_KEY`、`AUTH_SECURITY_HMAC_KEY` 與 `VITE_ORGANIZATION_ID`，並將 `DATABASE_URL` 保持為變數引用寫法。兩把 HMAC key 都應各自以 Python `secrets.token_urlsafe(32)` 產生且不得相同，不得沿用範例或提交 Git；本機 `.env` 建議權限設為只有本人可讀。`VITE_ORGANIZATION_ID` 是公開的部署識別碼，不是 Secret，但仍不可當成後端公司 scope 驗證的代替品。

正式伺服器不要把真實密鑰放在 React bundle、Git、Dockerfile 或可公開的 `.env`。單機 VM 可使用僅部署帳號可讀的系統環境檔（例如 `/etc/company-system/company-system.env`，owner-only）由 systemd 注入；雲端／容器環境優先使用 Secret Manager、Docker Secret 或等價機制在啟動時注入。輪替 `CSRF_HMAC_KEY` 會使現有 CSRF token 失效；輪替 `AUTH_SECURITY_HMAC_KEY` 會改變登入 bucket 指紋，應先清除短期 throttle state。兩者都不需要資料庫 migration，但應安排撤銷 Session或重新登入及保留安全事件的核對方式。

日常操作：

```bash
make dev    # PostgreSQL＋migration＋FastAPI＋Vite；Ctrl-C 停掉兩個 host process
make lint   # 文件、shell、Compose、Ruff、ESLint＋UI、OpenAPI drift
make test   # Import、backend unit、隔離 PostgreSQL integration、frontend test
make build  # backend import smoke、frontend typecheck 與 production build
make down   # 停掉 Compose 服務；不刪除 development volume
```

若 PostgreSQL volume 已用舊密碼初始化，之後只改 `.env` 會出現密碼驗證失敗。先確認 volume 是否含需保留資料，再讓 `.env` 改回該 volume 的原密碼或依備份／還原流程建立新 volume；不得為了排錯直接使用 `docker compose down -v` 刪除資料。

其他入口：

```bash
make audit  # pip check 與 npm security audit，需網路
make check  # lint → test → build → audit
make db-up  # 先顯式啟動本機 PostgreSQL
make seed-test-identity  # 顯式建立／核對虛構本機帳號；不會由 dev 自動執行
```

先以 `make db-up` 顯式啟動本機 PostgreSQL，再執行 `make seed-test-identity`。seed 只允許 development／test；它會先檢查環境與兩個密碼，通過後才升級 migration 並連接資料庫。密碼以隱藏提示分別讀取；非互動環境只能用 `TEST_ADMIN_SEED_PASSWORD`、`TEST_OPERATOR_SEED_PASSWORD` 程序環境變數。不要把兩個值寫進 `.env`、指令列參數、Git 或文件。

`make dev` 因範例密碼、範例 CSRF key 或缺少 `.env` 拒絕啟動時，先執行 `make bootstrap`並修改兩項 Secret。port 5173、8000 或 5432 被佔用時，先停掉佔用該 port 的本專案過程，不可使用寬鬆 `pkill node/python`。若只需停掉容器，執行 `make down`；它在 `.env` 不存在時仍可用，且不會刪除開發資料。

前端有完整 `package-lock.json`；Python 依賴目前是受控版本範圍而非 bit-for-bit lock，Phase 1 前會再評估 lockfile。`.env`、資料庫 volume、舊資料、Import 報告與正式資料都不得提交 Git。

```text
company-system/
├─ README.md
├─ 01_公司流程與新版改進.md
├─ 02_最終系統架構.md
├─ 03_最終實作計畫.md
├─ 04_開工前確認清單.md
├─ frontend/                # React + TypeScript + Vite
├─ backend/                 # FastAPI + SQLAlchemy + Alembic
├─ infra/                   # Docker、Caddy、部署與備份
├─ e2e/                     # Playwright 完整流程測試
├─ storage/                 # 本機附件，不進 Git
├─ scripts/                 # 文件檢查與 Git checkpoint 工具
└─ docs/                    # 資料、測試、移轉、決策與進度文件
```

目前 `frontend/` 與 `backend/` 已有可執行骨架，PostgreSQL 由根目錄 `compose.yaml` 啟動；`backend/app/modules/imports/` 包含 Import staging／trace infrastructure。登入、Cookie Session、公司 scope、capability、audit、登入限制、公司資料、公司預設設定與客戶管理均已完成；正式角色 mapping、舊客戶帳務欄位／Import、報價、工單、單號配發、稅額計算與帳務文件仍依後續 Slice 建立。

## 8. 完成定義

第一版只有在下列條件全部成立時才算完成：

- 可由客戶直接建立單工單案件，也可由報價明細建立一個案件與多張子工單。
- 可完整走完工單、製程、最終完工、存貨、出貨、計價、請款及收款。
- 部分完工、部分出貨、多次出貨、備品及沖銷均計算正確。
- 不會超量出貨、重複計價、重複請款或超額收款。
- 單價、版費、刀模費、稅額與取整方式均保存正確快照。
- A4 報價、工單、出貨單及對帳單經公司實際印表機驗收。
- 舊資料完成試匯、核對、正式匯入及抽樣驗收。
- 權限、稽核、附件安全、備份與異機還原均通過測試。
- 兩位使用者可同時操作核心流程。
- 正式切換後仍有已驗證的回復方案。
