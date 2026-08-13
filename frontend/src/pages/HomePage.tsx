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
        description="核心交易已完成到對帳與收款，並支援四種正式文件 PDF；目前尚未匯入公司正式業務資料。"
        actions={[]}
      />
      <KpiStrip
        label="工程基準狀態"
        items={[
          { label: '目前階段', value: 'Phase 8', hint: 'PDF 匯出補強已完成', tone: 'success' },
          { label: '正式業務資料', value: '0', hint: '依規定尚未匯入' },
          { label: '主模組路由', value: String(workflowModules.length), hint: '客戶一路到收款', tone: 'success' },
          { label: '開工決策', value: '10 / 10', hint: '公司已確認', tone: 'success' },
        ]}
      />
      <div className="ui-two-column">
        <Section title="目前成果" description="正式功能已依公司流程逐階段接上 API、資料庫與權限。">
          <ul className="check-list">
            <li>React、TanStack Router 與 TanStack Query</li>
            <li>平面工業 ERP 殼層與 Design Tokens</li>
            <li>總覽、清單、表單與詳細資料共用版型及 axe 基線</li>
            <li>客戶、報價、案件、工單、生產、庫存、出貨、計價、對帳與收款</li>
            <li>報價、工單、出貨單與對帳單的不可變 PDF 匯出</li>
          </ul>
          <Link className="ui-button ui-button--primary ui-section-link" to="/customers">從客戶管理開始</Link>
        </Section>
        <Section title="實作狀態" description="後續業務功能將依小切片實作、驗證與 Git 備份。">
          <div className="ui-status-summary"><StatusLabel tone="success">核心交易已可操作</StatusLabel><strong>Phase 8 與 PDF 匯出完成</strong><p>Phase 2～8 已接上正式 API 與資料庫；公司真實資料匯入、工作台整合查詢及正式部署仍依後續 Phase 執行。</p></div>
          <ApiConnectionStatus />
        </Section>
      </div>
    </div>
  )
}
