import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { createPricing, listPendingPricing, listPricing, PRICING_LIST_QUERY_KEY, PRICING_PENDING_QUERY_KEY } from '../../api/pricing'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

const PRICING_STATUS = {
  draft: ['草稿', 'neutral'], confirmed: ['已確認', 'success'], cancelled: ['已取消', 'danger'],
} as const
const SOURCE_STATUS = {
  pending: ['待計價', 'warning'], pricing: ['計價中', 'working'], priced: ['已計價', 'success'], cancelled: ['計價已取消', 'danger'],
} as const

export function PricingListPage() {
  const navigate = useNavigate(); const client = useQueryClient()
  const canRead = useHasCapability('pricing.read'); const canCreate = useHasCapability('pricing.create')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState('')
  const [sourceStatus, setSourceStatus] = useState('pending'); const [selected, setSelected] = useState<Set<string>>(new Set())
  const pending = useQuery({ queryKey: [...PRICING_PENDING_QUERY_KEY, keyword, sourceStatus], queryFn: () => listPendingPricing({ keyword: keyword || undefined, status: sourceStatus as 'pending' | 'pricing' | 'priced' | 'cancelled', page_size: 100 }), enabled: canRead })
  const documents = useQuery({ queryKey: PRICING_LIST_QUERY_KEY, queryFn: () => listPricing({ page_size: 100 }), enabled: canRead })
  const selectedRows = useMemo(() => pending.data?.items.filter((item) => selected.has(item.shipment_item_id)) ?? [], [pending.data, selected])
  const oneCustomer = new Set(selectedRows.map((item) => item.customer_id)).size <= 1
  const create = useMutation({ mutationFn: () => createPricing({ pricing_date: new Date().toLocaleDateString('sv-SE'), shipment_item_ids: [...selected], notes: null, idempotency_key: crypto.randomUUID() }), onSuccess: async (row) => { await client.invalidateQueries({ queryKey: PRICING_PENDING_QUERY_KEY }); void navigate({ to: '/pricing/$pricingId', params: { pricingId: row.id } }) } })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 pricing.read 權限。" eyebrow="權限限制" role="alert" title="沒有計價資料權限" />
  const search = (event: FormEvent) => { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack pricing-page"><PageHeader eyebrow="計價管理" title="待計價與計價單" description="基礎計價只取正式出貨量；備品必須另列可請款數量與價格，系統不會靜默收費。" />
    <Section title="出貨計價來源" description="狀態同時使用文字與輔助色；同一出貨明細只能建立一筆基礎計價。">
      <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="出貨單、工單、客戶、品名" type="search" value={input} /></Field><Field label="計價狀態"><select onChange={(event) => { setSourceStatus(event.target.value); setSelected(new Set()) }} value={sourceStatus}><option value="pending">待計價</option><option value="pricing">計價中</option><option value="priced">已計價</option><option value="cancelled">計價已取消</option></select></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
      {pending.isPending ? <p>正在載入待計價來源…</p> : pending.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(pending.error)}</p> : <DataTableFrame footer={<span>已選 {selected.size} 筆／共 {pending.data?.meta.pagination.total_items ?? 0} 筆</span>}><table className="ui-data-table"><thead><tr><th>選取</th><th>狀態</th><th>出貨單／日期</th><th>客戶</th><th>工單／品名</th><th>正式量</th><th>備品量</th><th>參考單價</th><th>計價單</th></tr></thead><tbody>{pending.data?.items.length === 0 ? <tr><td colSpan={9}>目前沒有符合條件的出貨明細。</td></tr> : pending.data?.items.map((item) => { const state = SOURCE_STATUS[item.pricing_status]; return <tr key={item.shipment_item_id}><td>{item.pricing_status === 'pending' ? <input aria-label={`選取 ${item.shipment_document_number} ${item.work_order_document_number}`} checked={selected.has(item.shipment_item_id)} onChange={(event) => setSelected((current) => { const next = new Set(current); if (event.target.checked) next.add(item.shipment_item_id); else next.delete(item.shipment_item_id); return next })} type="checkbox" /> : '—'}</td><td><StatusLabel tone={state[1]}>{state[0]}</StatusLabel></td><th scope="row">{item.shipment_document_number}<small>{item.shipment_date}</small></th><td>{item.customer_name}</td><td>{item.work_order_document_number}<small>{item.product_name}</small></td><td>{item.delivered_quantity}</td><td>{item.spare_quantity}</td><td>{item.suggested_unit_price}</td><td>{item.pricing_document_id ? <button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/pricing/$pricingId', params: { pricingId: item.pricing_document_id! } })} type="button">{item.pricing_document_number}</button> : '—'}</td></tr> })}</tbody></table></DataTableFrame>}
      {canCreate && sourceStatus === 'pending' ? <div className="pricing-actions"><button className="ui-button ui-button--primary" disabled={selected.size === 0 || !oneCustomer || create.isPending} onClick={() => create.mutate()} type="button">{create.isPending ? '建立中…' : `建立計價草稿（${selected.size}）`}</button>{!oneCustomer ? <p className="ui-inline-error" role="alert">一張計價單只能包含同一客戶。</p> : null}{create.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(create.error)}</p> : null}</div> : null}
    </Section>
    <Section title="計價單查詢">
      {documents.isPending ? <p>正在載入計價單…</p> : documents.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(documents.error)}</p> : <DataTableFrame footer={<span>共 {documents.data?.meta.pagination.total_items ?? 0} 筆</span>}><table className="ui-data-table"><thead><tr><th>計價單號</th><th>日期</th><th>客戶</th><th>明細</th><th>總額</th><th>狀態</th><th>操作</th></tr></thead><tbody>{documents.data?.items.length === 0 ? <tr><td colSpan={7}>目前沒有計價單。</td></tr> : documents.data?.items.map((item) => { const state = PRICING_STATUS[item.status]; return <tr key={item.id}><th scope="row">{item.document_number}{item.legacy_document_number ? <small>舊號 {item.legacy_document_number}</small> : null}</th><td>{item.pricing_date}</td><td>{item.customer_name}</td><td>{item.line_count}</td><td>{item.total_amount}</td><td><StatusLabel tone={state[1]}>{state[0]}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/pricing/$pricingId', params: { pricingId: item.id } })} type="button">查看</button></td></tr> })}</tbody></table></DataTableFrame>}
    </Section>
  </div>
}
