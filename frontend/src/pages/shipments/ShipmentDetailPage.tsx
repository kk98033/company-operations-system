import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { cancelShipment, confirmShipment, getShipment, SHIPMENT_LIST_QUERY_KEY, shipmentQueryKey } from '../../api/shipments'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

type CompletionInput = { quantity: string; reason: string }
const STATUS = { draft: ['草稿', 'neutral'], confirmed: ['已確認', 'success'], cancelled: ['已取消', 'danger'] } as const

export function ShipmentDetailPage() {
  const { shipmentId } = useParams({ strict: false }) as { shipmentId: string }; const navigate = useNavigate(); const client = useQueryClient()
  const canConfirm = useHasCapability('shipment.confirm'); const canCancel = useHasCapability('shipment.cancel'); const canComplete = useHasCapability('shipment.complete_and_confirm')
  const [completions, setCompletions] = useState<Record<string, CompletionInput>>({}); const [cancelReason, setCancelReason] = useState('')
  const query = useQuery({ queryKey: shipmentQueryKey(shipmentId), queryFn: () => getShipment(shipmentId) })
  const refresh = async () => { await client.invalidateQueries({ queryKey: shipmentQueryKey(shipmentId) }); await client.invalidateQueries({ queryKey: SHIPMENT_LIST_QUERY_KEY }); await client.invalidateQueries({ queryKey: ['inventory'] }) }
  const confirm = useMutation({ mutationFn: () => confirmShipment(shipmentId, { expected_version: query.data!.version, idempotency_key: crypto.randomUUID(), completions: Object.entries(completions).filter(([, value]) => Number(value.quantity) > 0 && value.reason.trim()).map(([work_order_id, value]) => ({ work_order_id, quantity: value.quantity, reason: value.reason })) }), onSuccess: refresh })
  const cancel = useMutation({ mutationFn: () => cancelShipment(shipmentId, { expected_version: query.data!.version, idempotency_key: crypto.randomUUID(), reason: cancelReason }), onSuccess: refresh })
  const updateCompletion = (id: string, field: keyof CompletionInput, value: string) => setCompletions((current) => ({ ...current, [id]: { quantity: current[id]?.quantity ?? '', reason: current[id]?.reason ?? '', [field]: value } }))
  if (query.isPending) return <SystemState action={<span>請稍候</span>} code="SHP" description="正在載入出貨明細。" eyebrow="資料讀取" role="status" title="正在載入" />
  if (query.isError || !query.data) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入出貨單" />
  const row = query.data; const status = STATUS[row.status]
  return <div className="ui-pattern-stack shipment-page"><PageHeader eyebrow="出貨管理" title={row.document_number} description={`${row.customer_name}｜${row.shipment_date}`} actions={[{ label: '返回清單', onClick: () => void navigate({ to: '/shipments' }) }, { label: 'A4 預覽', onClick: () => void navigate({ to: '/shipments/$shipmentId/print', params: { shipmentId } }) }]} />
    <Section title="出貨摘要"><div className="shipment-summary"><div><span>狀態</span><StatusLabel tone={status[1]}>{status[0]}</StatusLabel></div><div><span>送貨地址</span><strong>{row.delivery_address || '—'}</strong></div><div><span>備註</span><strong>{row.notes || '—'}</strong></div><div><span>版本</span><strong>{row.version}</strong></div></div></Section>
    <Section title="出貨明細" description="實際扣庫量＝正式量＋備品量。"><DataTableFrame><table className="ui-data-table"><thead><tr><th>工單</th><th>品名／規格</th><th>正式量</th><th>備品量</th><th>實際扣庫</th><th>確認前可用量</th></tr></thead><tbody>{row.items.map((item) => <tr key={item.id}><th scope="row">{item.work_order_document_number}<small>{item.customer_order_number || '無客戶單號'}</small></th><td>{item.product_name}<small>{item.specification || '—'}</small></td><td>{item.delivered_quantity}</td><td>{item.spare_quantity}</td><td><strong>{item.inventory_consumed_quantity}</strong></td><td>{item.available_quantity_snapshot ?? '確認時重新計算'}</td></tr>)}</tbody></table></DataTableFrame></Section>
    {row.warnings?.map((warning) => <p className="ui-inline-warning" key={warning}>{warning}</p>)}
    {row.status === 'draft' && canComplete ? <Section title="庫存不足時補登真實完工（選用）" description="只有已有有效運送完成事件才可使用；完工入庫與整張出貨會在同一交易完成，取消出貨不會取消真實完工。"><div className="shipment-completion-grid">{row.items.map((item) => <div className="shipment-completion-row" key={item.id}><strong>{item.work_order_document_number}｜{item.product_name}</strong><Field label="本次實際完工量"><input min="0" onChange={(event) => updateCompletion(item.work_order_id, 'quantity', event.target.value)} step="0.0001" type="number" value={completions[item.work_order_id]?.quantity ?? ''} /></Field><Field label="補登原因"><input onChange={(event) => updateCompletion(item.work_order_id, 'reason', event.target.value)} placeholder="填寫實際完工依據" value={completions[item.work_order_id]?.reason ?? ''} /></Field></div>)}</div></Section> : null}
    {confirm.isError || cancel.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(confirm.error || cancel.error)}</p> : null}
    {row.status === 'draft' && canConfirm ? <div className="shipment-page-actions"><button className="ui-button ui-button--primary" disabled={confirm.isPending} onClick={() => confirm.mutate()} type="button">{confirm.isPending ? '確認中…' : '確認出貨並扣庫'}</button></div> : null}
    {row.status === 'confirmed' && canCancel ? <Section title="取消出貨" description="建立反向流水恢復正式量與備品量；原出貨與補登的真實完工紀錄都會保留。"><div className="shipment-cancel-form"><Field label="取消原因"><input onChange={(event) => setCancelReason(event.target.value)} value={cancelReason} /></Field><button className="ui-button ui-button--danger" disabled={!cancelReason.trim() || cancel.isPending} onClick={() => cancel.mutate()} type="button">確認取消並沖銷</button></div></Section> : null}
  </div>
}
