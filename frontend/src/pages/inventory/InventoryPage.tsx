import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { createInventoryAdjustment, INVENTORY_LIST_QUERY_KEY, listInventory } from '../../api/production'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, Section, SystemState } from '../../ui/UiPatterns'

export function InventoryPage() {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const canRead = useHasCapability('inventory.read'); const canAdjust = useHasCapability('inventory.adjust')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState(''); const [positiveOnly, setPositiveOnly] = useState(true)
  const [selectedId, setSelectedId] = useState(''); const [quantity, setQuantity] = useState(''); const [reason, setReason] = useState('')
  const query = useQuery({ queryKey: [...INVENTORY_LIST_QUERY_KEY, keyword, positiveOnly], queryFn: () => listInventory({ keyword: keyword || undefined, positive_only: positiveOnly }), enabled: canRead })
  const mutation = useMutation({ mutationFn: () => createInventoryAdjustment(selectedId, { quantity, reason, idempotency_key: crypto.randomUUID() }), onSuccess: async () => { setQuantity(''); setReason(''); await queryClient.invalidateQueries({ queryKey: INVENTORY_LIST_QUERY_KEY }) } })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 inventory.read 權限。" eyebrow="權限限制" role="alert" title="沒有庫存資料權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack inventory-page"><PageHeader eyebrow="庫存管理" title="待出貨存貨與流水" description="可用量只由不可變流水加總；預設只顯示正庫存，零庫存與未完工工單不會混入待出貨清單。" />
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="工單、客戶或品名" type="search" value={input} /></Field><Field label="顯示範圍"><label className="ui-check"><input checked={positiveOnly} onChange={(event) => setPositiveOnly(event.target.checked)} type="checkbox" />只顯示正可用量</label></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="INV" description="正在加總庫存流水。" eyebrow="資料讀取" role="status" title="正在載入庫存" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入庫存" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}><table className="ui-data-table"><thead><tr><th>工單</th><th>客戶</th><th>品名</th><th>訂單量</th><th>可用量</th><th>交期</th><th>操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={7}>目前沒有符合條件的可用庫存。</td></tr> : query.data.items.map((item) => <tr key={item.work_order_id}><th scope="row">{item.document_number}</th><td>{item.customer_name}</td><td>{item.product_name}</td><td>{item.order_quantity}</td><td><strong>{item.available_quantity}</strong></td><td>{item.delivery_date ?? '—'}</td><td><button className="ui-button ui-button--secondary" onClick={() => { setSelectedId(item.work_order_id); void navigate({ to: '/production/work-orders/$workOrderId', params: { workOrderId: item.work_order_id } }) }} type="button">查看流水</button>{canAdjust ? <button className="ui-button ui-button--secondary" onClick={() => setSelectedId(item.work_order_id)} type="button">人工調整</button> : null}</td></tr>)}</tbody></table></DataTableFrame> : null}
    {canAdjust && selectedId ? <Section title="人工庫存調整" description="正數增加、負數減少；原因必填，調整後不得為負。"><div className="inventory-adjust-form"><Field label="調整量"><input onChange={(event) => setQuantity(event.target.value)} step="0.0001" type="number" value={quantity} /></Field><Field label="調整原因"><input onChange={(event) => setReason(event.target.value)} value={reason} /></Field><button className="ui-button ui-button--primary" disabled={!quantity || !reason.trim()} onClick={() => mutation.mutate()} type="button">核准並調整</button></div>{mutation.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(mutation.error)}</p> : null}</Section> : null}
  </div>
}
