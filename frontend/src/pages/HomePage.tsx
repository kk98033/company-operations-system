import { Link } from '@tanstack/react-router'

import { workflowModules } from '../app/workflowModules'
import { ApiConnectionStatus } from '../app/ApiConnectionStatus'
import { KpiStrip, PageHeader, Section, StatusLabel } from '../ui/UiPatterns'

export function HomePage() {
  return (
    <div className="ui-pattern-stack">
      <PageHeader
        eyebrow="COMPANY SYSTEM / OVERVIEW"
        title="首頁"
        description="正式 UI、無障礙與主模組路由骨架已建立；目前仍未載入公司正式業務資料。"
        actions={[]}
      />
      <KpiStrip
        label="工程基準狀態"
        items={[
          { label: '工程基準', value: '10 / 10', hint: 'Phase 0 工程已完成', tone: 'success' },
          { label: '正式業務資料', value: '0', hint: '依規定尚未匯入' },
          { label: '主模組路由', value: String(workflowModules.length), hint: '客戶一路到收款', tone: 'success' },
          { label: 'P0 待確認', value: '6', hint: '4／10 已由公司確認', tone: 'warning' },
        ]}
      />
      <div className="ui-two-column">
        <Section title="目前成果" description="這一階段只建立可持續開發的工程與介面基準。">
          <ul className="check-list">
            <li>React、TanStack Router 與 TanStack Query</li>
            <li>平面工業 ERP 殼層與 Design Tokens</li>
            <li>總覽、清單、表單與詳細資料共用版型及 axe 基線</li>
            <li>客戶、報價、案件、工單至收款的可點擊假資料路由</li>
          </ul>
          <Link className="ui-button ui-button--primary ui-section-link" to="/customers">從客戶管理開始</Link>
        </Section>
        <Section title="實作狀態" description="後續業務功能將依小切片實作、驗證與 Git 備份。">
          <div className="ui-status-summary"><StatusLabel tone="warning">待公司簽核</StatusLabel><strong>Phase 0 工程基準完成</strong><p>案件三層模型已納入原型；其餘 P0 業務規則仍須公司確認，所有模組頁目前都不是正式業務功能。</p></div>
          <ApiConnectionStatus />
        </Section>
      </div>
    </div>
  )
}
