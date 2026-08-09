import { FormEvent } from 'react'
import { Navigate, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiRequestError, getApiErrorMessage } from '../api/errorMessage'
import { CURRENT_SESSION_QUERY_KEY, getCurrentSession, loginSession } from '../auth/session'
import { Field, SystemState } from '../ui/UiPatterns'

export function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const organizationId = import.meta.env.VITE_ORGANIZATION_ID?.trim() ?? ''
  const sessionQuery = useQuery({
    queryKey: CURRENT_SESSION_QUERY_KEY,
    queryFn: getCurrentSession,
    retry: false,
  })
  const loginMutation = useMutation({
    mutationFn: loginSession,
    onSuccess: async (session) => {
      queryClient.setQueryData(CURRENT_SESSION_QUERY_KEY, session)
      await navigate({ to: '/', replace: true })
    },
  })

  if (sessionQuery.data) return <Navigate replace to="/" />
  if (sessionQuery.isPending) {
    return (
      <SystemState
        action={<span>正在確認 Cookie Session</span>}
        code="AUTH"
        description="重新整理後仍會先向伺服器確認登入狀態，不使用瀏覽器儲存的假登入資料。"
        eyebrow="身分驗證"
        fullPage
        role="status"
        title="正在確認登入狀態"
      />
    )
  }
  if (sessionQuery.error instanceof ApiRequestError && sessionQuery.error.status !== 401) {
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
        description="目前無法連線至登入服務。請確認後端與資料庫都已啟動。"
        eyebrow="連線異常"
        fullPage
        role="alert"
        title="登入服務無法使用"
      />
    )
  }
  if (!organizationId) {
    return (
      <SystemState
        action={<span>請在部署環境設定 VITE_ORGANIZATION_ID</span>}
        code="CFG"
        description="公司識別碼是公開部署設定，不是密碼；員工不需要在每次登入時手動輸入。"
        eyebrow="部署設定"
        fullPage
        role="alert"
        title="尚未指定登入公司"
      />
    )
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    loginMutation.mutate({
      organization_id: organizationId,
      login_name: String(form.get('login_name') ?? ''),
      password: String(form.get('password') ?? ''),
    })
  }

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <header className="login-panel__header">
          <span className="login-panel__mark" aria-hidden="true">UV</span>
          <div>
            <p className="eyebrow">OPERATIONS ERP</p>
            <h1 id="login-title">公司管理系統</h1>
            <p>請使用公司配發的使用者代號與密碼登入。</p>
          </div>
        </header>

        <form className="login-form" onSubmit={submit}>
          <Field label="使用者代號" required>
            <input
              autoComplete="username"
              autoFocus
              maxLength={128}
              name="login_name"
              required
            />
          </Field>
          <Field label="密碼" required>
            <input
              autoComplete="current-password"
              maxLength={256}
              name="password"
              required
              type="password"
            />
          </Field>

          {loginMutation.isError ? (
            <p className="login-form__error" role="alert">
              {getApiErrorMessage(loginMutation.error)}
            </p>
          ) : null}

          <button
            className="ui-button ui-button--primary login-form__submit"
            disabled={loginMutation.isPending}
            type="submit"
          >
            {loginMutation.isPending ? '登入中…' : '登入'}
          </button>
        </form>

        <footer className="login-panel__footer">
          <span>公司範圍已由此部署指定</span>
          <span>Session 最長 8 小時</span>
        </footer>
      </section>
    </main>
  )
}
