import { Link } from '@tanstack/react-router'

import { KpiStrip, PageHeader, Section, StatusLabel } from '../ui/UiPatterns'

export function HomePage() {
  return (
    <div className="ui-pattern-stack">
      <PageHeader
        eyebrow="PHASE 0 / FOUNDATION"
        title="首頁"
        description="工程骨架與正式 UI 基準已建立；目前尚未載入客戶、工單或帳務正式資料。"
        actions={[]}
      />
      <KpiStrip
        label="工程基準狀態"
        items={[
          { label: '前端測試', value: '待驗證', hint: '本切片完成後更新' },
          { label: '正式業務資料', value: '0', hint: '依規定尚未匯入' },
          { label: 'UI 版型', value: '4', hint: '總覽／清單／表單／詳細', tone: 'success' },
          { label: 'P0 待確認', value: '10', hint: '業務決策尚待公司', tone: 'warning' },
        ]}
      />
      <div className="ui-two-column">
        <Section title="目前成果" description="這一階段只建立可持續開發的工程與介面基準。">
          <ul className="check-list">
            <li>React、TanStack Router 與 TanStack Query</li>
            <li>平面工業 ERP 殼層與 Design Tokens</li>
            <li>總覽、清單、表單與詳細資料共用版型</li>
            <li>錯誤邊界、404 與本機測試流程</li>
          </ul>
          <Link className="ui-button ui-button--primary ui-section-link" to="/ui-patterns">查看統一 UI 版型</Link>
        </Section>
        <Section title="實作狀態" description="所有業務功能依小切片完成、驗證與 Git 備份。">
          <div className="ui-status-summary"><StatusLabel tone="working">Phase 0</StatusLabel><strong>UI 基準切片</strong><p>下一個工程切片仍為 0.2；尚未開始客戶、工單、出貨與帳務功能。</p></div>
        </Section>
      </div>
    </div>
  )
}
