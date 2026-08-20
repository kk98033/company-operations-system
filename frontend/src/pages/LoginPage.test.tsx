import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderApp } from '../test/renderApp'
import { syntheticCurrentSession } from '../test/sessionFixture'

const organizationId = syntheticCurrentSession.organization.id

function apiError(status: number, code: string, message: string) {
  return Response.json({ error: { code, details: null, message } }, { status })
}

function currentSessionResponse() {
  return Response.json(syntheticCurrentSession, { status: 200 })
}

beforeEach(() => {
  vi.stubEnv('VITE_ORGANIZATION_ID', organizationId)
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('登入與 Cookie Session 流程', () => {
  it('未登入使用者進入受保護頁時會轉到登入頁', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async () => (
      apiError(401, 'SESSION_INVALID', '請重新登入')
    )))

    const { router } = await renderApp(['/cases'], { session: null })

    expect(await screen.findByRole(
      'heading',
      { level: 1, name: '公司管理系統' },
      { timeout: 5_000 },
    ))
      .toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })

  it('重新整理時由 HttpOnly Cookie 恢復伺服器 Session', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/session')) return currentSessionResponse()
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    await renderApp(['/cases'], { session: null })

    expect(await screen.findByRole('heading', { level: 1, name: '沒有案件權限' }))
      .toBeInTheDocument()
    expect(screen.getByText('測試操作員')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('Session 在前端判定到期後重新向伺服器確認並回登入頁', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async () => (
      apiError(401, 'SESSION_INVALID', '請重新登入')
    )))

    const { router } = await renderApp(['/cases'], {
      session: { ...syntheticCurrentSession, expires_at: '2000-01-01T00:00:00Z' },
    })

    expect(await screen.findByRole('heading', { level: 1, name: '公司管理系統' }))
      .toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })

  it('送出公司部署識別碼、使用者代號與密碼後進入工作區', async () => {
    const requests: Array<{ body: unknown; url: string }> = []
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/session')) {
        return apiError(401, 'SESSION_INVALID', '請重新登入')
      }
      if (url.endsWith('/api/v1/auth/login')) {
        requests.push({ body: JSON.parse(String(init?.body)), url })
        return currentSessionResponse()
      }
      if (url.endsWith('/api/v1/health/ready')) {
        return Response.json({ checks: [], status: 'ready' })
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()

    await renderApp(['/login'], { session: null })
    await user.type(await screen.findByRole('textbox', { name: /^使用者代號/ }), 'test.operator')
    await user.type(screen.getByLabelText(/^密碼/), 'runtime-only-password')
    await user.click(screen.getByRole('button', { name: '登入' }))

    expect(await screen.findByRole('heading', { level: 1, name: '首頁' }))
      .toBeInTheDocument()
    expect(requests).toEqual([{
      body: {
        login_name: 'test.operator',
        organization_id: organizationId,
        password: 'runtime-only-password',
      },
      url: '/api/v1/auth/login',
    }])
  })

  it('帳密失敗時只顯示後端的通用錯誤，不進入工作區', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/session')) {
        return apiError(401, 'SESSION_INVALID', '請重新登入')
      }
      if (url.endsWith('/api/v1/auth/login')) {
        return apiError(401, 'AUTHENTICATION_FAILED', '登入資料不正確或帳號目前無法使用')
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()

    await renderApp(['/login'], { session: null })
    await user.type(await screen.findByRole('textbox', { name: /^使用者代號/ }), 'test.operator')
    await user.type(screen.getByLabelText(/^密碼/), 'wrong-password')
    await user.click(screen.getByRole('button', { name: '登入' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '登入資料不正確或帳號目前無法使用',
    )
    expect(screen.queryByRole('heading', { level: 1, name: '首頁' }))
      .not.toBeInTheDocument()
  })

  it('登入被暫時限制時顯示安全訊息且不進入工作區', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/session')) {
        return apiError(401, 'SESSION_INVALID', '請重新登入')
      }
      if (url.endsWith('/api/v1/auth/login')) {
        return apiError(429, 'LOGIN_RATE_LIMITED', '登入嘗試過於頻繁，請稍後再試')
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()

    await renderApp(['/login'], { session: null })
    await user.type(await screen.findByRole('textbox', { name: /^使用者代號/ }), 'test.operator')
    await user.type(screen.getByLabelText(/^密碼/), 'wrong-password')
    await user.click(screen.getByRole('button', { name: '登入' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '登入嘗試過於頻繁，請稍後再試',
    )
    expect(screen.queryByRole('heading', { level: 1, name: '首頁' }))
      .not.toBeInTheDocument()
  })

  it('登出後清除前端 Session cache 並回到登入頁', async () => {
    document.cookie = 'company_system_csrf=signed-csrf-token; Path=/'
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/logout')) {
        expect(init?.headers).toEqual({ 'X-CSRF-Token': 'signed-csrf-token' })
        return new Response(null, { status: 204 })
      }
      if (url.endsWith('/api/v1/auth/session')) {
        return apiError(401, 'SESSION_INVALID', '請重新登入')
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    const { queryClient, router } = await renderApp(['/cases'])
    await user.click(screen.getByRole('button', { name: '登出' }))

    expect(await screen.findByRole('heading', { level: 1, name: '公司管理系統' }))
      .toBeInTheDocument()
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(queryClient.getQueryData(['auth', 'current-session'])).toBeUndefined()
  })
})
