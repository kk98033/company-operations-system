import { useEffect } from 'react'
import { Navigate } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiRequestError } from '../api/errorMessage'
import { AppLayout } from '../app/AppLayout'
import { SystemState } from '../ui/UiPatterns'
import { AuthProvider } from './AuthProvider'
import { CURRENT_SESSION_QUERY_KEY, getCurrentSession } from './session'

const MAX_BROWSER_TIMER_DELAY_MS = 2_147_483_647

export function AuthenticatedBoundary() {
  const queryClient = useQueryClient()
  const sessionQuery = useQuery({
    queryKey: CURRENT_SESSION_QUERY_KEY,
    queryFn: getCurrentSession,
    retry: false,
  })
  const sessionIsExpired = sessionQuery.data
    ? new Date(sessionQuery.data.expires_at).getTime() <= Date.now()
    : false

  useEffect(() => {
    if (!sessionQuery.data) return undefined
    const remaining = new Date(sessionQuery.data.expires_at).getTime() - Date.now()
    if (remaining <= 0) {
      void queryClient.resetQueries({ exact: true, queryKey: CURRENT_SESSION_QUERY_KEY })
      return undefined
    }
    const timeout = window.setTimeout(() => {
      void queryClient.resetQueries({ exact: true, queryKey: CURRENT_SESSION_QUERY_KEY })
    }, Math.min(remaining, MAX_BROWSER_TIMER_DELAY_MS))
    return () => window.clearTimeout(timeout)
  }, [queryClient, sessionQuery.data])

  if (sessionQuery.isPending || sessionIsExpired) {
    return (
      <SystemState
        action={<span>正在確認伺服器 Session</span>}
        code="AUTH"
        description="系統正在確認目前登入狀態，完成後會自動載入工作區。"
        eyebrow="身分驗證"
        fullPage
        role="status"
        title="正在載入登入狀態"
      />
    )
  }

  if (sessionQuery.error instanceof ApiRequestError && sessionQuery.error.status === 401) {
    return <Navigate replace to="/login" />
  }

  if (sessionQuery.isError || !sessionQuery.data) {
    return (
      <SystemState
        action={(
          <button
            className="ui-button ui-button--primary"
            onClick={() => void sessionQuery.refetch()}
            type="button"
          >
            重新連線
          </button>
        )}
        code="AUTH"
        description="目前無法向後端確認登入狀態。請確認服務已啟動後再試一次。"
        eyebrow="連線異常"
        fullPage
        role="alert"
        title="無法確認登入狀態"
      />
    )
  }

  return (
    <AuthProvider session={sessionQuery.data}>
      <AppLayout />
    </AuthProvider>
  )
}
