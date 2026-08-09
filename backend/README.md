# Backend

FastAPI 後端專案骨架。現階段提供環境防呆、統一 API 契約、真實資料庫就緒檢查、SQLAlchemy／Alembic、Import staging／trace，以及 Phase 1 identity schema。尚未建立登入 API、Cookie、角色權限或正式業務流程資料表。

## 環境

- Python 3.12（專案基準版本）
- FastAPI
- SQLAlchemy 2 同步模式
- Alembic
- Psycopg 3 binary distribution
- Uvicorn
- Pytest

請不要在 Python 3.8 環境安裝；本專案使用 Python 3.12 作為 Phase 0 的後端基準。

## 初次安裝

以 macOS/Linux 為例：

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Windows PowerShell：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 啟動

```bash
cd company-system
cp .env.example .env
# 只需更換 POSTGRES_PASSWORD；DATABASE_URL 會引用同一組 PostgreSQL 變數
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

後端在建立 FastAPI app 前就會載入專案根目錄的 `.env`。`.env.example` 的 `DATABASE_URL` 由 `POSTGRES_USER`、`POSTGRES_PASSWORD`、host、port 與 database name 展開，避免同一密碼改兩次後不一致。系統環境變數優先於 `.env`；缺少必要值、格式錯誤或資料庫環境不符時，啟動會立即失敗，不會先用不安全的預設值繼續執行。

若 `.env` 是 Slice 0.2 之前建立的舊檔，請先把其中的 `DATABASE_URL` 更新成目前 `.env.example` 的變數引用寫法，再設定 `POSTGRES_PASSWORD`；不要只改密碼卻保留舊的完整範例 DSN。`.env` 是本機私密設定且不納入 Git，程式不會自動覆寫。

### 必要環境變數

| 變數 | 用途 | 規則 |
|---|---|---|
| `APP_ENV` | 執行環境 | 僅允許 `development`、`test`、`production` |
| `APP_HOST` | 本機 API 綁定位址 | 不可為空 |
| `APP_PORT` | 本機 API port | 1–65535 |
| `DATABASE_URL` | PostgreSQL DSN | 必須含帳號與密碼，資料庫名稱與帳號都要隔離；視為 Secret，錯誤訊息不回顯連線值 |

### 資料庫環境隔離

`DATABASE_URL` 目前僅允許 PostgreSQL，而且資料庫名稱與資料庫帳號都必須含有和 `APP_ENV` 對應的獨立標記：

| `APP_ENV` | 資料庫與帳號命名規則 | 範例 |
|---|---|---|
| `development` | 含 `_dev` 或 `-dev` | `company_system_dev` |
| `test` | 含 `_test` 或 `-test` | `company_system_test` |
| `production` | 含 `_prod` 或 `-prod` | `company_system_prod` |

比對的是 DSN path 中實際的資料庫名稱，以及 DSN username，不會用整段 URL 做寬鬆字串搜尋。名稱或帳號只能出現當前環境標記；`company_system_dev_test` 這類混合標記也會被拒絕。因此即使密碼含 `test`，測試環境仍不能連到 `company_system_dev`。`.env.example` 的範例密碼也會被拒絕。

日後 SQLAlchemy 只可透過 `AppSettings.database_url_value()` 取得 DSN，不可自行再讀取 `os.environ`。

可開啟：

- API 文件：`http://127.0.0.1:8000/docs`
- 存活檢查：`http://127.0.0.1:8000/api/v1/health/live`
- 就緒檢查：`http://127.0.0.1:8000/api/v1/health/ready`

`ready` 會透過 SQLAlchemy 執行 `SELECT 1`；資料庫停止或連線失敗時回傳 HTTP 503，且不回顯 DSN、密碼或 driver exception。`live` 不檢查外部相依，仍會回傳 HTTP 200。

development 與 test 環境會開啟 `/docs` 及 `/openapi.json`；production 環境會同時關閉這兩個入口，避免對外暴露 API 結構。OpenAPI 中的共通 4xx、422 與 500，以及真正可能未就緒 endpoint 的 503，均宣告為同一 `ErrorResponse` envelope；`live` 不會錯誤宣告 503。

前端 client 的權威來源是離線匯出的 FastAPI OpenAPI，不需啟動 API 或連接資料庫：

```bash
cd ..
./scripts/generate-api-client.sh          # 更新 snapshot 與 generated client
./scripts/generate-api-client.sh --check  # 在暫存目錄重產並檢查 drift
```

產生流程對匯出器注入固定 test-only 設定，並使用排序穩定的 UTF-8 JSON 與唯一 snake_case operation ID。`frontend/openapi/` 及 `frontend/src/api/generated/` 要提交 Git，但 generated client 禁止手改。

## 測試

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

如要看較完整的輸出：

```bash
python -m pytest -ra
```

設定測試包含：

- 必要變數缺少時同次列出所有缺項。
- process environment 正確覆寫 `.env`。
- development、test、production 的資料庫名稱與帳號都不得交叉或混用環境標記。
- 驗證失敗與 `repr` 不得曝露 DSN 內的密碼。

## 資料庫 session 與 lifecycle

- 每個 FastAPI app 擁有一組 lazy engine 與 session factory；建立 app 不會立即連線。
- 小型 VM 預設 pool 為 5 connections、2 overflow、5 秒 timeout，並開啟 `pool_pre_ping`。
- request dependency 只負責 rollback-on-error 與 close，不自動 commit；後續 service 必須明確擁有 transaction boundary。
- `create_app(database_resources=...)` 的注入即代表把 ownership 移交給該 app；FastAPI shutdown 會 dispose engine，不得把同一個 resources 共用給多個 app。
- SQLAlchemy 關閉 parameter log，並只使用設定層驗證過的 PostgreSQL DSN。

## Alembic migration

Alembic 設定在 `alembic.ini`，版本檔在 `migrations/versions/`。`0001_empty_baseline` 是空白起點；`0002_import_staging` 建立 run／source file／staging，`0003_import_trace` 建立 errors／mappings；`0004_identity_foundation` 建立 organizations／users／organization_members／sessions。`0004` 不建立 seed、角色、權限或登入行為，也不建立 `customers` 等正式業務流程資料。應用程式啟動不會自動 migration。

Identity schema 的邊界：

- `users.login_name` 是全域使用者代號，trim 且不分大小寫後唯一；不把 email 擅自設為必填。
- `organization_members` 只表達使用者屬於哪間公司；角色與 capability 留在 Slice 1.6。
- `sessions` 只保存 64 字元的小寫 SHA-256 token digest 並綁定 membership；禁止保存 raw cookie token。
- 父資料有 membership／session 時使用 `RESTRICT`，不以 cascade 抹除身分軌跡。
- Slice 1.2 才加入可重跑的 test-only seed，且必須使用有效 Argon2id 雜湊。

一般 `make backend-test` 會排除整合測試，不需要 Docker。要用完全隔離的 PostgreSQL 驗證真實連線與 `upgrade -> downgrade -> upgrade`：

```bash
cd ..
make backend-database-integration-check
```

`postgres-test` 只綁定 `127.0.0.1:5433`、資料庫名與 username 均含 `_test`，並使用 tmpfs，不與 development volume 共用資料。專案內只提供明確非正式用途的本機 test-only 預設密碼；CI 或共用環境可以 `POSTGRES_TEST_PASSWORD` 覆寫。Make target 無論成功或失敗都會停止 test container，不會刪除 development volume。

當需要人工驗收停機行為時，先啟動 API 再停止 PostgreSQL；`live` 應持續 200，`ready` 應變為 503，重啟 PostgreSQL 後 `ready` 應恢復 200。

## Import staging 與 trace

`app/modules/imports/models/` 目前只定義五個 infrastructure models：

- `import_runs`：manifest hash、importer version、既定 run lifecycle 與彙總計數。
- `import_source_files`：相對路徑、來源表、SHA-256、檔案大小、實體行、含表頭邏輯列與資料列。
- `import_staging_records`：來源檔／表／列／key，以及可比較的 raw／normalized JSONB。
- `import_errors`：run／file／row／field scope 與處理狀態。
- `legacy_mappings`：跨 run 的來源 identity 唯一鍵與 target UUID。

複合外鍵會拒絕 file、staging、error 與 mapping 互相矛盾的來源資訊；同一 manifest／檔案允許建立新 run 重跑，但同一來源 identity 不得因 run ID 不同而建立第二個相同 mapping。所有目前測試資料都是 synthetic canary；不得把 221 筆客戶、真實名稱、地址、電話或原始 payload 放進 fixture、log 或 Git。

I-0.3 不提供 Import API、reader service、domain mapping、dry-run 或 apply。`import_staging_records` 是正式 schema 未簽認前的通用 envelope，不是未來客戶／工單的正式 JSONB 模型。I-1.1 前還要補 raw PII 的管理者權限、保留／清除政策，以及禁止錯誤訊息拼接 raw value 的規則。

## API 錯誤格式

所有已處理的 HTTP、輸入驗證、應用程式與未預期錯誤都使用同一外層：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "請檢查輸入資料",
    "details": []
  }
}
```

`details` 可為 `null`、清單或物件；前端應先依 `code` 判斷錯誤類型，不可解析 `message` 文字當作業務規則。

輸入驗證錯誤只會回傳欄位位置、穩定類型與固定安全文案，不回顯 Pydantic 的 `input`、`ctx`、`url` 或 validator 自訂文字。未預期錯誤的 log 只記錄 exception type，不記錄例外文字或 stack trace；需向前端公開的細節必須明確使用 `ApplicationError`。

## 列表 API 契約

`app.api.contracts` 提供不依賴資料庫的共用 primitive：

| 契約 | 規則 |
|---|---|
| `PageParams` | `page` 預設 1、上限 1,000,000；`page_size` 預設 25、上限 100，並提供 zero-based `offset` |
| `SortParams[DomainSortField]` | `sort_by` 必須使用 endpoint 所屬 domain 定義的 `StrEnum`；不接受裸字串或任意 SQL 欄位 |
| `KeywordParams` | 通用 `keyword` 上限 100 字元，前後空白會移除，全空白視為未篩選 |
| `DateRangeParams` | 通用含頭含尾 `date_from` / `date_to`，禁止起日晚於迄日；FastAPI 請透過 `parse_date_range_params` dependency 使用 |
| `PaginationMeta` | 回傳總筆數、總頁數、前／後頁狀態 |
| `ListResponse[Item, FilterSummary]` | 回傳 `items` 與含 pagination、實際 sort、當前 filters 的 `meta` |

`status` 不是共通字串篩選：後續各 domain 必須定義自己的 status enum。`customer_id` 也要等 ID 與 organization scope 契約完成後由 domain 加入，不在共通 primitive 預先假設。

`date_from`／`date_to` 只適用於 endpoint 已明確定義唯一「主要日期」的情況，而且 OpenAPI 說明必須指出它代表建立日、交期、開立日或其他日期。同一列表若需要查詢兩種日期，不得重複套用這個 FastAPI dependency；應由 domain 定義 `delivery_date_from` 等明確欄位，再重用純日期區間驗證。

endpoint-specific 排序寫法：

```python
class CustomerSortField(StrEnum):
    CODE = "customer_code"
    NAME = "customer_name"


class CustomerSortParams(SortParams[CustomerSortField]):
    sort_by: CustomerSortField = CustomerSortField.CODE
```

在 FastAPI handler 以 `Annotated[CustomerSortParams, Depends()]` 注入，OpenAPI 會列出允許值，非白名單欄位會在進入 query/repository 前回傳 422。一般列表不得把 `page_size` 放大或繞過分頁；大量匯出必須另建有權限的專用 endpoint。

列表 response 形狀：

```json
{
  "items": [],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 25,
      "total_items": 0,
      "total_pages": 0,
      "has_previous": false,
      "has_next": false
    },
    "sort": {"field": "customer_code", "direction": "asc"},
    "filters": {"keyword": null}
  }
}
```

## 目錄責任

```text
app/
├─ api/
│  ├─ contracts/ # 列表、OpenAPI 等可重用 HTTP 契約
│  └─ v1/        # v1 router 與 health endpoints
├─ core/
│  ├─ config/   # 設定模型、載入順序、資料庫環境防呆
│  ├─ database/ # engine、session、metadata、readiness 與 lifecycle
│  ├─ errors.py # 統一例外與 API error response
│  └─ readiness.py # 可注入的就緒檢查
├─ modules/
│  ├─ auth/          # user／session schema；登入行為尚未實作
│  ├─ imports/       # Import run／source／staging／error／mapping；無正式資料 apply
│  └─ organizations/ # organization／membership schema；角色尚未實作
└─ main.py       # FastAPI app factory 與預設 app
migrations/        # Alembic 可回復 migration；目前到 0004 identity foundation
tests/             # API、核心元件及明確標記的 DB integration 測試
```

命名與模組原則：

- Python 模組、函式與變數使用 `snake_case`，class 使用 `PascalCase`。
- 每個模組只負責一類工作；`models.py` 不讀檔案，`loader.py` 不處理業務規則。
- 其他模組從 `app.core.config` 公開介面匯入，不依賴內部檔案位置。
- 測試用 settings 由 `tests/settings_factory.py` 統一建立，不在每個 API 測試重複 DSN。

核心原則：

- organization scope 將由可信任 session 注入。
- 核心數量及金額只由後端與資料庫保護。
- 高風險操作使用明確 command，不提供任意 status PATCH。
- 完工、出貨、計價、請款及收款在明確交易內處理。
- 作廢／沖銷保留原紀錄與 audit。
- 正式資料不進 seed 或測試 fixture。
