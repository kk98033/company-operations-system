import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'

import { getCustomerOverview } from '../../api/operations'
import { getApiErrorMessage } from '../../api/errorMessage'
import { DataTableFrame, KpiStrip, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

const labels: Record<string, string> = { quotation: '報價', case: '案件', work_order: '工單', shipment: '出貨', pricing: '計價', statement: '對帳', receipt: '收款' }

export function CustomerOverviewPage() {
  const { customerId } = useParams({ from: '/authenticated/customers/$customerId/overview' })
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['operations', 'customer', customerId], queryFn: () => getCustomerOverview(customerId) })
  if (query.isPending) return <p>正在整理客戶往來資料…</p>
  if (query.isError) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入客戶總覽" />
  const row = query.data
  const kpis = Object.entries(row.counts).map(([key, value]) => ({ label: labels[key] ?? key, value: String(value), hint: '筆往來資料' }))
  if (row.outstanding_amount != null) kpis.push({ label: '未收帳款', value: row.outstanding_amount, hint: '元' })
  return <div className="ui-pattern-stack operations-page"><PageHeader eyebrow="客戶管理 / 360 總覽" title={`${row.customer_code} ${row.customer_name}`} description="集中查看這位客戶在各業務模組的數量與最近往來。" actions={[{ label: '返回客戶', onClick: () => void navigate({ to: '/customers/$customerId', params: { customerId } }) }]} />
    <KpiStrip label="客戶往來統計" items={kpis} />
    <Section title="最近往來"><DataTableFrame footer={<span>最近 {row.recent_activity.length} 筆</span>}><table className="ui-data-table"><thead><tr><th>日期</th><th>類型</th><th>單號</th><th>狀態</th><th>操作</th></tr></thead><tbody>{row.recent_activity.length ? row.recent_activity.map((item) => <tr key={`${item.entity_type}-${item.entity_id}`}><td>{item.activity_date}</td><td>{labels[item.entity_type]}</td><th scope="row">{item.document_number}</th><td><StatusLabel tone="neutral">{item.status}</StatusLabel></td><td><a className="ui-button ui-button--secondary" href={item.target_path}>開啟</a></td></tr>) : <tr><td colSpan={5}>目前沒有往來資料。</td></tr>}</tbody></table></DataTableFrame></Section>
  </div>
}
