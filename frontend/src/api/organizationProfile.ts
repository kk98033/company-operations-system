import {
  organizationProfileGet,
  organizationProfileUpdate,
  type OrganizationProfileResponse,
  type OrganizationProfileUpdate,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const ORGANIZATION_PROFILE_QUERY_KEY = ['organization-profile'] as const

export async function getOrganizationProfile(): Promise<OrganizationProfileResponse> {
  try {
    const response = await organizationProfileGet({ credentials: 'same-origin' })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function updateOrganizationProfile(
  payload: OrganizationProfileUpdate,
): Promise<OrganizationProfileResponse> {
  const csrfToken = readCookie(CSRF_COOKIE_NAME)
  try {
    const response = await organizationProfileUpdate(payload, {
      credentials: 'same-origin',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined,
    })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
