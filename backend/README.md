# Backend

FastAPI 後端專案骨架。現階段只提供統一 API 錯誤格式與存活／就緒健康檢查，尚未建立業務資料表、登入或權限。

## 環境

- Python 3.12（專案基準版本）
- FastAPI
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
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可開啟：

- API 文件：`http://127.0.0.1:8000/docs`
- 存活檢查：`http://127.0.0.1:8000/api/v1/health/live`
- 就緒檢查：`http://127.0.0.1:8000/api/v1/health/ready`

目前尚未連接資料庫，因此 `ready` 會明確回傳 HTTP 503 與 `database: not_configured`。Slice 0.5 建立 SQLAlchemy session 後，會注入真實資料庫檢查。`live` 不檢查外部相依，仍會回傳 HTTP 200。

## 測試

```bash
cd backend
source .venv/bin/activate
pytest
```

如要看較完整的輸出：

```bash
pytest -ra
```

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

## 目錄責任

```text
app/
├─ api/v1/       # v1 router 與 health endpoints
├─ core/         # 例外、錯誤 response、readiness 檢查
└─ main.py       # FastAPI app factory 與預設 app
tests/            # API 與核心元件測試
```

核心原則：

- organization scope 將由可信任 session 注入。
- 核心數量及金額只由後端與資料庫保護。
- 高風險操作使用明確 command，不提供任意 status PATCH。
- 完工、出貨、計價、請款及收款在明確交易內處理。
- 作廢／沖銷保留原紀錄與 audit。
- 正式資料不進 seed 或測試 fixture。
