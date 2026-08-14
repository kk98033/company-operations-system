import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { CUSTOMER_LIST_QUERY_KEY, listCustomers } from '../../api/customers'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { CsvExportButton } from '../../ui/CsvExportButton'

export function CustomerListPage() {
  const navigate = useNavigate()
  const canRead = useHasCapability('customers.read')
  const canManage = useHasCapability('customers.manage')
  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<'active' | 'inactive' | ''>('active')
  const query = useQuery({
    queryKey: [...CUSTOMER_LIST_QUERY_KEY, keyword, status],
    queryFn: () => listCustomers({ keyword: keyword || undefined, status: status || undefined }),
    enabled: canRead,
  })

  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 customers.read 權限。" eyebrow="權限限制" role="alert" title="沒有客戶資料權限" />
  function search(event: FormEvent) {
    event.preventDefault()
    setKeyword(keywordInput.trim())
  }

  return (
    <div className="ui-pattern-stack customer-page">
      <PageHeader
        eyebrow="客戶管理"
        title="客戶資料"
        description="依客戶代號、名稱或簡稱查詢目前公司的客戶主檔。"
        actions={canManage ? [{ label: '新增客戶', tone: 'primary', onClick: () => void navigate({ to: '/customers/new' }) }] : []}
      />
      <div className="ui-page-tools"><CsvExportButton dataset="customers" /></div>
      <form onSubmit={search}>
        <FilterBar>
          <Field label="關鍵字"><input onChange={(event) => setKeywordInput(event.target.value)} placeholder="代號、名稱或簡稱" value={keywordInput} /></Field>
          <Field label="狀態"><select onChange={(event) => setStatus(event.target.value as typeof status)} value={status}><option value="">全部</option><option value="active">使用中</option><option value="inactive">已停用</option></select></Field>
          <div className="ui-field customer-filter-action"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">查詢</button></div>
        </FilterBar>
      </form>
      {query.isPending ? <SystemState action={<span>請稍候</span>} code="CUS" description="正在讀取客戶資料。" eyebrow="資料讀取" role="status" title="正在載入客戶" /> : null}
      {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入客戶" /> : null}
      {query.data ? (
        <DataTableFrame footer={<span>共 {query.data.meta.pagination.total_items} 筆</span>}>
          <table className="ui-data-table customer-table">
            <thead><tr><th scope="col">客戶代號</th><th scope="col">名稱</th><th scope="col">簡稱</th><th scope="col">聯絡人</th><th scope="col">電話</th><th scope="col">狀態</th><th scope="col">操作</th></tr></thead>
            <tbody>
              {query.data.items.length === 0 ? <tr><td colSpan={7}>查無符合條件的客戶資料。</td></tr> : query.data.items.map((customer) => (
                <tr key={customer.id}>
                  <th scope="row">{customer.code}</th><td>{customer.name}</td><td>{customer.short_name || '—'}</td><td>{customer.contact_name || '—'}</td><td>{customer.phone || '—'}</td>
                  <td><StatusLabel tone={customer.status === 'active' ? 'success' : 'neutral'}>{customer.status === 'active' ? '使用中' : '已停用'}</StatusLabel></td>
                  <td><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/customers/$customerId', params: { customerId: customer.id } })} type="button">{canManage ? '編輯' : '查看'}</button><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/customers/$customerId/overview', params: { customerId: customer.id } })} type="button">360 總覽</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataTableFrame>
      ) : null}
    </div>
  )
}
