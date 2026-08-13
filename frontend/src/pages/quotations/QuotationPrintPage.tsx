import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { getQuotation, quotationQueryKey } from '../../api/quotations'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { SystemState } from '../../ui/UiPatterns'
import { DocumentPdfButton } from '../document-exports/DocumentPdfButton'

export function QuotationPrintPage() {
  const { quotationId } = useParams({ from: '/authenticated/quotations/$quotationId/print' }); const navigate = useNavigate(); const canRead = useHasCapability('quotations.read')
  const query = useQuery({ queryKey: quotationQueryKey(quotationId), queryFn: () => getQuotation(quotationId), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 quotations.read 權限。" eyebrow="權限限制" role="alert" title="沒有報價資料權限" />
  if (query.isPending) return <SystemState action={<span>請稍候</span>} code="PRINT" description="正在準備列印內容。" eyebrow="列印準備" role="status" title="正在載入報價" />
  if (query.isError) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入報價" />
  const quote = query.data; const organization = quote.organization_snapshot; const customer = quote.customer_snapshot
  return <div className="quotation-print-page"><div className="quotation-print-actions"><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/quotations/$quotationId', params: { quotationId } })} type="button">返回報價</button><button className="ui-button ui-button--secondary" onClick={() => window.print()} type="button">列印 A4 橫向</button><DocumentPdfButton documentId={quotationId} documentType="quotation" /></div><article className="quotation-print-sheet"><header className="quotation-print-header"><div><h1>{String(organization.name ?? '')}</h1><p>{String(organization.address ?? '')}</p><p>電話 {String(organization.phone ?? '—')} | 傳真 {String(organization.fax ?? '—')} | {String(organization.email ?? '')}</p></div><strong>報 價 單</strong></header><section className="quotation-print-customer"><div>客戶：{String(customer.code ?? '')} {String(customer.name ?? '')}</div><div>聯絡人：{String(customer.contact_name ?? '—')}</div><div>電話：{String(customer.phone ?? '—')}</div><div>傳真：{String(customer.fax ?? '—')}</div><div>地址：{String(customer.address ?? '—')}</div><div>報價號碼：{quote.document_number}</div><div>報價日期：{quote.quotation_date}</div></section><table className="quotation-print-table"><thead><tr><th>序號</th><th>品名</th><th>尺寸</th><th>紙質</th><th>顏色</th><th>上光</th><th>版費</th><th>刀模費</th><th>數量</th><th>單價</th><th>附註</th></tr></thead><tbody>{quote.items.map((item) => <tr key={item.id}><td>{String(item.line_number).padStart(2, '0')}</td><td>{item.product_name}</td><td>{item.size ?? ''}</td><td>{item.paper ?? ''}</td><td>{item.color ?? ''}</td><td>{item.coating ?? ''}</td><td>{item.plate_fee}</td><td>{item.die_fee}</td><td>{item.quantity}</td><td>{item.unit_price}</td><td>{item.note ?? ''}</td></tr>)}</tbody></table><footer className="quotation-print-notes"><strong>備註</strong><p>{quote.notes || '-'}</p></footer></article></div>
}
