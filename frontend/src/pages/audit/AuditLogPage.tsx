import { FormEvent, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AUDIT_LOGS_QUERY_KEY, getAuditLogs } from '../../api/audit'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import {
  DataTableFrame,
  PageHeader,
  Section,
  StatusLabel,
  SystemState,
} from '../../ui/UiPatterns'

const PAGE_SIZE = 25

function displayTime(value: string) {
  return new Intl.DateTimeFormat('zh-TW', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(new Date(value))
}

function shortId(value: string | null | undefined) {
  return value ? value.slice(0, 8) : '—'
}

export function AuditLogPage() {
  const canRead = useHasCapability('audit.read')
  const [draftKeyword, setDraftKeyword] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const auditQuery = useQuery({
    queryKey: [...AUDIT_LOGS_QUERY_KEY, page, keyword],
    queryFn: () => getAuditLogs({
      keyword: keyword || undefined,
      page,
      page_size: PAGE_SIZE,
      sort_by: 'created_at',
      sort_direction: 'desc',
    }),
    enabled: canRead,
  })

  if (!canRead) {
    return (
      <SystemState
        action={<span>請聯絡公司系統管理者</span>}
        code="403"
        description="只有取得 audit.read 權限的公司成員可以查看操作紀錄。"
        eyebrow="權限限制"
        role="alert"
        title="沒有稽核查詢權限"
      />
    )
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setKeyword(draftKeyword.trim())
    setPage(1)
  }

  const result = auditQuery.data

  return (
    <div className="ui-pattern-stack audit-log-page">
      <PageHeader
        eyebrow="系統管理 / 唯讀"
        title="操作稽核"
        description="只顯示目前公司的不可變操作紀錄；密碼、Cookie、Token、Secret 與檔案內容不會寫入。"
      />

      <Section title="查詢條件" description="可依動作、對象、文件號碼或原因關鍵字縮小結果。">
        <form className="audit-log-search" onSubmit={submitSearch} role="search">
          <label htmlFor="audit-keyword">關鍵字</label>
          <input
            id="audit-keyword"
            maxLength={100}
            onChange={(event) => setDraftKeyword(event.target.value)}
            placeholder="例如 role.update 或工單號"
            type="search"
            value={draftKeyword}
          />
          <button className="ui-button ui-button--primary" type="submit">查詢</button>
        </form>
      </Section>

      {auditQuery.isPending ? (
        <SystemState
          action={<span>請稍候</span>}
          code="LOG"
          description="正在從伺服器讀取目前公司的操作紀錄。"
          eyebrow="資料讀取"
          role="status"
          title="正在載入稽核紀錄"
        />
      ) : auditQuery.isError ? (
        <SystemState
          action={(
            <button
              className="ui-button ui-button--primary"
              onClick={() => void auditQuery.refetch()}
              type="button"
            >
              重新載入
            </button>
          )}
          code="ERR"
          description={getApiErrorMessage(auditQuery.error)}
          eyebrow="資料異常"
          role="alert"
          title="無法載入稽核紀錄"
        />
      ) : (
        <Section title="稽核結果" description="前後值只保存必要且已遮罩的欄位。">
          <DataTableFrame footer={(
            <div className="audit-log-pagination">
              <span>共 {result?.meta.pagination.total_items ?? 0} 筆</span>
              <div>
                <button
                  className="ui-button ui-button--secondary"
                  disabled={!result?.meta.pagination.has_previous}
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                  type="button"
                >上一頁</button>
                <span>第 {result?.meta.pagination.page ?? 1} 頁</span>
                <button
                  className="ui-button ui-button--secondary"
                  disabled={!result?.meta.pagination.has_next}
                  onClick={() => setPage((value) => value + 1)}
                  type="button"
                >下一頁</button>
              </div>
            </div>
          )}>
            <table className="ui-data-table" aria-label="目前公司的操作稽核紀錄">
              <thead>
                <tr>
                  <th className="ui-data-table__sticky" scope="col">時間</th>
                  <th scope="col">動作</th>
                  <th scope="col">對象</th>
                  <th scope="col">文件號</th>
                  <th scope="col">操作者</th>
                  <th scope="col">結果</th>
                  <th scope="col">原因</th>
                  <th scope="col">前後值</th>
                  <th scope="col">Request ID</th>
                </tr>
              </thead>
              <tbody>
                {result?.items.length ? result.items.map((item) => (
                  <tr key={item.id}>
                    <th className="ui-data-table__sticky" scope="row">
                      {displayTime(item.created_at)}
                    </th>
                    <td><code>{item.action}</code></td>
                    <td>{item.entity_type} / {shortId(item.entity_id)}</td>
                    <td>{item.document_number ?? '—'}</td>
                    <td>{shortId(item.actor_user_id)}</td>
                    <td>
                      <StatusLabel tone={item.event_status === 'success' ? 'success' : 'danger'}>
                        {item.event_status === 'success' ? '成功' : '失敗'}
                      </StatusLabel>
                    </td>
                    <td>{item.reason ?? '—'}</td>
                    <td>
                      <details className="audit-log-details">
                        <summary>查看</summary>
                        <pre>{JSON.stringify({ before: item.before_data, after: item.after_data }, null, 2)}</pre>
                      </details>
                    </td>
                    <td><code>{shortId(item.request_id)}</code></td>
                  </tr>
                )) : (
                  <tr><td className="audit-log-empty" colSpan={9}>目前沒有符合條件的稽核紀錄。</td></tr>
                )}
              </tbody>
            </table>
          </DataTableFrame>
        </Section>
      )}
    </div>
  )
}
