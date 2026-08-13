# 舊系統資料 Import 對照與分批計畫

> 文件版本：v1.2
> 日期：2026-08-13
> 用途：把已提取的真實舊表對應到新版模組，規定每一批何時匯入、如何 dry-run、如何核對，以及何時才允許寫入正式資料。

## 1. Import 不是最後才做

資料 Import 是與功能同步的工作線：

```text
客戶模組完成
→ 試匯客戶
→ 核對
→ 才繼續依賴客戶的模組

工單模組完成
→ 試匯現行／歷史工單
→ 核對

庫存、出貨、計價、帳款模組完成
→ 各自試匯及核對
→ 最後才做全量整合演練
```

這樣可以提早發現 schema 無法表達舊資料，而不是系統做完後才大改。

## 2. 真實來源位置

主要來源：

```text
/Users/kk98033/Documents/公司 2/extraction/export/uv_print_full/tables/
/Users/kk98033/Documents/公司 2/extraction/export/uv_print_full/column_inventory.csv
/Users/kk98033/Documents/公司 2/extraction/ui-analysis/pb_sources/
/Users/kk98033/Documents/公司 2/extraction/ui-analysis/系統功能關聯分析.md
```

Import 程式不得修改上述檔案。正式執行時先複製到受控的唯讀 Import 來源位置並建立 manifest。

P0-10 已於 2026-08-07 定案為「不限年份的全量匯入目標」。全量的定義是每個來源檔與每筆來源資料都有可核對去向，不是把已停用或無法安全 mapping 的內容強塞正式業務表。去向為：

1. 正式業務資料。
2. 只讀歷史封存。
3. 合併／重複並保留 legacy mapping。
4. 例外待人工處理，保留原始 bytes、來源主鍵與原因。

核對報告中上述四類合計必須等於來源邏輯資料筆數，不允許靜默跳過。詳見 ADR-013。

## 3. 資料量盤點

下表多數仍是 2026-08-03 的「非空實體行」初步計數，不等於最終合法 CSV 邏輯筆數。I-0.2 已在 2026-08-04 完成 106 個 CSV 的正式 reader 基線；客戶表已更新為 CSV 邏輯資料筆數，其餘來源仍以各批 Import 報告定案。

| 舊表 | 初步非空資料行 | 用途 |
|---|---:|---|
| `cust` | 221（CSV 邏輯資料列） | 客戶、聯絡與帳務設定 |
| `fact` | 47 | 供應商／協力廠 |
| `wpa` | 9,831 | 客戶常用工作項目與歷史規格 |
| `b_replay1` | 4（CSV 邏輯資料列） | 舊報價主檔 |
| `b_replay2` | 10（CSV 邏輯資料列） | 舊報價明細；4 張報價各有 1～4 筆明細 |
| `subpoena` | 1,448 | 現行工單／製程傳票 |
| `quote` | 1,451 | 現行工單製程明細，不是新版報價單 |
| `subpoena_his` | 18,651 | 歷史工單 |
| `quote_his` | 18,630 | 歷史工單製程明細 |
| `merchandise` | 1,451 | 待出貨存貨與完工／出貨摘要 |
| `subp_sale` | 14,303 | 出貨主檔 |
| `subp_sale2` | 31,162 | 出貨明細 |
| `sal` | 30,499 | 計價主檔初步非空行 |
| `sal2` | 43,464 | 計價明細 |
| `rec` | 378 | 應收彙總 |
| `income` | 16 | 收款紀錄 |
| `lsm` | 353 | 營收／稅額彙總 |
| `subp_paperpru` | 27,344 | 紙張需求／採購歷史；納入全量核對，無新版操作模組時進只讀封存 |

### 客戶筆數差異（I-0.2 已定案）

- 先前輸出連結標示「客戶 221 筆」。
- 正式 CSV reader 讀到 222 個邏輯行（含表頭），因此資料列為 221。
- 221 個第一欄鍵值皆唯一、非空，沒有欄位數不一致。
- 實體行數是 225，因部分欄位含 CSV 合法內嵌換行，不能用逐行工具計數。
- 檔案可用 UTF-8 解碼，但資料列仍含 109 個 `U+FFFD` 與 168 個控制字元，不能據此宣稱文字完整。

因此正式來源資料筆數為 221；「222」是含表頭的邏輯行數，不是客戶數量。詳細證據見 `舊資料來源基線報告.md`。後續 I-0.3／I-1.1 仍必須輸出：

- CSV 邏輯筆數。
- 非空主鍵數。
- 重複主鍵。
- 空白／控制字元。
- Unicode replacement character。
- 欄位數不符的行。
- 可接受、停用與需人工處理筆數。

## 4. 舊表到新模組對照

### 4.1 公司與主檔

| 舊表 | 舊鍵 | 新資料 | Import 動作 |
|---|---|---|---|
| `company` | 依舊表確認 | `organizations` | 建立公司抬頭及聯絡資料；正式設定由公司複核 |
| `cust` | `c_no` | `customers`、`customer_contacts` | 代號、名稱、簡稱、統編、電話、地址、`c_tax`、`bpoint` |
| `fact` | `f_no` | `vendors` | 供應商／協力廠、類別、聯絡、結帳日 |
| `factkind_set` | 類別鍵 | vendor type | mapping 到新版類別，不一定建立獨立業務表 |
| `paper` | 舊紙質鍵 | `paper_types` | 名稱正規化、停用重複值 |
| `factpaper` | 依表欄位 | vendor／paper 關聯 | 保存紙張供應關係，若第一版需要 |
| `gloss`、`paste` | 舊代碼 | 製程選項／歷史文字 | mapping 到上光、裱紙等製程設定 |
| `factgloss`、`factpaste` | 複合鍵 | vendor process capability | 視第一版是否需要建立關聯 |
| `colorset` | 舊代碼 | 不建立新版設定 | 僅保留歷史文字 mapping |
| `cut_set` | 舊代碼 | 不建立新版設定 | 僅保留歷史文字 mapping |

### 4.2 客戶常用工作項目

| 舊表 | 舊鍵 | 新資料 | 注意事項 |
|---|---|---|---|
| `wpa` | `wpano`，並關聯 `c_no` | `customer_work_items` | 規格、紙質、尺寸、顏色、上光、刀模與歷史單價 |

`wpa` 有約 9,831 筆，不能在客戶主頁一次載入；需分頁、搜尋並處理同客戶重複／近似品名。

### 4.2.1 舊報價

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `b_replay1` | `br_no` | `quotations` | 報價日期、客戶、有效期限、付款天數、含稅與整體備註 |
| `b_replay2` | `br_no` → `b_replay1.br_no` | `quotation_items` | 序號、品名、規格、數量、單位、單價、合計與備註 |

PowerBuilder 報價模組沒有找到 `subpoena` 或工單視窗呼叫，也沒有可靠外鍵可把舊報價明細接到舊工單。匯入時保留報價主明細，但不得臆造 `production_cases`、`source_quotation_item_id` 或報價轉工單關係。

### 4.3 現行工單與製程

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `subpoena` | `id`／`idbuffer` | `production_cases`、`work_orders`、materials、print specs | 無可靠群組鍵時每張舊工單建立一個 `legacy_single_work_order` 案件，再匯主工單、紙材、印刷、價格、製版與備註 |
| `quote` | 原設想 `subpoenaid` → `subpoena.id`，但 I-2.1 dry-run 現有匯出 0／1,451 可直接相連 | `work_order_processes`、process history | 這個 `quote` 是製程內容，不可誤匯成新版 `quotations`；取得可靠父鍵前全部列 orphan，不猜關聯 |

重要：舊表名稱 `quote` 容易被誤認為報價單，但從欄位與舊程式關聯可確認它保存設計、製版、曬版、印刷、上光、裱紙、刀模、裁切、運送等工單製程資料。新版報價功能要用新的 `quotations`／`quotation_items`，不可直接把舊 `quote` 當報價。

### 4.4 歷史工單與製程

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `subpoena_his` | 工單舊鍵 | `production_cases`、同一 `work_orders` | 每張歷史工單先建立單工單 legacy 案件；使用 archived／completed 狀態，不建立第二套歷史業務表 |
| `quote_his` | `subpoenaid` | `work_order_processes`／歷史事件 | 和歷史工單配對 |

現行與歷史可能有相同業務單號。Import 必須先定義去重鍵與優先順序，不能只靠單號直接 INSERT。

ADR-018 定案後，每類舊文件都必須保存 `legacy_document_number`、`legacy_source_table` 與 `legacy_source_key`；舊號原樣顯示與搜尋，不加 `QUO`／`WO`／`SHP` 等前綴。新 sequence 只從新系統正式建單開始配發。

### 4.5 完工與待出貨

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `merchandise` | `subpoenaid` | `final_completion_entries`、`inventory_ledger` 或期初餘額 | `finishnumber`、`delivernumber`、`sparenumber` 用於核對 |
| `subp_replenish` | 依欄位確認 | adjustment／completion evidence | 是否代表補數或調整需從程式確認 |

若無法從歷史事件還原每一次完工，不得偽造多筆完成日期。使用一筆明確標示 `legacy_opening_inventory` 的期初流水，並保存原始完工、出貨、備品摘要作核對。

P0-04 新版「基礎計價只取正式量」不回溯改寫舊金額。舊備品計價依可取得的實際 `sal`／`sal2` 或對帳紀錄原樣匯入；無法證明時進差異報告，不以新公式重算。

### 4.6 出貨

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `subp_sale` | `deliverid` | `shipments` | 出貨日期、客戶、備註、列印狀態 |
| `subp_sale2` | `deliverid` → 主檔；`subpoenaid` → 工單 | `shipment_items` | 正式出貨、備品、單價、價格、`tr_ok` |

核對：

- 每個 `subp_sale2.deliverid` 都應找到主檔或進 orphan 報告。
- 每個來源 `subpoenaid` 能找到現行或歷史工單，找不到則列例外。
- `delivernumber` 與 `sparenumber` 分欄匯入。
- 舊 `tr_ok` 只作計價狀態佐證，真正來源仍以 `sal`／`sal2` 關聯核對。

### 4.7 計價

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `sal` | `sal_da + sno`；`deliverid` | `pricing_documents`／基礎 pricing item | 客戶、品名、數量、合計、來源出貨 |
| `sal2` | `sal_da + sno` | `pricing_items` | 內容、數量、單價、小計 |
| `sal_copy` | 依欄位確認 | 歷史／暫存 | 先判讀用途，不能與正式 sal 重複匯入 |

計價匯入後必須能由 `pricing_item` 回到來源出貨明細；無法逐筆對到來源者使用明確 legacy link 狀態並列入報告。

### 4.8 應收與收款

| 舊表 | 關聯 | 新資料 | 注意事項 |
|---|---|---|---|
| `lsm` | `yrmn + c_no` | 月度核對摘要 | 不一定直接成為正式 transaction；可作 reconciliation |
| `rec` | `idno + yrmn` | legacy receivable／statement balance | 需確認 `idno` 與客戶關聯 |
| `income` | `c_no + yrmn` 等 | `receipts`、allocations 或 opening receipt | 目前筆數少，逐筆人工抽查 |
| `rece` | 依欄位確認 | 收款／應收補充 | 先確認與 `rec`、`income` 的角色，避免重複 |

若舊系統只保存月度彙總而無法還原逐張請款分配，使用：

- `legacy_opening_statement`。
- `legacy_opening_receivable`。
- `legacy_unallocated_receipt`。

這些類型必須在 UI 標示為「舊系統期初資料」，不能假裝是新版正常流程產生。

### 4.9 紙張採購歷史

| 舊表 | 新方向 | 第一版決策 |
|---|---|---|
| `subp_paperpru` | 紙張需求／採購 | 全量納入；若第一版不做紙張採購模組，放入只讀歷史封存，不塞入工單材料表 |
| `subp_paperprein` | 紙張預進貨／暫存 | 同上，每筆來源仍需有封存 mapping 或例外記錄 |

大量紙張採購資料不能因表存在就擴大第一版範圍。

## 5. Import 平行工作線

| Import Slice | 在哪個功能後進行 | 匯入範圍 | 驗證 Gate |
|---|---|---|---|
| I-0.1 | Phase -1 | source manifest、雜湊、檔案與表清單 | 同一來源重跑結果一致 |
| I-0.2 | Phase -1 | CSV reader、編碼、邏輯筆數、欄位數 | `cust` 221／222 差異有正式報告 |
| I-0.3 | Phase -1 | staging、import run、error、mapping schema 設計 | migration 尚不寫正式業務表 |
| I-1.1 | DONE（未 apply） | `cust` 221 筆 aggregate-only dry-run | 無重複代號；109 個替代字元待修復／抽查 |
| I-1.2 | DONE（未 apply） | `fact`、paper、gloss、paste aggregate-only dry-run | 筆數與重複統計已產生；mapping／停用仍須簽認 |
| I-1.3 | DONE（未 apply） | `wpa` 9,831 筆全量 aggregate-only dry-run | 189 筆孤兒、6 筆缺客戶代號、1 筆缺名稱待處理 |
| I-1.4 | DONE（未 apply） | `b_replay1`＋`b_replay2` aggregate-only dry-run | 4 主檔／10 明細；3 筆明細缺 `br_no`、其餘 7 筆也無法對上 4 個主檔號，正式匯入前須回查來源；金額格式 10／10 可解析，不臆造工單關係 |
| I-2.1 | DONE（未 apply） | `subpoena`＋`quote` 現行工單 aggregate-only dry-run | 1,451 筆製程父鍵全數未命中，取得可靠 join 前不得試匯 |
| I-2.2 | Phase 4 history 完成 | `subpoena_his`＋`quote_his` | 現行／歷史去重、狀態及數量 |
| I-3.1 | DONE（未 apply） | `merchandise` 1,451 筆 aggregate-only dry-run | 數量皆可解析且餘額皆為正；8 碼 `subpoenaid` 對 11 碼工單號直接命中 0，日期前綴候選不可當正式關聯 |
| I-4.1 | DONE（未 apply） | `subp_sale`＋`subp_sale2` aggregate-only dry-run | 14,303 主檔／31,162 明細；5 筆缺主檔鍵、31,152 筆明細主鍵未直接命中、工單只直接命中 8 筆；不得猜測關聯 |
| I-5.1 | Phase 7 pricing 完成 | `sal`＋`sal2` | 來源出貨、防重複、金額總計 |
| I-6.1 | Phase 8 billing 完成 | `rec`、`income`、`lsm`、`rece` | 客戶／月份、稅額、已收／未收核對 |
| I-7.1 | Phase 10 | 不限年份全模組整合 dry-run，含只讀封存與例外清單 | 零未解高風險錯誤，所有來源列皆有去向 |
| I-7.2 | Phase 10 | 第二次完全重跑 | idempotent，不新增重複資料 |
| I-8.1 | Phase 12 | 最終差異匯入 | 公司簽認筆數、數量、金額 |

I-2.1 已於 2026-08-13 完成 aggregate-only dry-run：目前 CSV 讀得 `subpoena` 1,431 筆、`quote` 1,451 筆；`quote.subpoenaid` 對 `subpoena.id`、`idbuffer`、`ordernumber`、`orderid` 的直接命中皆為 0。報告沒有輸出客戶、品名或製程內容，且 `apply_performed=false`。下一步必須回查舊程式實際 join／另一版匯出或請公司提供可核對樣本，不能以列序或相似文字臆造父子關係。

I-3.1 已於 2026-08-13 完成 aggregate-only dry-run：`merchandise` 讀得 1,451 筆，`finishnumber - delivernumber - sparenumber` 全部可解析且目前均為正值；來源包含 5,804 個 NUL bytes，dry-run 只在記憶體移除並保留原檔 SHA-256。`merchandise.subpoenaid` 為 8 碼日期型參考，對 11 碼 `subpoena.id` 直接命中 0；日期前綴雖有候選但可能一對多，禁止據此 apply。報告不含客戶、品名或逐列值，且 `apply_performed=false`。

I-4.1 已於 2026-08-13 完成 aggregate-only dry-run：`subp_sale` 讀得 14,303 筆主檔、`subp_sale2` 讀得 31,162 筆明細，正式出貨與備品數量欄全部可解析且沒有負數。舊明細有 5 筆缺 `deliverid`、31,152 筆非空 `deliverid` 無法直接命中本次主檔，`subpoenaid` 也只有 8 筆直接命中匯出的工單 ID；因此 `apply_performed=false`，不以列序、日期或客戶／品名相似度猜關聯。報告只保存 aggregate 與來源雜湊，不含客戶、品名、地址、備註或逐列內容。

每個 Import Slice 都是小切片，必須各自測試、更新進度及 commit；不能把全部 Import 寫成一個超大腳本。

I-0.1～I-0.3 與 I-1.1～I-1.3 dry-run 已完成。報告只保存雜湊、筆數與錯誤分類，不含客戶／工作項目值，且全部 `apply_performed=false`。目前正式 apply 仍被 `cust` 轉碼替代字元與 `wpa` 孤兒／缺鍵阻擋；修復來源或簽認 mapping 後必須重跑相同 dry-run 才能進入 staging／apply。

## 6. 預定程式結構

```text
backend/app/modules/imports/
├─ api.py
├─ models.py
├─ schemas.py
├─ services/
│  ├─ manifest.py
│  ├─ run_manager.py
│  ├─ staging.py
│  ├─ apply.py
│  └─ reconciliation.py
├─ readers/
│  └─ uv_print_csv.py
├─ transforms/
│  ├─ text.py
│  ├─ dates.py
│  ├─ decimals.py
│  └─ identifiers.py
├─ mappings/
│  ├─ customers.py
│  ├─ vendors.py
│  ├─ work_orders.py
│  ├─ inventory.py
│  ├─ shipments.py
│  ├─ pricing.py
│  └─ billing.py
└─ reports/
```

共用 reader 負責 CSV quoting、換行、編碼與原始行號；domain mapping 不自行重寫 CSV parser。

## 7. 預定操作命令

以下是計畫介面，尚未實作；真正命令在 Slice I-0 建立：

```bash
make import-manifest SOURCE_DIR=/approved/read-only/source
make import-dry-run RUN_ID=<id> DOMAIN=customers
make import-report RUN_ID=<id>
make import-apply RUN_ID=<id> DOMAIN=customers
make import-reconcile RUN_ID=<id> DOMAIN=customers
```

正式 apply 額外要求：

- 指定 organization。
- 指定已核准 run ID。
- 檔案雜湊與 dry-run 完全相同。
- 目標環境明確顯示。
- 正式環境需要二次確認或維護者權限。
- apply 前已有可還原備份。

## 8. Import Run 狀態

```text
created
→ manifested
→ staged
→ validated
→ awaiting_approval
→ applying
→ applied
→ reconciled
→ accepted

任一階段 → failed
已套用但未通過核對 → reconciliation_failed
```

不得跳過 `validated` 與 `awaiting_approval` 直接 apply。

## 9. Dry-run 報告

每個 domain 至少輸出：

- Source manifest hash。
- Reader／mapping 程式版本與 Git commit。
- 實體行、CSV 邏輯筆數。
- 成功、警告、錯誤、跳過筆數。
- 空主鍵、重複主鍵、無效日期／Decimal。
- Unicode／控制字元問題。
- 主檔找不到、孤兒外鍵。
- 將新增、更新、保持不變的數量。
- 會建立的 legacy opening／unresolved link 數量。
- 抽樣前後值，但報告不得無必要地輸出完整個資。

## 10. 分批 apply 策略

### 開發／測試環境

- 可整個測試 DB 重建。
- 先用 10～50 筆 fixture。
- 再用完整來源 dry-run。
- apply 後刪除 DB 重跑，驗證結果一致。

### UAT 環境

- 匯入完整範圍。
- 公司抽樣客戶、工單、出貨、計價、未收款。
- 問題修正 mapping 後建立全新 DB 重跑，不在錯誤結果上大量手改。

### 正式環境

- 先匯主檔並核對。
- 再按工單、庫存、出貨、計價、帳款依賴順序套用。
- 每個 wave 都有前後核對與 checkpoint。
- 高風險錯誤立即停止後續 wave。

## 11. 核對門檻

### 主檔

- 所有有效來源主鍵必須匯入或出現在已簽認例外清單。
- 不允許無報告地丟資料。
- 重複合併必須保存每個來源鍵 mapping。

### 關聯

- 新系統正式資料不得有無效外鍵。
- 舊孤兒資料必須列例外或匯入明確 legacy unresolved 類型。

### 數量

對可完整對應的每張工單：

```text
舊完工量 - 舊正式出貨量 - 舊備品量 = 新版可出貨量
```

差異不得只看全公司合計；必須逐工單列出。

### 金額

- 計價、稅額、請款、已收及未收使用 Decimal 核對。
- 逐客戶、逐月份及全公司三層核對。
- 因舊取整造成的差異必須有明確規則及報告。

## 12. Git 與資料安全

進 Git：

- Import reader、mapping、migration、測試。
- 不含個資的欄位字典及統計格式。
- 虛構／去識別 fixture。
- Sanitized reconciliation summary。

不進 Git：

- 原始 CSV、MDF、資料庫 dump。
- 客戶姓名、電話、地址及統編明細。
- Import staging 匯出。
- 錯誤報告中的完整個資。
- 正式附件。

每完成一個 Import wave：

1. 更新 README 目前進度。
2. 更新詳細進度與 Import run ID。
3. 提交程式與測試。
4. 中型 wave 建立 checkpoint tag、bundle 及遠端 push。
5. 原始資料及正式 report 依資料備份政策另存，不用 Git 當資料備份。

## 13. Import 完成定義

- 所有核准範圍已有 source manifest。
- 所有匯入資料可追到來源表與來源主鍵。
- 客戶筆數差異已有解釋與公司簽認。
- 現行／歷史工單沒有錯誤重複。
- 庫存逐工單核對通過。
- 出貨主明細與工單來源通過。
- 計價主明細與出貨來源通過。
- 請款、稅額、已收、未收依客戶／月份核對通過。
- 完整 Import 可在乾淨 DB 重跑。
- 第二次相同來源執行不產生重複資料。
- 例外清單已由公司接受。
- 最終 apply 前後都有可還原備份。
