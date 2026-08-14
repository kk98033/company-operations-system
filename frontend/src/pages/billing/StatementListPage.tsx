import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { createStatement, listPendingStatements, listStatements, BILLING_QUERY_KEY } from '../../api/billing'
import { getOrganizationSettings } from '../../api/organizationSettings'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { CsvExportButton } from '../../ui/CsvExportButton'

const statuses = { draft: ['草稿', 'neutral'], issued: ['已請款', 'working'], partially_paid: ['部分收款', 'warning'], paid: ['已收款', 'success'], cancelled: ['已取消', 'danger'] } as const
const today = () => new Date().toLocaleDateString('sv-SE')
const monthStart = () => `${today().slice(0, 7)}-01`

export function StatementListPage() {
  const canRead = useHasCapability('statement.read'); const canIssue = useHasCapability('statement.issue'); const navigate = useNavigate(); const cache = useQueryClient()
  const [selected, setSelected] = useState<Set<string>>(new Set()); const [taxEnabled, setTaxEnabled] = useState(false)
  const pending = useQuery({ queryKey: [...BILLING_QUERY_KEY, 'pending'], queryFn: () => listPendingStatements(), enabled: canRead })
  const statements = useQuery({ queryKey: [...BILLING_QUERY_KEY, 'statements'], queryFn: () => listStatements(), enabled: canRead })
  const settings = useQuery({ queryKey: ['organization-settings'], queryFn: getOrganizationSettings, enabled: canIssue })
  const selectedRows = useMemo(() => pending.data?.items.filter((item) => selected.has(item.pricing_item_id)) ?? [], [pending.data, selected])
  const oneCustomer = new Set(selectedRows.map((item) => item.customer_id)).size <= 1
  const tax = settings.data?.statement_tax
  const create = useMutation({ mutationFn: () => createStatement({ statement_date: today(), period_from: monthStart(), period_to: today(), pricing_item_ids: [...selected], tax_enabled: taxEnabled, tax_rate_percent: taxEnabled ? tax?.tax_rate_percent : null, rounding_scope: taxEnabled ? tax?.rounding_scope : null, rounding_decimal_places: taxEnabled ? tax?.rounding_decimal_places : null, notes: null, idempotency_key: crypto.randomUUID() }), onSuccess: async (row) => { await cache.invalidateQueries({ queryKey: BILLING_QUERY_KEY }); void navigate({ to: '/statements/$statementId', params: { statementId: row.id } }) } })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 statement.read 權限。" eyebrow="權限限制" role="alert" title="沒有對帳資料權限" />
  return <div className="ui-pattern-stack billing-page"><PageHeader eyebrow="請款／對帳" title="待請款與對帳單" description="第一版只有一種正式對帳單；請款是狀態，不另外複製第二份文件。" />
    <div className="ui-page-tools"><CsvExportButton dataset="statements" /></div>
    <Section title="待請款計價明細" description="只列已確認計價；同一計價明細只能存在於一張有效對帳單。">
      {pending.isPending ? <p>正在載入…</p> : pending.isError ? <p role="alert">{getApiErrorMessage(pending.error)}</p> : <DataTableFrame footer={<span>已選 {selected.size} 筆／共 {pending.data?.total_items ?? 0} 筆</span>}><table className="ui-data-table"><thead><tr><th>選取</th><th>計價單</th><th>日期</th><th>客戶</th><th>內容</th><th>金額</th></tr></thead><tbody>{pending.data?.items.length ? pending.data.items.map((item) => <tr key={item.pricing_item_id}><td><input aria-label={`選取 ${item.pricing_document_number} ${item.content}`} checked={selected.has(item.pricing_item_id)} onChange={(event) => setSelected((current) => { const next = new Set(current); if (event.target.checked) next.add(item.pricing_item_id); else next.delete(item.pricing_item_id); return next })} type="checkbox" /></td><th scope="row">{item.pricing_document_number}</th><td>{item.pricing_date}</td><td>{item.customer_name}</td><td>{item.content}</td><td>{item.amount}</td></tr>) : <tr><td colSpan={6}>目前沒有待請款明細。</td></tr>}</tbody></table></DataTableFrame>}
      {canIssue ? <div className="billing-actions"><label className="billing-tax-toggle"><input checked={taxEnabled} disabled={!tax?.enabled} onChange={(event) => setTaxEnabled(event.target.checked)} type="checkbox" /> 本張對帳單計稅{!tax?.enabled ? '（公司預設關閉）' : ''}</label><button className="ui-button ui-button--primary" disabled={!selected.size || !oneCustomer || create.isPending || (taxEnabled && !tax?.tax_rate_percent)} onClick={() => create.mutate()} type="button">{create.isPending ? '建立中…' : `建立對帳草稿（${selected.size}）`}</button>{!oneCustomer ? <p className="ui-inline-error">一張對帳單只能包含同一客戶。</p> : null}{create.isError ? <p className="ui-inline-error" role="alert">{getApiErrorMessage(create.error)}</p> : null}</div> : null}
    </Section>
    <Section title="對帳單查詢"><DataTableFrame footer={<span>共 {statements.data?.total_items ?? 0} 筆</span>}><table className="ui-data-table"><thead><tr><th>對帳單號</th><th>日期</th><th>客戶</th><th>總額</th><th>已收</th><th>未收</th><th>狀態</th><th>操作</th></tr></thead><tbody>{statements.data?.items.length ? statements.data.items.map((item) => { const state = statuses[item.status]; return <tr key={item.id}><th scope="row">{item.document_number}</th><td>{item.statement_date}</td><td>{item.customer_name}</td><td>{item.grand_total}</td><td>{item.paid_amount}</td><td>{item.outstanding_amount}</td><td><StatusLabel tone={state[1]}>{state[0]}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/statements/$statementId', params: { statementId: item.id } })} type="button">查看</button></td></tr> }) : <tr><td colSpan={8}>目前沒有對帳單。</td></tr>}</tbody></table></DataTableFrame></Section>
  </div>
}
