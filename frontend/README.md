# Frontend

公司管理系統的 React＋TypeScript 前端。目前只完成 Phase 0 工程骨架，尚未連接正式 API，也不包含任何真實公司資料。

## 環境

- Node.js 24 LTS（以 `frontend/.nvmrc` 為基準）
- npm 11.x

## 開發指令

```bash
nvm use
npm ci
npm run dev
```

開發伺服器預設為 `http://localhost:5173`。後端建立後，`/api` 會由 Vite 代理至 `http://localhost:8000`。

目前可用頁面：

- `/`：Phase 0 工程首頁。
- `/style-preview`：A 平面工業 ERP、B 現代桌面 ERP、C Bootstrap 企業版的互動比較；全部使用假資料，尚未選定正式風格。

## 驗證指令

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

`npm run test:watch` 可在開發時持續執行 Vitest。

## 目錄原則

```text
src/
├─ app/          Router、Providers、ErrorBoundary 與桌面版 Layout
├─ pages/        首頁與共用狀態頁；業務頁面後續移入 features
├─ styles/       可替換的 Design Tokens 與全域樣式
└─ test/         Vitest 與 Testing Library 共用設定
```

- 後端資料一律由 TanStack Query 管理。
- 不在前端自行決定庫存、稅額、單號或權限結果。
- 本機介面只使用專案 CSS tokens；依架構基準導入 Ant Design 時，不得混用第二套完整 UI framework。
- 業務功能必須依 `../03_最終實作計畫.md` 的 Slice 順序新增。
