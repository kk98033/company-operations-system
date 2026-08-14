import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { attachmentQueryKey, deleteAttachment, listAttachments, uploadAttachment } from '../../api/workOrders'
import { getApiErrorMessage } from '../../api/errorMessage'
import { Field, Section } from '../../ui/UiPatterns'

type Props = { notes: string; editable: boolean; workOrderId?: string; onChange: (value: string) => void }

export function WorkOrderNotesSection({ notes, editable, workOrderId, onChange }: Props) {
  const queryClient = useQueryClient()
  const attachments = useQuery({ queryKey: workOrderId ? attachmentQueryKey(workOrderId) : ['work-orders', 'new', 'attachments'], queryFn: () => listAttachments(workOrderId!), enabled: Boolean(workOrderId) })
  const upload = useMutation({ mutationFn: (file: File) => uploadAttachment(workOrderId!, file), onSuccess: () => queryClient.invalidateQueries({ queryKey: attachmentQueryKey(workOrderId!) }) })
  const remove = useMutation({ mutationFn: (id: string) => deleteAttachment(workOrderId!, id), onSuccess: () => queryClient.invalidateQueries({ queryKey: attachmentQueryKey(workOrderId!) }) })
  const error = upload.error ?? remove.error
  return <div className="work-order-prototype__anchor" id="work-order-notes" tabIndex={-1}>
    <Section title="備註與圖片" description="備註可留空並支援長文字；圖片與 PDF 必須登入且具工單權限才能下載。">
      <div className="work-order-notes-grid">
        <Field label="工單備註" hint="可留空；最多 12,000 個字元"><textarea data-error-key="notes" disabled={!editable} maxLength={12000} name="notes" onChange={(event) => onChange(event.target.value)} rows={10} value={notes} /></Field>
        <fieldset className="work-order-attachment-placeholder"><legend>私人附件</legend>
          {attachments.data?.length ? <ul className="work-order-attachment-list">{attachments.data.map((item) => <li key={item.id}><a href={`/api/v1/work-orders/${workOrderId}/attachments/${item.id}`} rel="noreferrer" target="_blank">{item.filename}</a><span>{Math.ceil(item.size_bytes / 1024)} KB</span>{editable ? <button className="ui-text-button" disabled={remove.isPending} onClick={() => remove.mutate(item.id)} type="button">刪除</button> : null}</li>)}</ul> : <div aria-label="刀模圖預覽區" role="img">尚未加入刀模圖或成品參考圖</div>}
          <label className={`ui-button ui-button--secondary${!workOrderId || !editable ? ' is-disabled' : ''}`}>選擇附件<input accept="image/jpeg,image/png,image/webp,application/pdf" disabled={!workOrderId || !editable || upload.isPending} hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.target.value = '' }} type="file" /></label>
          {!workOrderId ? <small>請先存檔，再上傳附件。</small> : null}
          {error ? <p className="company-profile-message company-profile-message--error" role="alert">{getApiErrorMessage(error)}</p> : null}
        </fieldset>
      </div>
    </Section>
  </div>
}
