import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { ManagedSessionResponse } from '../../api/generated/company-system'
import { getApiErrorMessage } from '../../api/errorMessage'
import {
  COMPANY_SESSIONS_QUERY_KEY,
  getCompanySessions,
  getPersonalSessions,
  PERSONAL_SESSIONS_QUERY_KEY,
  revokeCompanySession,
  revokeMembershipSessions,
} from '../../api/sessionManagement'
import { useHasCapability } from '../../auth/capabilities'
import { DataTableFrame, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

const statusLabels = {
  active: '有效',
  expired: '已到期',
  revoked: '已撤銷',
  identity_inactive: '帳號已停用',
} as const

function displayTime(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-TW', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function statusTone(status: ManagedSessionResponse['status']) {
  if (status === 'active') return 'success' as const
  if (status === 'expired') return 'neutral' as const
  return 'danger' as const
}

function SessionTable({
  items,
  companyMode = false,
  pendingId,
  onRevoke,
  onRevokeAll,
}: {
  items: ManagedSessionResponse[]
  companyMode?: boolean
  pendingId?: string
  onRevoke?: (item: ManagedSessionResponse) => void
  onRevokeAll?: (item: ManagedSessionResponse) => void
}) {
  return (
    <DataTableFrame>
      <table className="ui-data-table" aria-label={companyMode ? '公司尚未撤銷的登入工作階段' : '我的登入工作階段'}>
        <thead><tr>
          {companyMode ? <th className="ui-data-table__sticky" scope="col">使用者</th> : null}
          <th className={companyMode ? undefined : 'ui-data-table__sticky'} scope="col">裝置摘要</th>
          <th scope="col">登入時間</th><th scope="col">到期時間</th>
          <th scope="col">狀態</th>{companyMode ? <th scope="col">操作</th> : null}
        </tr></thead>
        <tbody>
          {items.length ? items.map((item) => (
            <tr key={item.id}>
              {companyMode ? (
                <th className="ui-data-table__sticky" scope="row">
                  {item.user.display_name}<small>{item.user.login_name}</small>
                </th>
              ) : null}
              <td className={companyMode ? undefined : 'ui-data-table__sticky'}>
                {item.client_summary}{item.is_current ? <strong className="session-current">目前裝置</strong> : null}
              </td>
              <td>{displayTime(item.created_at)}</td>
              <td>{displayTime(item.expires_at)}</td>
              <td><StatusLabel tone={statusTone(item.status)}>{statusLabels[item.status]}</StatusLabel></td>
              {companyMode ? (
                <td><div className="session-actions">
                  <button
                    className="ui-button ui-button--secondary"
                    disabled={item.is_current || pendingId === item.id}
                    onClick={() => onRevoke?.(item)}
                    type="button"
                  >撤銷此登入</button>
                  <button
                    className="ui-button ui-button--danger"
                    disabled={item.is_current || pendingId === item.id}
                    onClick={() => onRevokeAll?.(item)}
                    type="button"
                  >撤銷此帳號全部</button>
                </div></td>
              ) : null}
            </tr>
          )) : <tr><td colSpan={companyMode ? 6 : 4}>目前沒有可顯示的登入紀錄。</td></tr>}
        </tbody>
      </table>
    </DataTableFrame>
  )
}

export function SessionManagementPage() {
  const canManage = useHasCapability('sessions.manage')
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [pendingId, setPendingId] = useState<string>()
  const personal = useQuery({ queryKey: PERSONAL_SESSIONS_QUERY_KEY, queryFn: getPersonalSessions })
  const company = useQuery({
    queryKey: COMPANY_SESSIONS_QUERY_KEY,
    queryFn: getCompanySessions,
    enabled: canManage,
  })
  const mutation = useMutation({
    mutationFn: async ({ item, all }: { item: ManagedSessionResponse; all: boolean }) => {
      setPendingId(item.id)
      if (all) await revokeMembershipSessions(item.organization_member_id, reason.trim())
      else await revokeCompanySession(item.id, reason.trim())
    },
    onSuccess: async () => {
      setReason('')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PERSONAL_SESSIONS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: COMPANY_SESSIONS_QUERY_KEY }),
      ])
    },
    onSettled: () => setPendingId(undefined),
  })

  if (personal.isPending) {
    return <SystemState action={<span>請稍候</span>} code="AUTH" eyebrow="資料讀取" title="正在載入登入紀錄" description="正在讀取安全的 Session 摘要。" role="status" />
  }
  if (personal.isError) {
    return <SystemState action={<span>請重新整理後再試</span>} code="ERR" eyebrow="資料異常" title="無法載入登入紀錄" description={getApiErrorMessage(personal.error)} role="alert" />
  }

  const invoke = (item: ManagedSessionResponse, all: boolean) => {
    if (reason.trim().length < 2) return
    mutation.mutate({ item, all })
  }

  return (
    <div className="ui-pattern-stack session-management-page">
      <PageHeader
        eyebrow="帳號安全 / Session"
        title="登入與工作階段"
        description="同一公司帳號只保留一個有效登入；系統只顯示裝置摘要與時間，不顯示 Cookie 或 token。"
      />
      <Section title="我的登入紀錄" description="目前裝置可由右上角登出；已撤銷與到期紀錄只供安全核對。">
        <SessionTable items={personal.data.items} />
      </Section>
      {canManage ? (
        <Section title="公司尚未撤銷登入" description="包含身分已停用但尚未撤銷的紀錄；遠端撤銷會保存操作者、原因與 Request ID。">
          <div className="session-revoke-reason">
            <label htmlFor="session-revoke-reason">撤銷原因</label>
            <input
              id="session-revoke-reason"
              maxLength={500}
              onChange={(event) => setReason(event.target.value)}
              placeholder="例如：員工離職、裝置遺失或異常登入"
              value={reason}
            />
            <span>至少輸入 2 個字，才能執行撤銷。</span>
          </div>
          {mutation.isError ? <p className="session-error" role="alert">{getApiErrorMessage(mutation.error)}</p> : null}
          {company.isPending ? <p role="status">正在載入公司登入…</p> : company.isError ? (
            <p className="session-error" role="alert">{getApiErrorMessage(company.error)}</p>
          ) : (
            <SessionTable
              companyMode
              items={company.data?.items ?? []}
              onRevoke={(item) => invoke(item, false)}
              onRevokeAll={(item) => invoke(item, true)}
              pendingId={pendingId}
            />
          )}
        </Section>
      ) : (
        <Section title="公司登入管理" description="只有取得 sessions.manage 權限的管理者可查看及遠端撤銷其他員工的登入。">
          <p>你可以查看自己的紀錄；如發現異常登入，請聯絡公司系統管理者。</p>
        </Section>
      )}
    </div>
  )
}
