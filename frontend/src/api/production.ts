import {
  inventoryAdjustmentCreate, inventoryLedgerGet, inventoryList,
  productionFinalCompletionCreate, productionFinalCompletionReverse, productionGet,
  productionList, productionProcessEventCreate,
  type FinalCompletionCreate, type FinalCompletionResponse,
  type InventoryAdjustmentCreate, type InventoryLedgerResponse,
  type InventoryListParams, type InventoryListResponse,
  type ProcessEventCreate, type ProcessEventResponse,
  type ProductionListParams, type ProductionOrderDetail,
  type ProductionOrderListResponse, type ReversalCreate,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const PRODUCTION_LIST_QUERY_KEY = ['production', 'list'] as const
export const INVENTORY_LIST_QUERY_KEY = ['inventory', 'list'] as const
export const productionQueryKey = (id: string) => ['production', 'detail', id] as const
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

export const listProduction = (params: ProductionListParams = {}) => execute<ProductionOrderListResponse>(() => productionList(params, readOptions), 200)
export const getProduction = (id: string) => execute<ProductionOrderDetail>(() => productionGet(id, readOptions), 200)
export const createProcessEvent = (id: string, payload: ProcessEventCreate) => execute<ProcessEventResponse>(() => productionProcessEventCreate(id, payload, writeOptions()), 201)
export const createFinalCompletion = (id: string, payload: FinalCompletionCreate) => execute<FinalCompletionResponse>(() => productionFinalCompletionCreate(id, payload, writeOptions()), 201)
export const reverseFinalCompletion = (id: string, payload: ReversalCreate) => execute<FinalCompletionResponse>(() => productionFinalCompletionReverse(id, payload, writeOptions()), 201)
export const listInventory = (params: InventoryListParams = {}) => execute<InventoryListResponse>(() => inventoryList(params, readOptions), 200)
export const getInventoryLedger = (id: string) => execute<ProductionOrderDetail>(() => inventoryLedgerGet(id, readOptions), 200)
export const createInventoryAdjustment = (id: string, payload: InventoryAdjustmentCreate) => execute<InventoryLedgerResponse>(() => inventoryAdjustmentCreate(id, payload, writeOptions()), 201)
