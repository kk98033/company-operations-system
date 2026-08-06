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

- `/`：Phase 0 工程首頁，使用正式 ADR-010 UI。
- `/customers`、`/quotations`、`/work-orders`、`/production`、`/inventory`、`/shipments`、`/pricing`、`/statements`、`/receipts`：九個公司主流程的 Phase 0 可點擊路由原型；只描述責任與交接，尚無正式功能或資料。
- `/ui-patterns`：總覽、清單、表單與詳細資料的正式共用版型；全部使用假資料。
- `/style-preview`：A／B／C 的歷史比較證據；不是正式 UI，不得加入業務功能。

## 驗證指令

```bash
npm run lint
npm run check:ui
npm run typecheck
npm run test
npm run test:a11y
npm run build
```

`npm run test` 已包含 accessibility 測試；`npm run test:a11y` 可單獨執行 axe-core 的 WCAG A／AA 與 best-practice 基線。`npm run test:watch` 可在開發時持續執行 Vitest。色彩與實際焦點仍須用瀏覽器人工確認。

## 目錄原則

```text
src/
├─ app/          Router、主流程模組目錄、Providers、ErrorBoundary 與桌面版 Layout
├─ pages/        首頁、流程原型與共用狀態頁；正式業務頁後續移入 features
├─ ui/           ADR-010 跨模組共用元件與開發規則
├─ styles/       正式 Design Tokens、殼層、共用元件及歷史預覽樣式
└─ test/         Vitest 與 Testing Library 共用設定
```

- 後端資料一律由 TanStack Query 管理。
- 不在前端自行決定庫存、稅額、單號或權限結果。
- 正式介面已依 ADR-010 鎖定 A 平面工業架構＋C 表單清晰度；只使用專案 tokens 與共用元件。
- `npm run lint` 會同時執行 UI conformance；新頁面不得自創另一套視覺。
- 九個流程名稱、順序、路徑與原型責任集中在 `src/app/workflowModules.ts`；不得在側邊欄或其他頁面另建重複清單。
- 業務功能必須依 `../03_最終實作計畫.md` 的 Slice 順序新增。
