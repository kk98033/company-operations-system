import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { listQuotations, QUOTATION_LIST_QUERY_KEY } from '../../api/quotations'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'

export function QuotationListPage() {
  const navigate = useNavigate(); const canRead = useHasCapability('quotations.read'); const canManage = useHasCapability('quotations.manage')
  const [input, setInput] = useState(''); const [keyword, setKeyword] = useState(''); const [status, setStatus] = useState<''|'draft'|'confirmed'|'void'>('')
  const query = useQuery({ queryKey: [...QUOTATION_LIST_QUERY_KEY, keyword, status], queryFn: () => listQuotations({ keyword: keyword || undefined, status: status || undefined }), enabled: canRead })
  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 quotations.read 權限。" eyebrow="權限限制" role="alert" title="沒有報價資料權限" />
  function search(event: FormEvent) { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack quotation-page"><PageHeader eyebrow="報價管理" title="報價單查詢" description="依報價號碼、舊號或客戶名稱查詢；報價不是建立工單的必經流程。" actions={canManage ? [{ label: '新增報價', tone: 'primary', onClick: () => void navigate({ to: '/quotations/new' }) }] : []} />
    <form onSubmit={search}><FilterBar><Field label="關鍵字"><input onChange={(event) => setInput(event.target.value)} placeholder="報價號碼、舊號或客戶" type="search" value={input} /></Field><Field label="狀態"><select onChange={(event) => setStatus(event.target.value as typeof status)} value={status}><option value="">全部</option><option value="draft">草稿</option><option value="confirmed">已確認</option><option value="void">已作廢</option></select></Field><div className="ui-field quotation-filter-action"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div></FilterBar></form>
    {query.isPending ? <SystemState action={<span>請稍候</span>} code="QUO" description="正在讀取報價資料。" eyebrow="資料讀取" role="status" title="正在載入報價" /> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入報價" /> : null}
    {query.data ? <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}><table className="ui-data-table quotation-list-table"><thead><tr><th scope="col">報價號碼</th><th scope="col">日期</th><th scope="col">客戶</th><th scope="col">第一項品名</th><th scope="col">明細數</th><th scope="col">狀態</th><th scope="col">操作</th></tr></thead><tbody>{query.data.items.length === 0 ? <tr><td colSpan={7}>查無報價資料。</td></tr> : query.data.items.map((item) => <tr key={item.id}><th scope="row">{item.document_number}{item.legacy_document_number ? <small>舊號 {item.legacy_document_number}</small> : null}</th><td>{item.quotation_date}</td><td>{item.customer_name}</td><td>{item.first_product_name}</td><td>{item.item_count}</td><td><StatusLabel tone={item.status === 'confirmed' ? 'success' : item.status === 'draft' ? 'working' : 'neutral'}>{item.status === 'confirmed' ? '已確認' : item.status === 'draft' ? '草稿' : '已作廢'}</StatusLabel></td><td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/quotations/$quotationId', params: { quotationId: item.id } })} type="button">{canManage && item.status === 'draft' ? '編輯' : '查看'}</button></td></tr>)}</tbody></table></DataTableFrame> : null}
  </div>
}
