import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { listCustomers } from '../../api/customers'
import { cloneQuotation, confirmQuotation, createQuotation, getQuotation, quotationQueryKey, QUOTATION_LIST_QUERY_KEY, updateQuotation, voidQuotation } from '../../api/quotations'
import { getApiErrorMessage } from '../../api/errorMessage'
import { convertQuotation } from '../../api/workOrders'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { FormValidationSummary } from '../../ui/FormValidationSummary'
import { collectFormValidationIssues, type FormValidationIssue } from '../../ui/formValidation'
import { emptyItem, emptyQuotationDraft, quotationPayload, responseToDraft, type QuotationDraft, type QuotationItemDraft } from './quotationDraft'

const itemLabels: Record<keyof QuotationItemDraft, string> = {
  key: '識別碼', product_name: '品名', size: '尺寸', paper: '紙質', color: '顏色',
  coating: '上光', quantity: '數量', plate_fee: '版費', die_fee: '刀模費',
  unit_price: '單價', note: '附註',
}

export function QuotationNewPage() { return <QuotationEditorPage /> }
export function QuotationEditPage() { const { quotationId } = useParams({ from: '/authenticated/quotations/$quotationId' }); return <QuotationEditorPage quotationId={quotationId} /> }

function QuotationEditorPage({ quotationId }: { quotationId?: string }) {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const canRead = useHasCapability('quotations.read'); const canManage = useHasCapability('quotations.manage'); const canConfirm = useHasCapability('quotations.confirm')
  const canCreateCase = useHasCapability('cases.manage')
  const [draft, setDraft] = useState<QuotationDraft>(emptyQuotationDraft)
  const [voidReason, setVoidReason] = useState('')
  const [validationIssues, setValidationIssues] = useState<FormValidationIssue[]>([])
  const formRef = useRef<HTMLFormElement>(null)
  const query = useQuery({ queryKey: quotationId ? quotationQueryKey(quotationId) : ['quotations', 'new'], queryFn: () => getQuotation(quotationId!), enabled: Boolean(quotationId && canRead) })
  const customers = useQuery({ queryKey: ['customers', 'quotation-options'], queryFn: () => listCustomers({ page_size: 100, status: 'active' }), enabled: canRead })
  useEffect(() => { if (query.data) setDraft(responseToDraft(query.data)) }, [query.data])
  const save = useMutation({ mutationFn: async () => quotationId ? updateQuotation(quotationId, { ...quotationPayload(draft), expected_updated_at: query.data!.updated_at }) : createQuotation(quotationPayload(draft)), onSuccess: async (value) => { setValidationIssues([]); queryClient.setQueryData(quotationQueryKey(value.id), value); await queryClient.invalidateQueries({ queryKey: QUOTATION_LIST_QUERY_KEY }); if (!quotationId) await navigate({ to: '/quotations/$quotationId', params: { quotationId: value.id }, replace: true }) } })
  const confirm = useMutation({ mutationFn: () => confirmQuotation(quotationId!, query.data!.updated_at), onSuccess: (value) => { queryClient.setQueryData(quotationQueryKey(value.id), value); void queryClient.invalidateQueries({ queryKey: QUOTATION_LIST_QUERY_KEY }) } })
  const clone = useMutation({ mutationFn: () => cloneQuotation(quotationId!, new Date().toLocaleDateString('en-CA')), onSuccess: async (value) => { await queryClient.invalidateQueries({ queryKey: QUOTATION_LIST_QUERY_KEY }); await navigate({ to: '/quotations/$quotationId', params: { quotationId: value.id } }) } })
  const voidQuote = useMutation({ mutationFn: () => voidQuotation(quotationId!, query.data!.updated_at, voidReason), onSuccess: (value) => { queryClient.setQueryData(quotationQueryKey(value.id), value); setVoidReason(''); void queryClient.invalidateQueries({ queryKey: QUOTATION_LIST_QUERY_KEY }) } })
  const convert = useMutation({ mutationFn: () => convertQuotation({ quotation_id: quotationId!, item_ids: query.data!.items.map((item) => item.id) }), onSuccess: (productionCase) => navigate({ to: '/cases/$caseId', params: { caseId: productionCase.id } }) })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 quotations.read 權限。" eyebrow="權限限制" role="alert" title="沒有報價資料權限" />
  if (quotationId && query.isPending) return <SystemState action={<span>請稍候</span>} code="QUO" description="正在讀取報價資料。" eyebrow="資料讀取" role="status" title="正在載入報價" />
  if (query.isError) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入報價" />
  const value = query.data; const editable = canManage && (!value || value.status === 'draft')
  const errors = [save.error, confirm.error, clone.error, voidQuote.error, convert.error].filter(Boolean)
  function updateItem(key: string, field: keyof QuotationItemDraft, next: string) { setDraft((current) => ({ ...current, items: current.items.map((item) => item.key === key ? { ...item, [field]: next } : item) })); setValidationIssues((current) => current.filter((issue) => issue.key !== `${key}-${field}`)) }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const issues = collectFormValidationIssues(form)
    setValidationIssues(issues)
    if (issues.length) {
      requestAnimationFrame(() => form.querySelector<HTMLElement>(`[data-error-key="${issues[0].key}"]`)?.focus())
      return
    }
    save.mutate()
  }
  const actions = [
    { label: '另存新檔', disabled: !quotationId || !canManage, onClick: () => clone.mutate() },
    { label: '存檔', disabled: !editable || save.isPending, tone: 'primary' as const, onClick: () => document.querySelector<HTMLFormElement>('#quotation-form')?.requestSubmit() },
    { label: '取消', onClick: () => void navigate({ to: '/quotations' }) },
    { label: '列印', disabled: !quotationId, onClick: () => quotationId ? void navigate({ to: '/quotations/$quotationId/print', params: { quotationId } }) : undefined },
  ]
  return <form className={`ui-pattern-stack quotation-page${validationIssues.length ? ' quotation-page--validated' : ''}`} id="quotation-form" noValidate onSubmit={submit} ref={formRef}>
    <PageHeader eyebrow="報價管理 / 單頁建檔" title={value ? `${value.document_number} 報價單` : '新增報價單'} description="欄位、順序與動作依公司報價建檔稿；沒有稅額欄，客戶與公司資料建立時即保存快照。" actions={actions} />
    <FormValidationSummary formRef={formRef} issues={validationIssues} />
    {value ? <div className="quotation-status-line"><StatusLabel tone={value.status === 'confirmed' ? 'success' : value.status === 'draft' ? 'working' : 'neutral'}>{value.status === 'confirmed' ? '已確認' : value.status === 'draft' ? '草稿' : '已作廢'}</StatusLabel>{value.source_quotation_id ? <span>另存來源：{value.source_quotation_id}</span> : null}</div> : null}
    <Section title="客戶與報價資料"><div className="ui-form-grid ui-form-grid--three"><Field label="客戶" required><select data-error-key="customer_id" disabled={!editable || customers.isPending} name="customer_id" onChange={(event) => { setDraft({ ...draft, customer_id: event.target.value }); setValidationIssues((current) => current.filter((issue) => issue.key !== 'customer_id')) }} required value={draft.customer_id}><option value="">請選擇客戶</option>{customers.data?.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.code} {customer.name}</option>)}</select></Field><Field label="報價號碼" hint="首次存檔由系統配置"><input disabled value={value?.document_number ?? '存檔後自動產生'} /></Field><Field label="報價日期" required><input data-error-key="quotation_date" disabled={!editable} name="quotation_date" onChange={(event) => { setDraft({ ...draft, quotation_date: event.target.value }); setValidationIssues((current) => current.filter((issue) => issue.key !== 'quotation_date')) }} required type="date" value={draft.quotation_date} /></Field></div>{value ? <div className="quotation-snapshot">快照客戶：{String(value.customer_snapshot.name ?? '')} | 聯絡人：{String(value.customer_snapshot.contact_name ?? '—')} | 電話：{String(value.customer_snapshot.phone ?? '—')} | 傳真：{String(value.customer_snapshot.fax ?? '—')} | 地址：{String(value.customer_snapshot.address ?? '—')}</div> : null}</Section>
    <Section title="報價明細" description="序號依目前排列自動產生；每筆附註與整張報價備註分開保存。" actions={editable ? <button className="ui-button ui-button--secondary" onClick={() => setDraft((current) => ({ ...current, items: [...current.items, emptyItem()] }))} type="button">新增明細</button> : undefined}><DataTableFrame><table className="ui-data-table quotation-items"><thead><tr><th scope="col">序號</th><th scope="col">品名＊</th><th scope="col">尺寸</th><th scope="col">紙質</th><th scope="col">顏色</th><th scope="col">上光</th><th scope="col">數量＊</th><th scope="col">版費＊</th><th scope="col">刀模費＊</th><th scope="col">單價＊</th><th scope="col">附註</th>{editable ? <th scope="col">操作</th> : null}</tr></thead><tbody>{draft.items.map((item, index) => <tr key={item.key}><th scope="row">{String(index + 1).padStart(2, '0')}</th>{(['product_name','size','paper','color','coating'] as const).map((field) => <td key={field}><input aria-label={`第 ${index + 1} 筆${itemLabels[field]}`} data-error-key={`${item.key}-${field}`} disabled={!editable} maxLength={field === 'product_name' || field === 'size' || field === 'paper' ? 200 : 100} name={`items.${index}.${field}`} onChange={(event) => updateItem(item.key, field, event.target.value)} required={field === 'product_name'} value={item[field]} /></td>)}{(['quantity','plate_fee','die_fee','unit_price'] as const).map((field) => <td key={field}><input aria-label={`第 ${index + 1} 筆${itemLabels[field]}`} data-error-key={`${item.key}-${field}`} disabled={!editable} min={field === 'quantity' ? '0.0001' : '0'} name={`items.${index}.${field}`} onChange={(event) => updateItem(item.key, field, event.target.value)} required step="0.0001" type="number" value={item[field]} /></td>)}<td><input aria-label={`第 ${index + 1} 筆附註`} data-error-key={`${item.key}-note`} disabled={!editable} maxLength={2000} name={`items.${index}.note`} onChange={(event) => updateItem(item.key, 'note', event.target.value)} value={item.note} /></td>{editable ? <td><button className="ui-text-button" disabled={draft.items.length === 1} onClick={() => { setDraft((current) => ({ ...current, items: current.items.filter((candidate) => candidate.key !== item.key) })); setValidationIssues((current) => current.filter((issue) => !issue.key.startsWith(`${item.key}-`))) }} type="button">刪除</button></td> : null}</tr>)}</tbody></table></DataTableFrame></Section>
    <Section title="報價備註"><Field label="整張報價備註" hint="與每筆明細附註分開"><textarea disabled={!editable} maxLength={4000} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} rows={5} value={draft.notes} /></Field></Section>
    {value && canConfirm && value.status !== 'void' ? <Section title="狀態操作" description="確認後內容即凍結；作廢保留原單號、原因與稽核紀錄，不會回收號碼。"><div className="quotation-lifecycle-actions">{value.status === 'draft' ? <button className="ui-button ui-button--secondary" disabled={confirm.isPending} onClick={() => confirm.mutate()} type="button">確認報價</button> : null}<Field label="作廢原因" required><input maxLength={1000} onChange={(event) => setVoidReason(event.target.value)} placeholder="請輸入作廢原因" value={voidReason} /></Field><button className="ui-button ui-button--danger" disabled={!voidReason.trim() || voidQuote.isPending} onClick={() => voidQuote.mutate()} type="button">作廢報價</button></div></Section> : null}
    {value?.status === 'confirmed' && canCreateCase ? <Section title="轉入生產案件" description="將本報價全部明細一次建立為一個案件；每筆報價明細各建立一張可再調整的草稿工單。"><button className="ui-button ui-button--primary" disabled={convert.isPending} onClick={() => convert.mutate()} type="button">建立案件與 {value.items.length} 張工單</button></Section> : null}
    {value?.status === 'void' ? <p className="quotation-void-reason">作廢原因：{value.void_reason}</p> : null}
    {errors.length ? <p className="company-profile-message company-profile-message--error" role="alert">{getApiErrorMessage(errors[0])}</p> : null}
    <footer className="quotation-action-bar"><button className="ui-button ui-button--secondary" disabled={!quotationId || !canManage} onClick={() => clone.mutate()} type="button">另存新檔</button><button className="ui-button ui-button--primary" disabled={!editable || save.isPending} type="submit">存檔</button><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/quotations' })} type="button">取消</button><button className="ui-button ui-button--secondary" disabled={!quotationId} onClick={() => quotationId ? void navigate({ to: '/quotations/$quotationId/print', params: { quotationId } }) : undefined} type="button">列印</button></footer>
  </form>
}
