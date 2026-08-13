import {
  caseFromQuotation, caseGet, caseList, caseCreate, caseUpdate, caseVoid,
  workOrderAttachmentDelete, workOrderAttachmentList, workOrderAttachmentUpload,
  workOrderClone, workOrderConfirm, workOrderCreate, workOrderGet, workOrderList,
  workOrderUpdate, workOrderVoid,
  type AttachmentResponse, type CaseCreate, type CaseListParams,
  type CaseListResponse, type CaseResponse, type CaseUpdate,
  type QuotationConversionRequest, type VoidRequest, type WorkOrderCreate,
  type WorkOrderListParams, type WorkOrderListResponse, type WorkOrderResponse,
  type WorkOrderUpdate,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const CASE_LIST_QUERY_KEY = ['cases', 'list'] as const
export const WORK_ORDER_LIST_QUERY_KEY = ['work-orders', 'list'] as const
export const caseQueryKey = (id: string) => ['cases', 'detail', id] as const
export const workOrderQueryKey = (id: string) => ['work-orders', 'detail', id] as const
export const attachmentQueryKey = (id: string) => ['work-orders', id, 'attachments'] as const

const readOptions = { credentials: 'same-origin' as const }
function writeOptions(extra?: RequestInit): RequestInit {
  const csrf = readCookie(CSRF_COOKIE_NAME)
  return {
    ...readOptions,
    ...extra,
    headers: { ...(extra?.headers ?? {}), ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
  }
}
async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) {
  try {
    const response = await request()
    if (response.status === ok) return response.data as T
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export const listCases = (params: CaseListParams = {}) => execute<CaseListResponse>(() => caseList(params, readOptions), 200)
export const getCase = (id: string) => execute<CaseResponse>(() => caseGet(id, readOptions), 200)
export const createCase = (payload: CaseCreate) => execute<CaseResponse>(() => caseCreate(payload, writeOptions()), 201)
export const updateCase = (id: string, payload: CaseUpdate) => execute<CaseResponse>(() => caseUpdate(id, payload, writeOptions()), 200)
export const voidCase = (id: string, payload: VoidRequest) => execute<CaseResponse>(() => caseVoid(id, payload, writeOptions()), 200)
export const convertQuotation = (payload: QuotationConversionRequest) => execute<CaseResponse>(() => caseFromQuotation(payload, writeOptions()), 201)

export const listWorkOrders = (params: WorkOrderListParams = {}) => execute<WorkOrderListResponse>(() => workOrderList(params, readOptions), 200)
export const getWorkOrder = (id: string) => execute<WorkOrderResponse>(() => workOrderGet(id, readOptions), 200)
export const createWorkOrder = (payload: WorkOrderCreate) => execute<WorkOrderResponse>(() => workOrderCreate(payload, writeOptions()), 201)
export const updateWorkOrder = (id: string, payload: WorkOrderUpdate) => execute<WorkOrderResponse>(() => workOrderUpdate(id, payload, writeOptions()), 200)
export const confirmWorkOrder = (id: string, expected: string) => execute<WorkOrderResponse>(() => workOrderConfirm(id, { expected_updated_at: expected }, writeOptions()), 200)
export const cloneWorkOrder = (id: string, orderDate: string) => execute<WorkOrderResponse>(() => workOrderClone(id, { order_date: orderDate }, writeOptions()), 201)
export const voidWorkOrder = (id: string, payload: VoidRequest) => execute<WorkOrderResponse>(() => workOrderVoid(id, payload, writeOptions()), 200)

export const listAttachments = (id: string) => execute<AttachmentResponse[]>(() => workOrderAttachmentList(id, readOptions), 200)
export const uploadAttachment = (id: string, file: File) => execute<AttachmentResponse>(
  () => workOrderAttachmentUpload(id, { filename: file.name }, writeOptions({ body: file, headers: { 'Content-Type': file.type } })),
  201,
)
export const deleteAttachment = (workOrderId: string, attachmentId: string) => execute<void>(() => workOrderAttachmentDelete(workOrderId, attachmentId, writeOptions()), 204)
