import {
  organizationSettingsGet,
  organizationSettingsUpdate,
  type OrganizationSettingsResponse,
  type OrganizationSettingsUpdate,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const ORGANIZATION_SETTINGS_QUERY_KEY = ['organization-settings'] as const

export async function getOrganizationSettings(): Promise<OrganizationSettingsResponse> {
  try {
    const response = await organizationSettingsGet({ credentials: 'same-origin' })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function updateOrganizationSettings(
  payload: OrganizationSettingsUpdate,
): Promise<OrganizationSettingsResponse> {
  const csrfToken = readCookie(CSRF_COOKIE_NAME)
  try {
    const response = await organizationSettingsUpdate(payload, {
      credentials: 'same-origin',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined,
    })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
