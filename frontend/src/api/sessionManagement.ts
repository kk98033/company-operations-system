import {
  authListCompanySessions,
  authListPersonalSessions,
  authRevokeCompanySession,
  authRevokeMembershipSessions,
  type ManagedSessionListResponse,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const PERSONAL_SESSIONS_QUERY_KEY = ['auth', 'sessions', 'personal'] as const
export const COMPANY_SESSIONS_QUERY_KEY = ['auth', 'sessions', 'company'] as const

async function unwrap(
  request: () => Promise<{ status: number; data: unknown }>,
): Promise<ManagedSessionListResponse> {
  try {
    const response = await request()
    if (response.status === 200) return response.data as ManagedSessionListResponse
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export function getPersonalSessions(): Promise<ManagedSessionListResponse> {
  return unwrap(() => authListPersonalSessions(
    { limit: 50 },
    { credentials: 'same-origin' },
  ))
}

export function getCompanySessions(): Promise<ManagedSessionListResponse> {
  return unwrap(() => authListCompanySessions(
    { limit: 100 },
    { credentials: 'same-origin' },
  ))
}

function mutationOptions(): RequestInit {
  const csrf = readCookie(CSRF_COOKIE_NAME)
  return {
    credentials: 'same-origin',
    headers: csrf ? { 'X-CSRF-Token': csrf } : undefined,
  }
}

export async function revokeCompanySession(sessionId: string, reason: string): Promise<void> {
  try {
    const response = await authRevokeCompanySession(
      sessionId,
      { reason },
      mutationOptions(),
    )
    if (response.status === 204) return
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function revokeMembershipSessions(
  organizationMemberId: string,
  reason: string,
): Promise<void> {
  try {
    const response = await authRevokeMembershipSessions(
      { organization_member_id: organizationMemberId, reason },
      mutationOptions(),
    )
    if (response.status === 204) return
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
