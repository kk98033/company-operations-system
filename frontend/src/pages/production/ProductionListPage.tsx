import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { listProduction, PRODUCTION_LIST_QUERY_KEY } from '../../api/production'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'

const stateLabel = { not_started: '未開始', in_progress: '進行中', partial: '部分完成', completed: '已完成' }

export function ProductionListPage() {
  const navigate = useNavigate(); const canRead = useHasCapability('production.read')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState('')
  const query = useQuery({ queryKey: [...PRODUCTION_LIST_QUERY_KEY, keyword], queryFn: () => listProduction({ keyword: keyword || undefined }), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 production.read 權限。" eyebrow="權限限制" role="alert" title="沒有生產資料權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack production-page">
    <PageHeader eyebrow="生產管理" title="製程監管" description="追蹤已確認工單的 13 道製程；一般製程與運送完成都不會自動入庫。" />
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="工單、客戶或品名" type="search" value={input} /></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="PROD" description="正在讀取生產工單。" eyebrow="資料讀取" role="status" title="正在載入製程" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入生產資料" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 張已確認工單</span>}><table className="ui-data-table"><thead><tr><th>工單</th><th>客戶</th><th>品名</th><th>交期</th><th>完成製程</th><th>運送</th><th>可用庫存</th><th>操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={8}>尚無已確認工單。</td></tr> : query.data.items.map((item) => <tr key={item.work_order_id}><th scope="row">{item.document_number}</th><td>{item.customer_name}</td><td>{item.product_name}</td><td>{item.delivery_date ?? '—'}</td><td>{item.process_completed_count}／13</td><td><StatusLabel tone={item.transport_state === 'completed' ? 'success' : item.transport_state === 'not_started' ? 'neutral' : 'working'}>{stateLabel[item.transport_state]}</StatusLabel></td><td>{item.available_quantity}</td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/production/work-orders/$workOrderId', params: { workOrderId: item.work_order_id } })} type="button">製程操作</button></td></tr>)}</tbody></table></DataTableFrame> : null}
  </div>
}
