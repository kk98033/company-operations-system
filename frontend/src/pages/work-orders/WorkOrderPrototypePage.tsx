import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { listCustomers } from '../../api/customers'
import {
  cloneWorkOrder, confirmWorkOrder, createWorkOrder, getWorkOrder,
  updateWorkOrder, voidWorkOrder, WORK_ORDER_LIST_QUERY_KEY, workOrderQueryKey,
} from '../../api/workOrders'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { PaperPreparationSection } from './PaperPreparationSection'
import { PrintingSpecificationSection } from './PrintingSpecificationSection'
import { ProcessPlanningSection } from './ProcessPlanningSection'
import { WorkOrderBasicSection } from './WorkOrderBasicSection'
import { WorkOrderNotesSection } from './WorkOrderNotesSection'
import { emptyWorkOrderDraft, responseToDraft, toPayload, type PaperDraft, type ProcessDraft, type WorkOrderDraft } from './workOrderDraft'

const sections = [['basic','客戶與訂單'],['paper','備紙'],['printing','印刷'],['process','製程'],['notes','備註與圖片']] as const

export function WorkOrderNewPage() { return <WorkOrderEditorPage /> }
export function WorkOrderPrototypePage() { return <WorkOrderEditorPage /> }
export function WorkOrderEditPage() { const { workOrderId } = useParams({ from: '/authenticated/work-orders/$workOrderId' }); return <WorkOrderEditorPage workOrderId={workOrderId} /> }

function WorkOrderEditorPage({ workOrderId }: { workOrderId?: string }) {
  const navigate = useNavigate(); const queryClient = useQueryClient()
  const canRead = useHasCapability('work_orders.read'); const canManage = useHasCapability('work_orders.manage'); const canConfirm = useHasCapability('work_orders.confirm')
  const [draft, setDraft] = useState<WorkOrderDraft>(() => emptyWorkOrderDraft())
  const [dirty, setDirty] = useState(false); const [voidReason, setVoidReason] = useState('')
  const query = useQuery({ queryKey: workOrderId ? workOrderQueryKey(workOrderId) : ['work-orders', 'new'], queryFn: () => getWorkOrder(workOrderId!), enabled: Boolean(workOrderId && canRead) })
  const customers = useQuery({ queryKey: ['customers', 'work-order-options'], queryFn: () => listCustomers({ page_size: 100, status: 'active' }), enabled: canRead })
  useEffect(() => { if (query.data) { setDraft(responseToDraft(query.data)); setDirty(false) } }, [query.data])
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn) }, [dirty])
  const save = useMutation({ mutationFn: () => {
    const payload = toPayload(draft)
    if (!workOrderId) return createWorkOrder(payload)
    const values = { ...payload }
    delete values.case_id
    return updateWorkOrder(workOrderId, { ...values, expected_updated_at: query.data!.updated_at })
  }, onSuccess: async (value) => { setDirty(false); queryClient.setQueryData(workOrderQueryKey(value.id), value); await queryClient.invalidateQueries({ queryKey: WORK_ORDER_LIST_QUERY_KEY }); if (!workOrderId) await navigate({ to: '/work-orders/$workOrderId', params: { workOrderId: value.id }, replace: true }) } })
  const confirm = useMutation({ mutationFn: () => confirmWorkOrder(workOrderId!, query.data!.updated_at), onSuccess: (value) => { queryClient.setQueryData(workOrderQueryKey(value.id), value); void queryClient.invalidateQueries({ queryKey: WORK_ORDER_LIST_QUERY_KEY }) } })
  const clone = useMutation({ mutationFn: () => cloneWorkOrder(workOrderId!, new Date().toLocaleDateString('en-CA')), onSuccess: async (value) => { await queryClient.invalidateQueries({ queryKey: WORK_ORDER_LIST_QUERY_KEY }); await navigate({ to: '/work-orders/$workOrderId', params: { workOrderId: value.id } }) } })
  const voidOrder = useMutation({ mutationFn: () => voidWorkOrder(workOrderId!, { expected_updated_at: query.data!.updated_at, reason: voidReason }), onSuccess: (value) => { queryClient.setQueryData(workOrderQueryKey(value.id), value); setVoidReason(''); void queryClient.invalidateQueries({ queryKey: WORK_ORDER_LIST_QUERY_KEY }) } })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 work_orders.read 權限。" eyebrow="權限限制" role="alert" title="沒有工單資料權限" />
  if (workOrderId && query.isPending) return <SystemState action={<span>請稍候</span>} code="WO" description="正在讀取工單。" eyebrow="資料讀取" role="status" title="正在載入工單" />
  if (query.isError) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入工單" />
  const value = query.data; const editable = canManage && (!value || value.status === 'draft')
  const mutate = <K extends keyof WorkOrderDraft>(field: K, next: WorkOrderDraft[K]) => { setDraft((current) => ({ ...current, [field]: next })); setDirty(true) }
  const paper = (index: number, field: keyof PaperDraft, next: string) => mutate('papers', draft.papers.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: next } : item))
  const process = (index: number, field: keyof ProcessDraft, next: string) => mutate('processes', draft.processes.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: next } : item))
  const submit = (event: FormEvent) => { event.preventDefault(); save.mutate() }
  const actions = [
    { label: '另存新檔', disabled: !workOrderId || !canManage, onClick: () => clone.mutate() },
    { label: '存檔', tone: 'primary' as const, disabled: !editable || save.isPending, onClick: () => document.querySelector<HTMLFormElement>('#work-order-form')?.requestSubmit() },
    { label: '取消', onClick: () => { if (!dirty || window.confirm('尚未存檔，確定離開？')) void navigate({ to: '/work-orders' }) } },
    { label: '列印', disabled: !workOrderId, onClick: () => workOrderId ? void navigate({ to: '/work-orders/$workOrderId/print', params: { workOrderId } }) : undefined },
  ]
  const errors = [save.error, confirm.error, clone.error, voidOrder.error].filter(Boolean)
  return <form aria-label="工單整合建檔" className="ui-pattern-stack work-order-prototype" id="work-order-form" onSubmit={submit}>
    <PageHeader actions={actions} description="依公司工單稿把客戶、訂單、備紙、印刷、13 道製程、備註與圖片集中在同一頁。" eyebrow="工單管理 / 單頁建檔" title={value ? `${value.document_number} 工單` : '工單建檔作業'} />
    <div className="module-prototype__notice" role="status"><StatusLabel tone={value?.status === 'confirmed' ? 'success' : 'working'}>{value?.status === 'confirmed' ? '已確認' : value?.status === 'void' ? '已作廢' : '草稿'}</StatusLabel><span>{value ? `案件 ${value.case_id}` : '直接建工單會自動建立單工單案件；也可由已確認報價一次轉入多張。'}</span></div>
    <nav className="work-order-prototype__section-nav" aria-label="工單頁內快速跳轉">{sections.map(([id,label]) => <a href={`#work-order-${id}`} key={id} onClick={() => document.getElementById(`work-order-${id}`)?.focus()}>{label}</a>)}</nav>
    <WorkOrderBasicSection customers={customers.data} documentNumber={value?.document_number} draft={draft} editable={editable} onChange={(field, next) => mutate(field, next)} />
    <PaperPreparationSection editable={editable} onChange={paper} papers={draft.papers} />
    <PrintingSpecificationSection editable={editable} onChange={(next) => mutate('print', next)} value={draft.print} />
    <ProcessPlanningSection editable={editable} onChange={process} processes={draft.processes} />
    <WorkOrderNotesSection editable={editable} notes={draft.notes} onChange={(next) => mutate('notes', next)} workOrderId={workOrderId} />
    {value && canConfirm && value.status !== 'void' ? <Section title="狀態操作" description="確認後凍結內容與 A4 列印快照；作廢保留單號與原因。"><div className="quotation-lifecycle-actions">{value.status === 'draft' ? <button className="ui-button ui-button--secondary" disabled={confirm.isPending} onClick={() => confirm.mutate()} type="button">確認工單</button> : null}<label className="ui-field"><span className="ui-field__label">作廢原因</span><input maxLength={1000} onChange={(event) => setVoidReason(event.target.value)} value={voidReason} /></label><button className="ui-button ui-button--danger" disabled={!voidReason.trim() || voidOrder.isPending} onClick={() => voidOrder.mutate()} type="button">作廢工單</button></div></Section> : null}
    {errors.length ? <p className="company-profile-message company-profile-message--error" role="alert">{getApiErrorMessage(errors[0])}</p> : null}
    <footer className="ui-form-footer work-order-prototype__footer"><span>{dirty ? '有尚未存檔的變更' : '內容已同步'}</span><div>{actions.map((action) => <button className={`ui-button ui-button--${action.tone ?? 'secondary'}`} disabled={action.disabled} key={action.label} onClick={action.onClick} type={action.label === '存檔' ? 'submit' : 'button'}>{action.label}</button>)}</div></footer>
  </form>
}
