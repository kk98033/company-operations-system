import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  authCurrentSession,
  authLogin,
  authLogout,
} from '../api/generated/company-system'
import { syntheticCurrentSession } from '../test/sessionFixture'
import {
  CSRF_COOKIE_NAME,
  getCurrentSession,
  loginSession,
  logoutSession,
} from './session'

vi.mock('../api/generated/company-system', () => ({
  authCurrentSession: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn(),
}))

const currentSessionMock = vi.mocked(authCurrentSession)
const loginMock = vi.mocked(authLogin)
const logoutMock = vi.mocked(authLogout)

beforeEach(() => {
  vi.clearAllMocks()
  document.cookie = `${CSRF_COOKIE_NAME}=; Max-Age=0; Path=/`
})

describe('瀏覽器 Session API adapter', () => {
  it('使用 same-origin Cookie 載入與建立 Session', async () => {
    currentSessionMock.mockResolvedValue({
      data: syntheticCurrentSession,
      headers: new Headers(),
      status: 200,
    })
    loginMock.mockResolvedValue({
      data: syntheticCurrentSession,
      headers: new Headers(),
      status: 200,
    })
    const payload = {
      login_name: 'test.operator',
      organization_id: syntheticCurrentSession.organization.id,
      password: 'runtime-only-password',
    }

    await expect(getCurrentSession()).resolves.toEqual(syntheticCurrentSession)
    await expect(loginSession(payload)).resolves.toEqual(syntheticCurrentSession)
    expect(currentSessionMock).toHaveBeenCalledWith({ credentials: 'same-origin' })
    expect(loginMock).toHaveBeenCalledWith(payload, { credentials: 'same-origin' })
  })

  it('登出只從 CSRF Cookie 建立同源 header，不讀取 localStorage', async () => {
    document.cookie = `${CSRF_COOKIE_NAME}=signed-csrf-token; Path=/`
    logoutMock.mockResolvedValue({
      data: undefined,
      headers: new Headers(),
      status: 204,
    })

    await expect(logoutSession()).resolves.toBeUndefined()
    expect(logoutMock).toHaveBeenCalledWith({
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': 'signed-csrf-token' },
    })
  })
})
