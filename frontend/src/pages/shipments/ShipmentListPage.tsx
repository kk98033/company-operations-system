import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { listShipments, SHIPMENT_LIST_QUERY_KEY } from '../../api/shipments'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { CsvExportButton } from '../../ui/CsvExportButton'

const STATUS: Record<string, { label: string; tone: 'neutral' | 'success' | 'danger' }> = {
  draft: { label: '草稿', tone: 'neutral' }, confirmed: { label: '已確認', tone: 'success' }, cancelled: { label: '已取消', tone: 'danger' },
}

export function ShipmentListPage() {
  const navigate = useNavigate(); const canRead = useHasCapability('shipment.read'); const canCreate = useHasCapability('shipment.create')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState(''); const [status, setStatus] = useState('')
  const query = useQuery({ queryKey: [...SHIPMENT_LIST_QUERY_KEY, keyword, status], queryFn: () => listShipments({ keyword: keyword || undefined, status: status ? status as 'draft' | 'confirmed' | 'cancelled' : undefined }), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 shipment.read 權限。" eyebrow="權限限制" role="alert" title="沒有出貨資料權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack shipment-page"><PageHeader eyebrow="出貨管理" title="出貨單查詢" description="正式量與備品分欄保存並同時扣庫；取消時以反向流水恢復，不刪除歷史。" actions={canCreate ? [{ label: '新增出貨單', tone: 'primary', onClick: () => void navigate({ to: '/shipments/new' }) }] : undefined} />
    <div className="ui-page-tools"><CsvExportButton dataset="shipments" /></div>
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="出貨單號、舊單號、客戶" type="search" value={input} /></Field><Field label="狀態"><select onChange={(event) => setStatus(event.target.value)} value={status}><option value="">全部</option><option value="draft">草稿</option><option value="confirmed">已確認</option><option value="cancelled">已取消</option></select></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="SHP" description="正在載入出貨資料。" eyebrow="資料讀取" role="status" title="正在載入" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入出貨單" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}><table className="ui-data-table"><thead><tr><th>出貨單號</th><th>日期</th><th>客戶</th><th>正式量</th><th>備品量</th><th>狀態</th><th>操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={7}>目前沒有符合條件的出貨單。</td></tr> : query.data.items.map((item) => <tr key={item.id}><th scope="row">{item.document_number}{item.legacy_document_number ? <small>舊號 {item.legacy_document_number}</small> : null}</th><td>{item.shipment_date}</td><td>{item.customer_name}</td><td>{item.delivered_quantity}</td><td>{item.spare_quantity}</td><td><StatusLabel tone={STATUS[item.status].tone}>{STATUS[item.status].label}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/shipments/$shipmentId', params: { shipmentId: item.id } })} type="button">查看</button></td></tr>)}</tbody></table></DataTableFrame> : null}
  </div>
}
