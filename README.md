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

1. 嚴格依照 `03_最終實作計畫.md` 的 Phase 與 Slice 順序實作。
2. 一個 Agent 一次只進行一個小切片；只有互不依賴、檔案範圍不重疊的工程工作可平行進行，整合時仍須逐項驗證，不得把多個未驗證功能混成一批。
3. 每個切片都必須通過該切片指定的自動測試與人工驗證，才能標記完成。
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
| 最後更新日期 | 2026-08-08 |
| 計畫版本 | v1.3（同步 P0-03、04、06、07、09 與 ADR-015～018） |
| 架構版本 | v1.8（完工、備品計價、對帳稅務與新舊單號已定案） |
| 目前階段 | Phase 0 工程切片 10／10 已完成；Phase Gate 等待公司簽核 |
| 目前切片 | P0-DECISION-SYNC-002：五項新決策已同步；只剩 P0-05 不足庫存操作待公司簽認 |
| 實作完成度 | Phase 0 工程切片：10／10 完成；Import I-0：3／3 完成；業務功能 0% |
| 規劃文件完成度 | 100% |
| 最新中型進度備份 | Git tag `checkpoint-p0-case-model-v1`；經驗證 bundle 位於專案外層 `git-backups/` |
| 正式遠端 Git 備份 | 尚未設定，必須在 Phase 1 完成前建立私人 repository |

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
- 完成 Slice 0.8：以 `workflowModules.ts` 集中定義主模組；P0-CASE-DECISION-001 後擴充為客戶、報價、案件、工單、生產、庫存、出貨、計價、請款／對帳、收款十個模組。同一份定義產生路由、側欄及公司流程導覽，所有頁面明確標示為 Phase 0 假資料原型，未連接 API、資料庫或正式公司資料。

- 完成 Slice 0.9：FastAPI 可離線、deterministic 匯出 OpenAPI snapshot，Orval 8.23.0 由契約產生原生 Fetch TypeScript client；`api:check` 以暫存目錄逐 byte 阻擋 snapshot／client drift。API origin 預設同源且不重複 `/api/v1`；首頁實際顯示 loading、ready、503、離線與重試，non-2xx 會成為 TanStack Query error，安全中文訊息不洩漏底層例外。獨立 Agent 攔下已進入 maintenance mode 的 `openapi-fetch` 與帶 high advisory 的替代版本，最終 lockfile 的 npm high advisory 為 0。
- 完成 Slice 0.10：根目錄提供 `make bootstrap/dev/test/lint/build/down`，另有 `audit/check`；Ruff、ESLint／UI conformance、OpenAPI drift、99 個一般後端測試、12 個隔離 PostgreSQL integration、39 個前端測試、build 與乾淨目錄安裝／啟停流程均通過。`make down` 不使用 `-v`，development volume 在停止後仍保留。
- 完成 UX-CLARIFICATION-001：依 Gmail 原稿把 `/work-orders` 修正為工單查詢清單，保留關鍵字及單價／版費／刀模費結果欄；`/work-orders/new` 是客戶、訂單、價格、備紙、印刷、13 道製程、備註與圖片都在同一 form 的假資料原型。畫面使用既有 ADR-010 元件，內部拆成 7 個單一責任 TSX 與 1 個 RWD 樣式檔；頁內錨點同步 hash 並移動焦點，沒有 KPI、正式資料、API 寫入或業務 migration。當時製版、單號、浪紙欄位等 P0 未決規則沒有被硬編；製版後續已由 P0-DECISION-001 定案。
- 完成 P0-DECISION-001：重新逐頁核對 9 份 Gmail PDF 與 `系統修改.jpg`，確認 P0-08 保留製版協力廠／說明、新舊版與輪轉方向，並把版本與輪轉實作為兩組獨立單選。P0-10 確認不限年份的全量匯入目標，每筆來源都必須有正式匯入、只讀封存、合併 mapping 或例外待處理的可核對去向。
- 完成 REQ-ATTACHMENT-TRACE-001：建立 [Gmail 附件需求逐項對照](docs/Gmail附件需求逐項對照.md)，把四份報價、五份工單 PDF 與 `系統修改.jpg` 分成建檔結構、註解規則、UAT 範例及列印契約；補齊 QUO-007～008、WO-013～016，並修正 Phase 3／4 的逐欄小切片與驗收條件。範例內容不作系統預設值；當時 P0-01／02／09 尚未決，P0-01／02 後續已由 ADR-014 定案。
- 完成 P0-CASE-DECISION-001：公司確認「案件 → 工單 → 製程任務」；N 筆報價明細建立一個案件與 N 張單品工單，直接建工單會自動建立單工單案件。新增 ADR-014、CASE-001～005、`/cases` 假資料原型與子工單表格；舊 `b_replay1`／`b_replay2` 納入 Import 計畫且不臆造舊報價工單關聯。
- 完成 P0-EVIDENCE-AUDIT-001：以 9 份 PDF／系統修改圖及直接 PowerBuilder 原始碼核對 P0-03～P0-07、P0-09，建立 [P0 待決策證據核對](docs/P0待決策證據核對.md)。確認舊運送 gate、正式量／備品扣庫、舊系統未可靠阻止超量、舊稅額／取整與單一對帳單證據；使用者的英文前綴＋舊號原樣觀看已記為 P0-09 部分方向，不把問句誤報成最終簽認。
- 完成 P0-DECISION-SYNC-002：公司簽認 P0-03 運送前置＋獨立完工核定、P0-04 正式／備品都扣庫且基礎計價預設只用正式量、P0-06 對帳可選計稅預設關閉、P0-07 單一對帳單＋請款狀態、P0-09 七類新號＋舊號原樣保留；建立 ADR-015～018。

### 進行中

- Phase 0 工程切片 10／10 已完成；工程完成不等於公司 Phase Gate 已簽核，也不代表正式業務功能已完成。
- 工單查詢與單頁建檔的介面邊界已依原稿修正；正式儲存、編輯、列印、API 與資料表仍屬 Phase 4，不把原型誤報為業務功能。
- 介面正式方向已定案；`/style-preview` 只保留為歷史比較與 ADR-010 決策證據，不是正式業務頁。
- 公司 P0 已確認 9／10；只剩 P0-05。候選為「前提是已有有效運送完成事件；不允許負庫存，但可由有權限者在出貨畫面同交易補登真實完工再出貨」，尚待簽認。因此尚未建立正式業務 migration，也未把舊客戶資料寫入新版資料庫。
- `import_staging_records` 目前只是 raw／normalized 通用 envelope；客戶 typed mapping、dry-run、apply、個資 access／retention 與錯誤訊息遮罩留在 I-1.x，不得提前把 JSONB 當正式業務模型。

### 接下來要做

1. 由公司簽認 Phase 0 的客戶→報價（可略過）→案件→工單→製程任務導覽與頁面名稱；工程完成不能代替公司驗收。
2. 由公司確認 P0-05：已有有效運送完成事件但出貨庫存不足時，是否允許具專用權限者在同一交易補登真實完工後再出貨，且任一步失敗全部回滾。
3. Phase 3／4 開工時依 `docs/Gmail附件需求逐項對照.md` 逐 Slice 建立測試，不可把整份報價或工單一次塞入單一元件。
4. 公司簽核完成後進入 Phase 1；客戶 Slice 2.6 完成並簽認 mapping 後，才執行 I-1.1 `cust` dry-run。

### 尚待確認但不影響閱讀計畫

- P0-05 不足庫存的最終交易與操作規則。
- 導覽、頁名、出貨／對帳實際樣張與角色權限等後續 Phase／UAT 項目，不得冒充 P0 已完成。

## 5. 每個切片的固定工作循環

```text
確認切片目標與需求編號
→ 更新或新增測試
→ 只實作該切片
→ 執行自動測試
→ 執行人工驗證
→ 更新文件與 README 進度
→ 更新 docs/progress/實作進度紀錄.md
→ Git commit
→ 達中型進度時建立 tag、Git bundle 並推送遠端
```

切片完成必須同時滿足：

- 功能符合需求追蹤矩陣。
- 單元、整合或 E2E 測試依風險通過。
- 錯誤情境與權限情境已驗證。
- 沒有使用正式公司資料作為測試資料。
- README 的「目前進度」「已完成」「進行中」「接下來要做」已更新。
- 詳細進度紀錄已追加本次日期、結果、測試與 commit。
- 形成一個可回復的 Git commit。

## 6. Git 與備份規則

- 每完成一個小切片：至少建立一個清楚、可單獨回復的 commit。
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
# 編輯 .env，把 POSTGRES_PASSWORD 換成只供本機使用的非範例密碼
make env-check
```

若 `.env` 是 Slice 0.2 前建立的舊檔，需先將其中的 `DATABASE_URL` 同步為目前 `.env.example` 的變數引用寫法，再設定 `POSTGRES_PASSWORD`；程式不會覆寫本機私密設定。

日常操作：

```bash
make dev    # PostgreSQL＋migration＋FastAPI＋Vite；Ctrl-C 停掉兩個 host process
make lint   # 文件、shell、Compose、Ruff、ESLint＋UI、OpenAPI drift
make test   # Import、backend unit、隔離 PostgreSQL integration、frontend test
make build  # backend import smoke、frontend typecheck 與 production build
make down   # 停掉 Compose 服務；不刪除 development volume
```

其他入口：

```bash
make audit  # pip check 與 npm security audit，需網路
make check  # lint → test → build → audit
```

`make dev` 因範例密碼或缺少 `.env` 拒絕啟動時，先執行 `make bootstrap`並修改密碼。port 5173、8000 或 5432 被佔用時，先停掉佔用該 port 的本專案過程，不可使用寬鬆 `pkill node/python`。若只需停掉容器，執行 `make down`；它在 `.env` 不存在時仍可用，且不會刪除開發資料。

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

目前 `frontend/` 與 `backend/` 已有可執行的 Phase 0 骨架，PostgreSQL 由根目錄 `compose.yaml` 啟動；`backend/app/modules/imports/` 只包含 Import staging／trace infrastructure，`infra/` 仍只保留責任說明。正式業務資料表、登入、客戶、工單與帳務功能都尚未建立。

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
