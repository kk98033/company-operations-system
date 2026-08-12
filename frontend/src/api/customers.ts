import {
  customerCreate,
  customerGet,
  customerList,
  customerStatusUpdate,
  customerUpdate,
  type CustomerCreate,
  type CustomerListResponse,
  type CustomerListParams,
  type CustomerResponse,
  type CustomerStatusUpdate,
  type CustomerUpdate,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const CUSTOMER_LIST_QUERY_KEY = ['customers', 'list'] as const
export const customerQueryKey = (customerId: string) => (
  ['customers', 'detail', customerId] as const
)

async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) {
  try {
    const response = await request()
    if (response.status === ok) return response.data as T
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

const baseOptions = { credentials: 'same-origin' as const }
function writeOptions() {
  const csrfToken = readCookie(CSRF_COOKIE_NAME)
  return {
    ...baseOptions,
    headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined,
  }
}

export function listCustomers(params: CustomerListParams) {
  return execute<CustomerListResponse>(() => customerList(params, baseOptions), 200)
}

export function getCustomer(customerId: string) {
  return execute<CustomerResponse>(() => customerGet(customerId, baseOptions), 200)
}

export function createCustomer(payload: CustomerCreate) {
  return execute<CustomerResponse>(() => customerCreate(payload, writeOptions()), 201)
}

export function updateCustomer(customerId: string, payload: CustomerUpdate) {
  return execute<CustomerResponse>(() => customerUpdate(customerId, payload, writeOptions()), 200)
}

export function updateCustomerStatus(customerId: string, payload: CustomerStatusUpdate) {
  return execute<CustomerResponse>(() => customerStatusUpdate(customerId, payload, writeOptions()), 200)
}
