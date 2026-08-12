import { customerWorkItemCreate, customerWorkItemList, customerWorkItemStatusUpdate, type WorkItemCreate, type WorkItemListResponse, type WorkItemResponse } from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const workItemQueryKey = (customerId: string) => ['customers', customerId, 'work-items'] as const
const baseOptions = { credentials: 'same-origin' as const }
function writeOptions() { const token = readCookie(CSRF_COOKIE_NAME); return { ...baseOptions, headers: token ? { 'X-CSRF-Token': token } : undefined } }
async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) { try { const response = await request(); if (response.status === ok) return response.data as T; throw createApiResponseError(response.status, response.data) } catch (error) { throw createApiTransportError(error) } }
export function listCustomerWorkItems(customerId: string) { return execute<WorkItemListResponse>(() => customerWorkItemList(customerId, { page_size: 100 }, baseOptions), 200) }
export function createCustomerWorkItem(customerId: string, payload: WorkItemCreate) { return execute<WorkItemResponse>(() => customerWorkItemCreate(customerId, payload, writeOptions()), 201) }
export function toggleCustomerWorkItem(customerId: string, item: WorkItemResponse) { return execute<WorkItemResponse>(() => customerWorkItemStatusUpdate(customerId, item.id, { expected_updated_at: item.updated_at, status: item.status === 'active' ? 'inactive' : 'active' }, writeOptions()), 200) }
