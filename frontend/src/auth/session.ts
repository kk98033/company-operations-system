import {
  authCurrentSession,
  authLogin,
  authLogout,
  type CurrentSessionResponse,
  type LoginRequest,
} from '../api/generated/company-system'
import { createApiResponseError, createApiTransportError } from '../api/errorMessage'

export const CURRENT_SESSION_QUERY_KEY = ['auth', 'current-session'] as const
export const CSRF_COOKIE_NAME = 'company_system_csrf'

function readCookie(name: string): string | null {
  const prefix = `${name}=`
  for (const segment of document.cookie.split(';')) {
    const value = segment.trim()
    if (value.startsWith(prefix)) return value.slice(prefix.length)
  }
  return null
}

export async function getCurrentSession(): Promise<CurrentSessionResponse> {
  try {
    const response = await authCurrentSession({ credentials: 'same-origin' })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function loginSession(payload: LoginRequest): Promise<CurrentSessionResponse> {
  try {
    const response = await authLogin(payload, { credentials: 'same-origin' })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function logoutSession(): Promise<void> {
  const csrfToken = readCookie(CSRF_COOKIE_NAME)
  try {
    const response = await authLogout({
      credentials: 'same-origin',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined,
    })
    if (response.status === 204) return
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
