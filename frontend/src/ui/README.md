# 共用 UI 開發規則

此目錄是正式 React UI 的唯一共用元件入口。完整規格見專案根目錄的 `docs/UI設計系統與通用版型.md` 與 ADR-010。

新增頁面時：

1. 先選擇總覽、清單查詢、新增／編輯、詳細資料、主從明細、Modal／Drawer、系統狀態或列印版型。
2. 優先組合本目錄元件，不在 feature 建立另一套 PageHeader、Button、Field、Status 或 Table 視覺。
3. 缺少能力時先擴充成跨模組可用元件，使用 `tokens.css`，同時補 RWD、鍵盤、空／錯誤／權限狀態與測試。
4. 執行 `npm run check:ui`、lint、typecheck、test、build 與人工尺寸驗證。

`StylePreviewPage` 只保存歷史比較，不是可複製的正式元件來源。

## Public boundary 與檔案責任

正式頁面一律由 `../ui/UiPatterns` 匯入，不直接依賴內部責任檔。這個 public boundary 保留既有 export 名稱，內部目前拆為：

- `PagePatterns.tsx`：PageHeader、KpiStrip、Section。
- `FormPatterns.tsx`：FilterBar、Field。
- `InformationPatterns.tsx`：StatusLabel、DataTableFrame、DefinitionGrid。
- `SystemState.tsx`：全頁與區塊系統狀態。

對應 CSS 由 `main.tsx` 依「頁面結構、表單、資訊、系統狀態、版型示範」順序載入。每個責任檔自帶自己的 RWD 規則；新增檔案或改變順序時必須同步 `scripts/check-ui-conformance.mjs` 的明確 manifest，不可把 media query 集中到無責任歸屬的補丁檔。
