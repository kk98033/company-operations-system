import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'

import { searchOperations } from '../../api/operations'
import { getApiErrorMessage } from '../../api/errorMessage'
import { DataTableFrame, Field, FilterBar, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'

const labels: Record<string, string> = { customer: '客戶', quotation: '報價', case: '案件', work_order: '工單', shipment: '出貨', pricing: '計價', statement: '對帳', receipt: '收款' }

export function SearchPage() {
  const [input, setInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const query = useQuery({ queryKey: ['operations', 'search', keyword], queryFn: () => searchOperations(keyword), enabled: keyword.length >= 2 })
  function submit(event: FormEvent) { event.preventDefault(); setKeyword(input.trim()) }
  return <div className="ui-pattern-stack operations-page">
    <PageHeader eyebrow="工作區 / 整合查詢" title="跨模組搜尋" description="以單號、舊號、客戶名稱或客戶代號搜尋；結果只顯示目前帳號有權讀取的模組。" />
    <form onSubmit={submit}><FilterBar><Field label="關鍵字"><input minLength={2} onChange={(event) => setInput(event.target.value)} placeholder="至少 2 個字" value={input} /></Field><div className="ui-field"><span className="ui-field__label">執行</span><button className="ui-button ui-button--primary" type="submit">搜尋</button></div></FilterBar></form>
    {query.isPending && keyword ? <p>搜尋中…</p> : null}
    {query.isError ? <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重試</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="搜尋異常" role="alert" title="無法完成搜尋" /> : null}
    {query.data ? <DataTableFrame footer={<span>顯示 {query.data.items.length} 筆{query.data.truncated ? '（結果已達上限，請縮小關鍵字）' : ''}</span>}><table className="ui-data-table"><thead><tr><th>類型</th><th>資料</th><th>相關資訊</th><th>狀態</th><th>操作</th></tr></thead><tbody>{query.data.items.length ? query.data.items.map((item) => <tr key={`${item.entity_type}-${item.entity_id}`}><td>{labels[item.entity_type]}</td><th scope="row">{item.primary_text}</th><td>{item.secondary_text || '—'}</td><td><StatusLabel tone="neutral">{item.status || '—'}</StatusLabel></td><td><a className="ui-button ui-button--secondary" href={item.target_path}>開啟</a></td></tr>) : <tr><td colSpan={5}>查無符合資料。</td></tr>}</tbody></table></DataTableFrame> : null}
  </div>
}
