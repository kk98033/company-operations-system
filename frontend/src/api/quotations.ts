import { quotationClone, quotationConfirm, quotationCreate, quotationGet, quotationList, quotationUpdate, quotationVoid, type QuotationCreate, type QuotationListParams, type QuotationListResponse, type QuotationResponse, type QuotationUpdate } from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'
export const QUOTATION_LIST_QUERY_KEY = ['quotations', 'list'] as const
export const quotationQueryKey = (id: string) => ['quotations', 'detail', id] as const
const baseOptions = { credentials: 'same-origin' as const }
function writeOptions() { const token = readCookie(CSRF_COOKIE_NAME); return { ...baseOptions, headers: token ? { 'X-CSRF-Token': token } : undefined } }
async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) { try { const response = await request(); if (response.status === ok) return response.data as T; throw createApiResponseError(response.status, response.data) } catch (error) { throw createApiTransportError(error) } }
export function listQuotations(params: QuotationListParams) { return execute<QuotationListResponse>(() => quotationList(params, baseOptions), 200) }
export function getQuotation(id: string) { return execute<QuotationResponse>(() => quotationGet(id, baseOptions), 200) }
export function createQuotation(payload: QuotationCreate) { return execute<QuotationResponse>(() => quotationCreate(payload, writeOptions()), 201) }
export function updateQuotation(id: string, payload: QuotationUpdate) { return execute<QuotationResponse>(() => quotationUpdate(id, payload, writeOptions()), 200) }
export function confirmQuotation(id: string, expectedUpdatedAt: string) { return execute<QuotationResponse>(() => quotationConfirm(id, { expected_updated_at: expectedUpdatedAt }, writeOptions()), 200) }
export function cloneQuotation(id: string, quotationDate: string) { return execute<QuotationResponse>(() => quotationClone(id, { quotation_date: quotationDate }, writeOptions()), 201) }
export function voidQuotation(id: string, expectedUpdatedAt: string, reason: string) { return execute<QuotationResponse>(() => quotationVoid(id, { expected_updated_at: expectedUpdatedAt, reason }, writeOptions()), 200) }
