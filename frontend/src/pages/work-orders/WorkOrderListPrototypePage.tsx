import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { listWorkOrders, WORK_ORDER_LIST_QUERY_KEY } from '../../api/workOrders'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { CsvExportButton } from '../../ui/CsvExportButton'

export function WorkOrderListPrototypePage() {
  const navigate = useNavigate(); const canRead = useHasCapability('work_orders.read'); const canManage = useHasCapability('work_orders.manage')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState(''); const [status, setStatus] = useState<''|'draft'|'confirmed'|'void'>('')
  const query = useQuery({ queryKey: [...WORK_ORDER_LIST_QUERY_KEY, keyword, status], queryFn: () => listWorkOrders({ keyword: keyword || undefined, status: status || undefined }), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 work_orders.read 權限。" eyebrow="權限限制" role="alert" title="沒有工單資料權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack work-order-list-page">
    <PageHeader eyebrow="工單管理" title="工單查詢" description="同一入口查詢現行、歷史與作廢工單；關鍵字涵蓋工單號、舊號、客戶單號、客戶、品名與備註。" actions={canManage ? [{ label: '新增工單', tone: 'primary', onClick: () => void navigate({ to: '/work-orders/new' }) }] : []} />
    <div className="ui-page-tools"><CsvExportButton dataset="work-orders" /></div>
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="工單號、客戶單號、客戶或品名" type="search" value={input} /></Field><Field label="狀態"><select onChange={(event) => setStatus(event.target.value as typeof status)} value={status}><option value="">全部</option><option value="draft">草稿</option><option value="confirmed">已確認</option><option value="void">已作廢</option></select></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="WO" description="正在讀取工單。" eyebrow="資料讀取" role="status" title="正在載入工單" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入工單" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}><table className="ui-data-table"><thead><tr><th scope="col">工單號碼</th><th scope="col">客戶</th><th scope="col">品名</th><th scope="col">數量</th><th scope="col">單價</th><th scope="col">版費</th><th scope="col">刀模費</th><th scope="col">交期</th><th scope="col">狀態</th><th scope="col">操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={10}>查無工單資料。</td></tr> : query.data.items.map((item) => <tr key={item.id}><th scope="row">{item.document_number}{item.legacy_document_number ? <small>舊號 {item.legacy_document_number}</small> : null}</th><td>{item.customer_name}</td><td>{item.product_name}</td><td>{item.order_quantity}</td><td>{item.unit_price}</td><td>{item.plate_fee}</td><td>{item.die_fee}</td><td>{item.delivery_date ?? '—'}</td><td><StatusLabel tone={item.status === 'confirmed' ? 'success' : item.status === 'draft' ? 'working' : 'neutral'}>{item.status === 'confirmed' ? '已確認' : item.status === 'draft' ? '草稿' : '已作廢'}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/work-orders/$workOrderId', params: { workOrderId: item.id } })} type="button">{canManage && item.status === 'draft' ? '編輯' : '查看'}</button></td></tr>)}</tbody></table></DataTableFrame> : null}
  </div>
}
