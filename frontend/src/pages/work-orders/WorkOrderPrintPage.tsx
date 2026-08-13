import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { attachmentQueryKey, getWorkOrder, listAttachments, workOrderQueryKey } from '../../api/workOrders'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { SystemState } from '../../ui/UiPatterns'
import { DocumentPdfButton } from '../document-exports/DocumentPdfButton'

const printCodes = ['plate','proof','printing','coating','mounting','die_cutting','finishing','gluing','other']
const checked = (value: boolean) => value ? '☑' : '☐'

export function WorkOrderPrintPage() {
  const { workOrderId } = useParams({ from: '/authenticated/work-orders/$workOrderId/print' }); const navigate = useNavigate(); const canRead = useHasCapability('work_orders.read')
  const query = useQuery({ queryKey: workOrderQueryKey(workOrderId), queryFn: () => getWorkOrder(workOrderId), enabled: canRead })
  const attachments = useQuery({ queryKey: attachmentQueryKey(workOrderId), queryFn: () => listAttachments(workOrderId), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="沒有工單列印權限。" eyebrow="權限限制" role="alert" title="無法列印" />
  if (query.isPending || attachments.isPending) return <SystemState action={<span>請稍候</span>} code="A4" description="正在準備工單列印資料。" eyebrow="列印預覽" role="status" title="正在載入" />
  if (query.isError || attachments.isError) return <SystemState action={<span>返回工單</span>} code="ERR" description={getApiErrorMessage(query.error ?? attachments.error)} eyebrow="資料異常" role="alert" title="無法載入列印資料" />
  const item = query.data; const organization = item.organization_snapshot; const customer = item.customer_snapshot; const print = item.print_specification ?? {}; const front = print.front ?? {}; const back = print.back ?? {}
  const papers = Object.fromEntries(item.papers.map((paper) => [paper.type, paper]))
  const processes = item.processes.filter((process) => printCodes.includes(process.code))
  return <div className="work-order-print-page"><div className="work-order-print-actions"><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/work-orders/$workOrderId', params: { workOrderId } })} type="button">返回工單</button><button className="ui-button ui-button--secondary" onClick={() => window.print()} type="button">列印 A4 直向</button><DocumentPdfButton documentId={workOrderId} documentType="work_order" /></div>
    <article className="work-order-print-sheet"><header><div><h1>{String(organization.name ?? '')}</h1><p>{String(organization.phone ?? '')} | {String(organization.fax ?? '')} | {String(organization.email ?? '')}</p><p>{String(organization.address ?? '')}</p></div><strong>工 作 單</strong></header>
      <section className="work-order-print-meta"><div>客戶：{String(customer.code ?? '')} {String(customer.name ?? '')}</div><div>工單號：{item.document_number}</div><div>客戶單號：{item.customer_order_number ?? '—'}</div><div>訂購日期：{item.order_date}</div><div>電話：{String(customer.phone ?? '—')}</div><div>交貨日期：{item.delivery_date ?? '—'}</div><div className="wide">品名：{item.product_name}</div><div>數量：{item.order_quantity}</div></section>
      <section><h2>備紙</h2><table><thead><tr><th>類型</th><th>供應商</th><th>紙質</th><th>廠別</th><th>尺寸</th><th>數量</th><th>備註</th></tr></thead><tbody>{[['face','面紙'],['back','底紙'],['flute','浪紙']].map(([code,label]) => { const paper = papers[code]; return <tr key={code}><th>{label}</th><td>{paper?.vendor ?? ''}</td><td>{paper?.paper ?? ''}</td><td>{paper?.mill ?? ''}</td><td>{paper?.size ?? ''}</td><td>{paper?.quantity ?? ''}</td><td>{paper?.note ?? ''}</td></tr> })}</tbody></table></section>
      <section className="work-order-print-spec"><h2>印刷</h2><p>尺寸 {print.length ?? ''} × {print.width ?? ''} | K數 {print.k_count ?? ''} | 模數 {print.imposition_count ?? ''} | 數量 {print.print_quantity ?? ''} | ±量 {print.variance ?? ''}</p><div><strong>正面</strong> {checked(front.c ?? false)}C {checked(front.m ?? false)}M {checked(front.y ?? false)}Y {checked(front.k ?? false)}K | 特：{front.special_colors ?? ''}</div><div><strong>反面</strong> {checked(back.c ?? false)}C {checked(back.m ?? false)}M {checked(back.y ?? false)}Y {checked(back.k ?? false)}K | 特：{back.special_colors ?? ''}</div></section>
      <section><h2>製程（公司列印稿固定 9 道）</h2><table><thead><tr><th>製程</th><th>協力廠</th><th>內容</th></tr></thead><tbody>{processes.map((process) => <tr key={process.code}><th>{process.name}</th><td>{process.vendor ?? ''}</td><td>{[process.content, process.coating_type, process.die_number, process.packing].filter(Boolean).join('／')}</td></tr>)}</tbody></table></section>
      {attachments.data?.length ? <section className="work-order-print-attachments"><h2>附件</h2><div>{attachments.data.map((attachment) => attachment.mime_type.startsWith('image/') ? <figure key={attachment.id}><img alt={attachment.filename} src={`/api/v1/work-orders/${workOrderId}/attachments/${attachment.id}`} /><figcaption>{attachment.filename}</figcaption></figure> : <p key={attachment.id}>PDF 附件：{attachment.filename}</p>)}</div></section> : null}
      <footer><strong>備註</strong><p>{item.notes || '—'}</p><p>單價 {item.unit_price} | 版費 {item.plate_fee} | 刀模費 {item.die_fee}</p></footer>
    </article>
  </div>
}
