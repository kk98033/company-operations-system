import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { listCustomers } from '../../api/customers'
import { createShipment, listAvailableShipmentItems } from '../../api/shipments'
import { getApiErrorMessage } from '../../api/errorMessage'
import { DataTableFrame, Field, PageHeader, Section, SystemState } from '../../ui/UiPatterns'

type Line = { workOrderId: string; delivered: string; spare: string }
const today = new Date().toISOString().slice(0, 10)

export function ShipmentEditorPage() {
  const navigate = useNavigate(); const [customerId, setCustomerId] = useState(''); const [shipmentDate, setShipmentDate] = useState(today); const [address, setAddress] = useState(''); const [notes, setNotes] = useState(''); const [lines, setLines] = useState<Line[]>([])
  const customers = useQuery({ queryKey: ['customers', 'shipment-options'], queryFn: () => listCustomers({ status: 'active', page_size: 100 }) })
  const available = useQuery({ queryKey: ['shipments', 'available', customerId], queryFn: () => listAvailableShipmentItems(customerId), enabled: Boolean(customerId) })
  const selected = useMemo(() => new Set(lines.map((line) => line.workOrderId)), [lines])
  const mutation = useMutation({ mutationFn: () => createShipment({ shipment_date: shipmentDate, customer_id: customerId, delivery_address: address || null, notes: notes || null, items: lines.map((line) => ({ work_order_id: line.workOrderId, delivered_quantity: line.delivered || '0', spare_quantity: line.spare || '0' })), idempotency_key: crypto.randomUUID() }), onSuccess: (row) => void navigate({ to: '/shipments/$shipmentId', params: { shipmentId: row.id } }) })
  const changeCustomer = (id: string) => { setCustomerId(id); setLines([]); const customer = customers.data?.items.find((item) => item.id === id); setAddress(customer?.address ?? '') }
  const patchLine = (id: string, field: 'delivered' | 'spare', value: string) => setLines((current) => current.map((line) => line.workOrderId === id ? { ...line, [field]: value } : line))
  return <div className="ui-pattern-stack shipment-page"><PageHeader eyebrow="出貨管理" title="新增出貨單" description="先選客戶，再從該客戶目前有正可用量的工單中選取出貨品項。" actions={[{ label: '返回清單', onClick: () => void navigate({ to: '/shipments' }) }]} />
    <Section title="出貨資料"><div className="shipment-header-grid"><Field label="客戶"><select onChange={(event) => changeCustomer(event.target.value)} value={customerId}><option value="">請選擇客戶</option>{customers.data?.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.code}｜{customer.name}</option>)}</select></Field><Field label="出貨日期"><input onChange={(event) => setShipmentDate(event.target.value)} type="date" value={shipmentDate} /></Field><Field label="送貨地址"><input onChange={(event) => setAddress(event.target.value)} value={address} /></Field><Field label="備註"><input onChange={(event) => setNotes(event.target.value)} value={notes} /></Field></div></Section>
    <Section title="可出貨品項" description="顯示量只供選擇；確認時後端會鎖定工單並重新加總。">{!customerId ? <p className="ui-help">請先選擇客戶。</p> : available.isPending ? <p>正在載入可出貨品項…</p> : available.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(available.error)}</p> : <DataTableFrame><table className="ui-data-table"><thead><tr><th>選取</th><th>工單</th><th>品名</th><th>可用量</th><th>正式量</th><th>備品量</th></tr></thead><tbody>{available.data?.items.length === 0 ? <tr><td colSpan={6}>這個客戶目前沒有正可用量。</td></tr> : available.data?.items.map((item) => { const line = lines.find((entry) => entry.workOrderId === item.work_order_id); return <tr key={item.work_order_id}><td><input aria-label={`選取 ${item.document_number}`} checked={selected.has(item.work_order_id)} onChange={(event) => setLines((current) => event.target.checked ? [...current, { workOrderId: item.work_order_id, delivered: '', spare: '0' }] : current.filter((entry) => entry.workOrderId !== item.work_order_id))} type="checkbox" /></td><th scope="row">{item.document_number}</th><td>{item.product_name}</td><td>{item.available_quantity}</td><td><input aria-label={`${item.document_number} 正式量`} disabled={!line} max={item.available_quantity} min="0" onChange={(event) => patchLine(item.work_order_id, 'delivered', event.target.value)} step="0.0001" type="number" value={line?.delivered ?? ''} /></td><td><input aria-label={`${item.document_number} 備品量`} disabled={!line} min="0" onChange={(event) => patchLine(item.work_order_id, 'spare', event.target.value)} step="0.0001" type="number" value={line?.spare ?? ''} /></td></tr> })}</tbody></table></DataTableFrame>}</Section>
    {mutation.isError ? <SystemState action={<span>請修正後重試</span>} code="ERR" description={getApiErrorMessage(mutation.error)} eyebrow="存檔失敗" role="alert" title="無法建立出貨草稿" /> : null}
    <div className="shipment-page-actions"><button className="ui-button ui-button--primary" disabled={!customerId || lines.length === 0 || lines.some((line) => Number(line.delivered) + Number(line.spare) <= 0) || mutation.isPending} onClick={() => mutation.mutate()} type="button">{mutation.isPending ? '存檔中…' : '存檔草稿'}</button></div>
  </div>
}
