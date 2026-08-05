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
5. [需求追蹤矩陣](docs/需求追蹤矩陣.md)
6. [資料模型與業務規則](docs/資料模型與業務規則.md)
7. [測試與驗收計畫](docs/測試與驗收計畫.md)
8. [舊資料移轉計畫](docs/舊資料移轉計畫.md)
9. [舊系統資料 Import 對照與分批計畫](docs/舊系統資料Import對照與分批計畫.md)
10. [舊資料來源基線報告](docs/舊資料來源基線報告.md)
11. [本機開發與 Git 備份規範](docs/本機開發與Git備份規範.md)
12. [風險與決策紀錄](docs/風險與決策紀錄.md)
13. [詳細實作進度紀錄](docs/progress/實作進度紀錄.md)

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

## 4. 目前進度

| 項目 | 目前狀態 |
|---|---|
| 最後更新日期 | 2026-08-05 |
| 計畫版本 | v1.0 |
| 架構版本 | v1.1（ADR-009：TanStack Router） |
| 目前階段 | Phase 0 工程骨架完成，介面風格比較頁等待使用者選擇；P0 業務決策仍待公司確認 |
| 目前切片 | DESIGN-PREVIEW-001 已完成；下一個工程切片仍為 0.2 |
| 實作完成度 | Phase 0：3／10 完成；Import I-0：2／3 完成；業務功能 0% |
| 規劃文件完成度 | 100% |
| 最新中型進度備份 | Git tag `checkpoint-foundation-batch-1`；bundle 位於專案外層 `git-backups/` |
| 正式遠端 Git 備份 | 尚未設定，開工前需建立私人 repository |

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
- 完成 Slice 0.1：鎖定 Node 24、npm 11、Python 3.12、PostgreSQL 17，初始化 React 與 FastAPI 專案。
- 完成 Slice 0.3：PostgreSQL Compose healthy、只綁 localhost，容器重啟後測試資料仍存在。
- 完成 Slice 0.6：React、TanStack Router、TanStack Query、Error Boundary、首頁與 404；lint、typecheck、4 個測試、build、`npm audit` 與實際瀏覽器檢查通過。
- 建立 FastAPI app、統一錯誤格式與 live／ready 骨架；8 個 API 測試及真實 HTTP smoke 通過。資料庫 readiness 留待 Slice 0.5 接線，因此 Slice 0.4 尚未標記完整完成。
- 建立 `.env.example`、工具鏈檢查、Make 指令與桌面版操作殼層初版；這些分別是 Slice 0.2、0.7、0.10 的部分成果，尚未提前標記完成。
- 因 2026-08-04 React Router 修補版尚未發布，依 ADR-009 改採安全版本 TanStack Router；乾淨 lockfile 的 `npm audit` 為 0。
- 完成 DESIGN-PREVIEW-001：`/style-preview` 可用同一組假工單資料切換 A 平面工業 ERP、B 現代桌面 ERP、C Bootstrap 企業版；5 個前端測試、build 與三種實際瀏覽器檢查通過。

### 進行中

- 無未提交的功能開發；第一批成果已驗證並建立 checkpoint。
- 介面正式風格尚待使用者從 A／B／C 選擇；比較頁不代表已導入 Bootstrap 或 Ant Design，也不計入已完成的正式業務頁面。
- 公司 P0-01～P0-10 業務決策仍未完成，因此尚未建立正式業務 migration，也未把舊客戶資料寫入新版資料庫。

### 接下來要做

1. 由使用者在 `/style-preview` 選擇 A、B、C 或指定混合方向，再把決定記錄到 UI Design Token／Slice 0.7。
2. 執行單一 Slice 0.2：加入後端 settings、必要環境變數驗證，以及 test 不得誤連 dev DB 的測試。
3. 完成 Slice 0.4／0.5：加入 SQLAlchemy session、真實 DB readiness 與 Alembic 空白基線；只建工程／Import 基礎 schema，不建正式業務表。
4. 執行 Import I-0.3：建立 `import_runs`、staging、mapping 與 errors 基礎，仍不得寫入正式客戶表。
5. 補完 Slice 0.7 的狀態元件、accessibility 基線及 Windows 常用尺寸檢查。
6. 逐項請公司完成 `04_開工前確認清單.md` 的 P0-01～P0-10，之後才開始不可逆的業務 schema。

### 尚待確認但不影響閱讀計畫

- 報價明細轉工單的粒度。
- 「運送」是否代表最終完工核定。
- 出貨量與備品量的扣庫存定義。
- 製版相關欄位的最後保留範圍。
- 稅額、逐筆取整、付款條件及請款／對帳格式。
- 是否允許超量出貨及核准權限。
- 正式單號格式與角色權限矩陣。

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

本機第一次啟動：

```bash
cp .env.example .env
# 將 .env 的本機 PostgreSQL 密碼換掉後：
docker compose up -d postgres

cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另一個終端啟動前端：

```bash
cd frontend
# 先依 .nvmrc 使用 Node 24 / npm 11
npm ci
npm run dev
```

若這台電腦尚未安裝 nvm／Node 24，可先在 `frontend/` 使用專案包裝器；它會透過現有 `npx` 暫時取得 Node 24 與固定 npm 11.19.0，不依賴不穩定的快取路徑：

```bash
../scripts/npm11.sh ci
../scripts/npm11.sh run dev
```

長期開發仍建議安裝 Node 24 LTS，再依 `.nvmrc` 切換。根目錄 `make test` 會執行文件、Import、後端與前端檢查；目前仍須先完成後端 venv 與前端 `npm ci`。`.env`、資料庫 volume、舊資料、Import 報告與正式資料都不得提交 Git。

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

目前 `frontend/` 與 `backend/` 已有可執行的 Phase 0 骨架，PostgreSQL 由根目錄 `compose.yaml` 啟動；`infra/` 仍只保留責任說明。正式業務資料表、登入、客戶、工單與帳務功能都尚未建立。

## 8. 完成定義

第一版只有在下列條件全部成立時才算完成：

- 可由客戶直接建立工單，也可由報價明細轉成工單。
- 可完整走完工單、製程、最終完工、存貨、出貨、計價、請款及收款。
- 部分完工、部分出貨、多次出貨、備品及沖銷均計算正確。
- 不會超量出貨、重複計價、重複請款或超額收款。
- 單價、版費、刀模費、稅額與取整方式均保存正確快照。
- A4 報價、工單、出貨單及對帳單經公司實際印表機驗收。
- 舊資料完成試匯、核對、正式匯入及抽樣驗收。
- 權限、稽核、附件安全、備份與異機還原均通過測試。
- 兩位使用者可同時操作核心流程。
- 正式切換後仍有已驗證的回復方案。
