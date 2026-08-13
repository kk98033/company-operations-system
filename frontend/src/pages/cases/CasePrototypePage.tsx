import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { CASE_LIST_QUERY_KEY, caseQueryKey, getCase, listCases } from '../../api/workOrders'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'

export function CasePrototypePage() {
  const navigate = useNavigate(); const canRead = useHasCapability('cases.read')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState(''); const [status, setStatus] = useState<''|'draft'|'active'|'void'>('')
  const query = useQuery({ queryKey: [...CASE_LIST_QUERY_KEY, keyword, status], queryFn: () => listCases({ keyword: keyword || undefined, status: status || undefined }), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 cases.read 權限。" eyebrow="權限限制" role="alert" title="沒有案件權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack case-page"><PageHeader eyebrow="案件管理" title="生產案件" description="一個案件集中同一客戶訂單的多張單品工單；可由報價多筆明細一次建立，也可由直接工單自動建立。" />
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="案件號、舊號或客戶" type="search" value={input} /></Field><Field label="狀態"><select onChange={(event) => setStatus(event.target.value as typeof status)} value={status}><option value="">全部</option><option value="draft">草稿</option><option value="active">進行中</option><option value="void">已作廢</option></select></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="CASE" description="正在讀取案件。" eyebrow="資料讀取" role="status" title="正在載入案件" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入案件" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}><table className="ui-data-table"><thead><tr><th>案件號碼</th><th>日期</th><th>客戶</th><th>工單數</th><th>已確認</th><th>狀態</th><th>操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={7}>尚無案件。</td></tr> : query.data.items.map((item) => <tr key={item.id}><th scope="row">{item.case_number}</th><td>{item.case_date}</td><td>{item.customer_name}</td><td>{item.work_order_count}</td><td>{item.confirmed_count}</td><td><StatusLabel tone={item.status === 'active' ? 'working' : item.status === 'void' ? 'neutral' : 'warning'}>{item.status === 'active' ? '進行中' : item.status === 'void' ? '已作廢' : '草稿'}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/cases/$caseId', params: { caseId: item.id } })} type="button">查看</button></td></tr>)}</tbody></table></DataTableFrame> : null}
  </div>
}

export function CaseDetailPage() {
  const { caseId } = useParams({ from: '/authenticated/cases/$caseId' }); const navigate = useNavigate(); const canRead = useHasCapability('cases.read')
  const query = useQuery({ queryKey: caseQueryKey(caseId), queryFn: () => getCase(caseId), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 cases.read 權限。" eyebrow="權限限制" role="alert" title="沒有案件權限" />
  if (query.isPending) return <SystemState action={<span>請稍候</span>} code="CASE" description="正在讀取案件與工單。" eyebrow="資料讀取" role="status" title="正在載入案件" />
  if (query.isError) return <SystemState action={<span>返回案件列表</span>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入案件" />
  const item = query.data
  return <div className="ui-pattern-stack case-page"><PageHeader eyebrow="案件管理 / 詳細資料" title={item.case_number} description={`${String(item.customer_snapshot.name ?? '')}｜${item.case_date}`} actions={[{ label: '返回案件', onClick: () => void navigate({ to: '/cases' }) }]} />
    <div className="module-prototype__notice"><StatusLabel tone={item.status === 'active' ? 'working' : item.status === 'void' ? 'neutral' : 'warning'}>{item.status === 'active' ? '進行中' : item.status === 'void' ? '已作廢' : '草稿'}</StatusLabel><span>{item.source_quotation_id ? `來源報價 ${item.source_quotation_id}` : '來源：直接建立工單'}</span></div>
    <DataTableFrame footer={<span>共 {item.work_orders.length} 張工單</span>}><table className="ui-data-table"><thead><tr><th>工單</th><th>品名</th><th>數量</th><th>交期</th><th>狀態</th><th>操作</th></tr></thead><tbody>{item.work_orders.map((order) => <tr key={order.id}><th scope="row">{order.document_number}</th><td>{order.product_name}</td><td>{order.order_quantity}</td><td>{order.delivery_date ?? '—'}</td><td>{order.status === 'confirmed' ? '已確認' : order.status === 'draft' ? '草稿' : '已作廢'}</td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/work-orders/$workOrderId', params: { workOrderId: order.id } })} type="button">開啟工單</button></td></tr>)}</tbody></table></DataTableFrame>
  </div>
}
