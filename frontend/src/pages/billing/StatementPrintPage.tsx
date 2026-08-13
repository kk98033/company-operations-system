import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { getStatement, statementQueryKey } from '../../api/billing'
import { getOrganizationProfile } from '../../api/organizationProfile'
import { SystemState } from '../../ui/UiPatterns'
import { DocumentPdfButton } from '../document-exports/DocumentPdfButton'

export function StatementPrintPage() {
  const { statementId } = useParams({ strict: false }) as { statementId: string }
  const navigate = useNavigate()
  const query = useQuery({ queryKey: statementQueryKey(statementId), queryFn: () => getStatement(statementId) })
  const company = useQuery({ queryKey: ['organization-profile'], queryFn: getOrganizationProfile })
  if (query.isPending || company.isPending) return <p>正在準備對帳單…</p>
  if (!query.data || !company.data) return <SystemState action={<span>返回後重試</span>} code="ERR" description="對帳單或公司資料無法載入。" eyebrow="列印資料異常" role="alert" title="無法產生對帳單" />
  const row = query.data
  return <div className="statement-print-shell"><div className="statement-print-toolbar"><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/statements/$statementId', params: { statementId } })} type="button">返回</button><button className="ui-button ui-button--secondary" onClick={() => window.print()} type="button">列印 A4</button><DocumentPdfButton documentId={statementId} documentType="statement" /></div><main className="statement-print"><header><h1>{company.data.name}</h1><h2>對帳單</h2><dl><div><dt>單號</dt><dd>{row.document_number}</dd></div><div><dt>日期</dt><dd>{row.statement_date}</dd></div><div><dt>客戶</dt><dd>{row.customer_name}</dd></div><div><dt>期間</dt><dd>{row.period_from}～{row.period_to}</dd></div></dl></header><table><thead><tr><th>項次</th><th>內容</th><th>數量</th><th>單價</th><th>版費</th><th>刀模費</th><th>金額</th></tr></thead><tbody>{row.items.map((item) => <tr key={item.id}><td>{item.line_no}</td><td>{item.content}</td><td>{item.quantity}</td><td>{item.unit_price}</td><td>{item.plate_fee}</td><td>{item.die_fee}</td><td>{item.amount}</td></tr>)}</tbody></table><footer><dl><div><dt>未稅</dt><dd>{row.subtotal_before_rounding}</dd></div><div><dt>取整</dt><dd>{row.rounding_adjustment}</dd></div><div><dt>稅額</dt><dd>{row.tax_amount}</dd></div><div><dt>總額</dt><dd>{row.grand_total}</dd></div></dl><p>計稅：{row.tax_enabled ? `${row.tax_rate_percent}%` : '不計稅'}</p></footer></main></div>
}
