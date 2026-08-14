import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { getDashboard } from '../api/operations'
import { getApiErrorMessage } from '../api/errorMessage'
import { ApiConnectionStatus } from '../app/ApiConnectionStatus'
import { KpiStrip, PageHeader, Section } from '../ui/UiPatterns'

export function HomePage() {
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['operations', 'dashboard'], queryFn: () => getDashboard() })
  return (
    <div className="ui-pattern-stack">
      <PageHeader
        eyebrow="COMPANY SYSTEM / OVERVIEW"
        title="首頁"
        description="依目前登入公司的權限彙整交期、生產、待出貨、待計價與未收帳款。"
        actions={[{ label: '整合搜尋', tone: 'primary', onClick: () => void navigate({ to: '/search' }) }]}
      />
      {query.isPending ? <p>正在載入營運總覽…</p> : null}
      {query.isError ? <Section title="營運總覽暫時無法載入"><p className="ui-inline-error" role="alert">{getApiErrorMessage(query.error)}</p><button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button></Section> : null}
      {query.data ? <KpiStrip label={`營運指標（${query.data.as_of}）`} items={query.data.cards.map((card) => ({ label: card.label, value: card.value, hint: card.unit, tone: card.tone === 'neutral' ? 'default' : card.tone }))} /> : null}
      <div className="ui-two-column">
        <Section title="每日工作入口" description="指標會依目前權限顯示；點選模組處理對應工作。">
          <ul className="check-list">
            <li>先查看到期工單與生產進度</li><li>處理已入庫、等待出貨的品項</li><li>完成待計價、對帳與未收帳款追蹤</li><li>用整合搜尋直接找到客戶或單據</li>
          </ul>
          <button className="ui-button ui-button--primary ui-section-link" onClick={() => void navigate({ to: '/search' })} type="button">開啟整合搜尋</button>
          {query.data?.cards.length ? <div className="ui-task-summary">{query.data.cards.map((card) => <a className="ui-button ui-button--secondary" href={card.target_path} key={card.key}><span>{card.label}</span><strong>{card.value} {card.unit}</strong></a>)}</div> : null}
        </Section>
        <Section title="系統連線" description="此處只顯示目前服務狀態，不顯示工程階段術語。">
          <ApiConnectionStatus />
        </Section>
      </div>
    </div>
  )
}
