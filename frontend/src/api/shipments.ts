import {
  shipmentAvailableItemList, shipmentCancel, shipmentConfirm, shipmentCreate,
  shipmentGet, shipmentList, shipmentUpdate,
  type AvailableShipmentListResponse, type ShipmentCancel, type ShipmentConfirm,
  type ShipmentDraftCreate, type ShipmentDraftUpdate, type ShipmentListParams,
  type ShipmentListResponse, type ShipmentResponse,
} from './generated/company-system'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'
import { createApiResponseError, createApiTransportError } from './errorMessage'

export const SHIPMENT_LIST_QUERY_KEY = ['shipments', 'list'] as const
export const shipmentQueryKey = (id: string) => ['shipments', 'detail', id] as const
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

export const listShipments = (params: ShipmentListParams = {}) => execute<ShipmentListResponse>(() => shipmentList(params, readOptions), 200)
export const listAvailableShipmentItems = (customerId: string, keyword?: string) => execute<AvailableShipmentListResponse>(() => shipmentAvailableItemList({ customer_id: customerId, keyword, page_size: 100 }, readOptions), 200)
export const getShipment = (id: string) => execute<ShipmentResponse>(() => shipmentGet(id, readOptions), 200)
export const createShipment = (payload: ShipmentDraftCreate) => execute<ShipmentResponse>(() => shipmentCreate(payload, writeOptions()), 201)
export const updateShipment = (id: string, payload: ShipmentDraftUpdate) => execute<ShipmentResponse>(() => shipmentUpdate(id, payload, writeOptions()), 200)
export const confirmShipment = (id: string, payload: ShipmentConfirm) => execute<ShipmentResponse>(() => shipmentConfirm(id, payload, writeOptions()), 200)
export const cancelShipment = (id: string, payload: ShipmentCancel) => execute<ShipmentResponse>(() => shipmentCancel(id, payload, writeOptions()), 200)
