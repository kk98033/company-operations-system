import { healthReady, type ReadyResponse } from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'

export async function getApiReadiness(): Promise<ReadyResponse> {
  try {
    const response = await healthReady({ credentials: 'same-origin' })
    if (response.status === 200) return response.data

    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
