import {
  priceSuggestionList, pricingCancel, pricingConfirm, pricingCreate, pricingGet,
  pricingList, pricingPendingItemList, pricingReopen, pricingUpdate,
  type PendingPricingListResponse, type PriceSuggestionListResponse,
  type PricingCancel, type PricingConfirm, type PricingDraftCreate,
  type PricingDraftUpdate, type PricingListParams, type PricingListResponse,
  type PricingPendingItemListParams, type PricingReopen, type PricingResponse,
} from './generated/company-system'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'
import { createApiResponseError, createApiTransportError } from './errorMessage'

export const PRICING_LIST_QUERY_KEY = ['pricing', 'list'] as const
export const PRICING_PENDING_QUERY_KEY = ['pricing', 'pending'] as const
export const pricingQueryKey = (id: string) => ['pricing', 'detail', id] as const
const readOptions = { credentials: 'same-origin' as const }

function writeOptions(): RequestInit {
  const csrf = readCookie(CSRF_COOKIE_NAME)
  return { ...readOptions, headers: csrf ? { 'X-CSRF-Token': csrf } : {} }
}

async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) {
  try {
    const response = await request()
    if (response.status === ok) return response.data as T
    throw createApiResponseError(response.status, response.data)
  } catch (error) { throw createApiTransportError(error) }
}

export const listPricing = (params: PricingListParams = {}) => execute<PricingListResponse>(() => pricingList(params, readOptions), 200)
export const listPendingPricing = (params: PricingPendingItemListParams = {}) => execute<PendingPricingListResponse>(() => pricingPendingItemList(params, readOptions), 200)
export const getPricing = (id: string) => execute<PricingResponse>(() => pricingGet(id, readOptions), 200)
export const createPricing = (payload: PricingDraftCreate) => execute<PricingResponse>(() => pricingCreate(payload, writeOptions()), 201)
export const updatePricing = (id: string, payload: PricingDraftUpdate) => execute<PricingResponse>(() => pricingUpdate(id, payload, writeOptions()), 200)
export const confirmPricing = (id: string, payload: PricingConfirm) => execute<PricingResponse>(() => pricingConfirm(id, payload, writeOptions()), 200)
export const cancelPricing = (id: string, payload: PricingCancel) => execute<PricingResponse>(() => pricingCancel(id, payload, writeOptions()), 200)
export const reopenPricing = (id: string, payload: PricingReopen) => execute<PricingResponse>(() => pricingReopen(id, payload, writeOptions()), 200)
export const listPriceSuggestions = (customerId: string, productName: string, specification?: string | null) => execute<PriceSuggestionListResponse>(() => priceSuggestionList({ customer_id: customerId, product_name: productName, specification: specification ?? undefined }, readOptions), 200)
