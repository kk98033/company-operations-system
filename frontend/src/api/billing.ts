import {
  receiptCreate, receiptGet, receiptList, receiptReverse, receivableAgingList,
  statementCancel, statementCreate, statementGet, statementIssue, statementList, statementPendingItemList,
  type AgingSummary, type PendingStatementListResponse, type ReceiptCreate, type ReceiptListResponse,
  type ReceiptResponse, type ReceiptReverse, type StatementCancel, type StatementCommand,
  type StatementCreate, type StatementListResponse, type StatementResponse,
} from './generated/company-system'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'
import { createApiResponseError, createApiTransportError } from './errorMessage'

const read = { credentials: 'same-origin' as const }
const write = (): RequestInit => { const csrf = readCookie(CSRF_COOKIE_NAME); return { ...read, headers: csrf ? { 'X-CSRF-Token': csrf } : {} } }
async function execute<T>(request: () => Promise<{ status: number; data: unknown }>, ok: number) { try { const response = await request(); if (response.status === ok) return response.data as T; throw createApiResponseError(response.status, response.data) } catch (error) { throw createApiTransportError(error) } }

export const BILLING_QUERY_KEY = ['billing'] as const
export const statementQueryKey = (id: string) => ['billing', 'statement', id] as const
export const listStatements = (params: { keyword?: string; status?: string } = {}) => execute<StatementListResponse>(() => statementList(params, read), 200)
export const listPendingStatements = (keyword?: string) => execute<PendingStatementListResponse>(() => statementPendingItemList({ keyword }, read), 200)
export const getStatement = (id: string) => execute<StatementResponse>(() => statementGet(id, read), 200)
export const createStatement = (payload: StatementCreate) => execute<StatementResponse>(() => statementCreate(payload, write()), 201)
export const issueStatement = (id: string, payload: StatementCommand) => execute<StatementResponse>(() => statementIssue(id, payload, write()), 200)
export const cancelStatement = (id: string, payload: StatementCancel) => execute<StatementResponse>(() => statementCancel(id, payload, write()), 200)
export const listReceipts = (keyword?: string) => execute<ReceiptListResponse>(() => receiptList({ keyword }, read), 200)
export const getReceipt = (id: string) => execute<ReceiptResponse>(() => receiptGet(id, read), 200)
export const createReceipt = (payload: ReceiptCreate) => execute<ReceiptResponse>(() => receiptCreate(payload, write()), 201)
export const reverseReceipt = (id: string, payload: ReceiptReverse) => execute<ReceiptResponse>(() => receiptReverse(id, payload, write()), 200)
export const listAging = (asOf: string) => execute<AgingSummary[]>(() => receivableAgingList({ as_of: asOf }, read), 200)
