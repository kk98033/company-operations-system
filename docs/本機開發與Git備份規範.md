# 本機開發與 Git 備份規範

> 目的：確保每一小步可驗證、可回復；每個中型進度有獨立版本與第二份備份。

## 1. 開發環境原則

- 第一階段在開發者電腦實作與測試。
- PostgreSQL 使用 Docker volume；正式資料不得放入本機開發 DB。
- React 與 FastAPI 可本機熱更新，另以 Compose 驗證完整容器環境。
- 所有啟動、migration、seed、test、build、backup 命令放進 Makefile 或 scripts，不依賴個人記憶。
- README 是新電腦復原的第一入口。

## 2. Git repository 範圍

新版 repository 根目錄是 `company-system/`。

提交：

- 前端、後端、infra、migration、測試。
- Markdown 文件。
- `.env.example`。
- 不含秘密的設定模板。
- 小型、虛構測試 fixture。

不得提交：

- `.env` 與正式 Secret。
- `node_modules`、virtualenv、cache、build artifact。
- 本機 PostgreSQL volume。
- 正式資料庫 dump、CSV、客戶資料。
- 真實附件、刀模圖或列印文件。
- Cloud service account key。
- 開發者私人憑證。
- 專案外的 `analysis/`、`extraction/` 原始大量資料。

## 3. 分支原則

初期單一開發者：

- `main` 始終保持已驗證、可啟動。
- 每個 Slice 可使用 `slice/<id>-<short-name>` 分支。
- 小型 Slice 也可在 main 完成，但 commit 前必須通過該 Slice 測試。

多人開發後：

- 每個 Slice 使用獨立分支及 Pull Request。
- PR 必須列需求 ID、測試證據、migration 影響及 screenshot，適用時。
- 未通過 review 與 CI 不合併 main。

## 4. Commit 規則

建議格式：

```text
docs(plan): establish implementation baseline
chore(dev): add local postgres compose
feat(customers): add customer search API
fix(shipments): prevent concurrent over-shipment
test(billing): cover per-line rounding
refactor(work-orders): split material form sections
```

每個 commit：

- 只處理一個清楚目的。
- 不混入無關格式化或私人檔案。
- 必須能說明驗證方式。
- migration 與依賴該 migration 的最小程式可在同一 Slice，但不要混入下一個功能。
- 不以 `wip` commit 當中型 checkpoint。

## 5. 小切片完成程序

1. 執行該 Slice 的測試。
2. 執行受影響範圍 lint／typecheck。
3. 人工走一次驗收步驟。
4. 更新 `README.md`：目前階段、目前切片、完成度、已完成、進行中、下一步。
5. 更新 `docs/progress/實作進度紀錄.md`。
6. 檢查 `git diff`，確認沒有 Secret／正式資料。
7. 建立 commit。
8. 記錄 commit hash。

## 6. 中型進度定義

以下任一成立：

- 一個 Phase 完成。
- 連續完成 3～5 個相關 Slice，已形成可展示、可回復成果。
- 核心 migration、資料移轉或正式部署前的安全基準。
- 公司完成一次簽認。

中型進度必須額外：

1. 執行完整適用測試集合。
2. 更新所有主文件版本及 README。
3. 建立明確 checkpoint commit。
4. 建立 annotated Git tag。
5. 建立 Git bundle 到 repository 外的 `../git-backups/`。
6. 推送 main／目前分支與 tag 到私人遠端。
7. 定期抽樣用 bundle 或遠端 clone 還原。

## 7. Checkpoint script

使用：

```bash
./scripts/create-checkpoint.sh phase-0
```

腳本應：

- 拒絕 dirty worktree。
- 驗證 checkpoint 名稱。
- 建立 annotated tag `checkpoint-<名稱>`。
- 建立 `../git-backups/company-system-<名稱>-<日期>.bundle`。
- 驗證 bundle。
- 若有 `origin`，推送目前分支及新 tag。
- 沒有 origin 時顯示明確警告，不假裝已完成異機備份。

## 8. 遠端 repository

要求：

- 使用私人 GitHub、GitLab 或公司核准的 Git server。
- repository 及付費／擁有權由適當的公司或專案帳號持有。
- 開啟 MFA。
- 不把正式資料放進 issue 或 PR 附件。
- main 可設定保護及必要 CI。

尚未建立遠端時：

- 本機 commit 與 bundle 繼續執行。
- README 必須顯示「遠端未設定」。
- 在 Phase 1 完成前設定遠端；不得拖到正式上線才處理。

## 9. 為什麼 commit 不等於備份

`.git` 與工作檔如果都在同一台電腦、同一顆磁碟，硬碟損壞仍可能一起遺失。因此完整策略是：

```text
工作目錄＋.git
→ 專案外 Git bundle
→ 私人遠端 repository
→ 定期公司／外接硬碟備份
```

Git 保護程式版本；資料庫與附件必須依系統備份計畫另外備份。

## 10. 回復程序

### 從遠端

```bash
git clone <private-remote>
git checkout <checkpoint-tag>
```

### 從 bundle

```bash
git clone /path/to/company-system-<checkpoint>.bundle restored-company-system
cd restored-company-system
git tag --list
```

還原後仍需依 README 建立環境、執行 migration、seed 及 test。正式資料不在 Git，必須從資料備份另行還原。

## 11. 進度更新模板

README 每次至少更新：

```text
最後更新日期：
目前階段：
目前切片：
實作完成度：
最新中型進度備份：
已完成：
進行中：
接下來要做：
阻擋／待確認：
```

詳細進度每筆至少包含：

```text
日期／Slice／狀態
需求 ID
完成內容
變更檔案
執行測試與結果
人工驗證
決策與風險
commit／tag／bundle／remote push
下一步
```
