# 共用 UI 開發規則

此目錄是正式 React UI 的唯一共用元件入口。完整規格見專案根目錄的 `docs/UI設計系統與通用版型.md` 與 ADR-010。

新增頁面時：

1. 先選擇總覽、清單查詢、新增／編輯、詳細資料、主從明細、Modal／Drawer、系統狀態或列印版型。
2. 優先組合本目錄元件，不在 feature 建立另一套 PageHeader、Button、Field、Status 或 Table 視覺。
3. 缺少能力時先擴充成跨模組可用元件，使用 `tokens.css`，同時補 RWD、鍵盤、空／錯誤／權限狀態與測試。
4. 執行 `npm run check:ui`、lint、typecheck、test、build 與人工尺寸驗證。

`StylePreviewPage` 只保存歷史比較，不是可複製的正式元件來源。
