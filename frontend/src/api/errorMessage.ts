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

type ValidationDetail = { loc: Array<string | number>; msg: string }

const FIELD_LABELS: Record<string, string> = {
  customer_id: '客戶', order_date: '訂購日期', delivery_date: '交貨日期',
  product_name: '品名', order_quantity: '訂單數量', unit_price: '單價',
  plate_fee: '版費', die_fee: '刀模費', papers: '備紙',
  print_specification: '印刷規格', processes: '製程規劃', notes: '備註',
  quotation_date: '報價日期', items: '明細', quantity: '數量',
  name: '名稱', code: '代號', statement_date: '對帳日期',
  receipt_date: '收款日期', shipment_date: '出貨日期',
}

function validationDetails(error: unknown): ValidationDetail[] {
  if (!(error instanceof ApiRequestError) || error.code !== 'VALIDATION_ERROR') return []
  if (!Array.isArray(error.details)) return []
  return error.details.filter((item): item is ValidationDetail => {
    if (typeof item !== 'object' || item === null) return false
    const value = item as { loc?: unknown; msg?: unknown }
    return Array.isArray(value.loc) && typeof value.msg === 'string'
  })
}

function validationLabel(location: Array<string | number>) {
  const parts = location.filter((part) => part !== 'body')
  const index = parts.find((part) => typeof part === 'number')
  const field = [...parts].reverse().find((part) => typeof part === 'string')
  const label = field ? (FIELD_LABELS[field] ?? field) : '表單內容'
  return typeof index === 'number' ? `第 ${index + 1} 筆${label}` : label
}

export function getApiValidationIssues(error: unknown) {
  return validationDetails(error).map((detail) => ({
    label: validationLabel(detail.loc),
    message: detail.msg,
  }))
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
  const issues = getApiValidationIssues(error)
  if (issues.length) {
    const summary = issues.slice(0, 4).map((item) => `${item.label}：${item.message}`).join('；')
    return issues.length > 4 ? `${summary}；另有 ${issues.length - 4} 項` : summary
  }
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
