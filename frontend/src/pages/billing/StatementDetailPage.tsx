import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { cancelStatement, getStatement, issueStatement, statementQueryKey, BILLING_QUERY_KEY } from '../../api/billing'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

const statuses = { draft: ['草稿', 'neutral'], issued: ['已請款', 'working'], partially_paid: ['部分收款', 'warning'], paid: ['已收款', 'success'], cancelled: ['已取消', 'danger'] } as const
export function StatementDetailPage() {
  const { statementId } = useParams({ strict: false }) as { statementId: string }; const navigate = useNavigate(); const cache = useQueryClient()
  const canRead = useHasCapability('statement.read'); const canIssue = useHasCapability('statement.issue'); const canCancel = useHasCapability('statement.cancel')
  const query = useQuery({ queryKey: statementQueryKey(statementId), queryFn: () => getStatement(statementId), enabled: canRead })
  const refresh = async (row: unknown) => { cache.setQueryData(statementQueryKey(statementId), row); await cache.invalidateQueries({ queryKey: BILLING_QUERY_KEY }) }
  const issue = useMutation({ mutationFn: () => issueStatement(statementId, { expected_version: query.data!.version, idempotency_key: crypto.randomUUID() }), onSuccess: refresh })
  const cancel = useMutation({ mutationFn: () => cancelStatement(statementId, { expected_version: query.data!.version, idempotency_key: crypto.randomUUID(), reason: '使用者取消對帳單' }), onSuccess: refresh })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 statement.read 權限。" eyebrow="權限限制" role="alert" title="沒有對帳資料權限" />
  if (query.isPending) return <p>正在載入對帳單…</p>; if (query.isError) return <p role="alert">{getApiErrorMessage(query.error)}</p>
  const row = query.data; const state = statuses[row.status]
  return <div className="ui-pattern-stack billing-page"><PageHeader eyebrow="對帳單詳情" title={row.document_number} description={`${row.customer_name}｜期間 ${row.period_from}～${row.period_to}`} actions={[{ label: '返回清單', onClick: () => void navigate({ to: '/statements' }) }, { label: 'A4 列印', onClick: () => void navigate({ to: '/statements/$statementId/print', params: { statementId } }) }]} />
    <Section title="請款狀態"><div className="billing-summary"><StatusLabel tone={state[1]}>{state[0]}</StatusLabel><span>未稅 {row.subtotal_before_rounding}</span><span>取整調整 {row.rounding_adjustment}</span><span>稅額 {row.tax_amount}</span><strong>總額 {row.grand_total}</strong><span>已收 {row.paid_amount}</span><strong>未收 {row.outstanding_amount}</strong></div><p>{row.tax_enabled ? `本張已啟用計稅：${row.tax_rate_percent}%／${row.rounding_scope}／${row.rounding_decimal_places} 位` : '本張不計稅（稅額 0）'}</p></Section>
    <Section title="明細與來源"><DataTableFrame><table className="ui-data-table"><thead><tr><th>項次</th><th>計價來源</th><th>內容</th><th>數量</th><th>單價</th><th>版費</th><th>刀模費</th><th>金額</th></tr></thead><tbody>{row.items.map((item) => <tr key={item.id}><td>{item.line_no}</td><td>{String(item.source_snapshot.pricing_document_number ?? '—')}</td><th scope="row">{item.content}</th><td>{item.quantity}</td><td>{item.unit_price}</td><td>{item.plate_fee}</td><td>{item.die_fee}</td><td>{item.amount}</td></tr>)}</tbody></table></DataTableFrame></Section>
    <div className="billing-actions">{canIssue && row.status === 'draft' ? <button className="ui-button ui-button--primary" disabled={issue.isPending} onClick={() => issue.mutate()} type="button">發行並進入已請款</button> : null}{canCancel && ['draft', 'issued'].includes(row.status) ? <button className="ui-button ui-button--danger" disabled={cancel.isPending} onClick={() => cancel.mutate()} type="button">取消對帳單</button> : null}{issue.isError || cancel.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(issue.error ?? cancel.error)}</p> : null}</div>
  </div>
}
