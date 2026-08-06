import type { ErrorResponse } from './generated/company-system'

export type ApiErrorResponse = ErrorResponse

const DEFAULT_API_ERROR_MESSAGE = '系統暫時無法完成操作，請稍後再試。'
const NETWORK_ERROR_MESSAGE = '無法連線至系統服務，請確認網路後再試。'

export class ApiRequestError extends Error {
  readonly code: string
  readonly details: unknown
  readonly status: number | null

  constructor(options: {
    cause?: unknown
    code: string
    details?: unknown
    message: string
    status?: number | null
  }) {
    super(options.message, { cause: options.cause })
    this.name = 'ApiRequestError'
    this.code = options.code
    this.details = options.details ?? null
    this.status = options.status ?? null
  }
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false

  const error = value.error
  return typeof error === 'object'
    && error !== null
    && 'message' in error
    && typeof error.message === 'string'
    && error.message.trim().length > 0
}

export function getApiErrorMessage(error: unknown): string {
  if (isApiErrorResponse(error)) return error.error.message.trim()
  if (error instanceof ApiRequestError) return error.message
  if (error instanceof TypeError) return NETWORK_ERROR_MESSAGE
  return DEFAULT_API_ERROR_MESSAGE
}

export function createApiResponseError(status: number, response: unknown): ApiRequestError {
  if (isApiErrorResponse(response)) {
    return new ApiRequestError({
      code: response.error.code,
      details: response.error.details,
      message: response.error.message.trim(),
      status,
    })
  }

  return new ApiRequestError({
    code: 'UNEXPECTED_RESPONSE',
    message: DEFAULT_API_ERROR_MESSAGE,
    status,
  })
}

export function createApiTransportError(error: unknown): ApiRequestError {
  if (error instanceof ApiRequestError) return error
  if (error instanceof TypeError) {
    return new ApiRequestError({
      cause: error,
      code: 'NETWORK_ERROR',
      message: NETWORK_ERROR_MESSAGE,
    })
  }

  return new ApiRequestError({
    cause: error,
    code: 'UNEXPECTED_RESPONSE',
    message: DEFAULT_API_ERROR_MESSAGE,
  })
}
