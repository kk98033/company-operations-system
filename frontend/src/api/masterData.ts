import {
  paperMillCreate,
  paperMillList,
  paperMillStatusUpdate,
  paperTypeCreate,
  paperTypeList,
  paperTypeStatusUpdate,
  processDefinitionList,
  processDefinitionStatusUpdate,
  vendorCreate,
  vendorList,
  vendorStatusUpdate,
  type CatalogCreate,
  type CatalogListResponse,
  type CatalogResponse,
  type MasterStatusUpdate,
  type ProcessDefinitionResponse,
  type VendorCreate,
  type VendorListResponse,
  type VendorResponse,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'

export const MASTER_DATA_QUERY_KEY = ['master-data'] as const
export type CatalogKind = 'paper-types' | 'paper-mills'

const baseOptions = { credentials: 'same-origin' as const }
function writeOptions() {
  const csrfToken = readCookie(CSRF_COOKIE_NAME)
  return { ...baseOptions, headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined }
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

export function listVendors() {
  return execute<VendorListResponse>(() => vendorList({ page_size: 100 }, baseOptions), 200)
}

export function createVendor(payload: VendorCreate) {
  return execute<VendorResponse>(() => vendorCreate(payload, writeOptions()), 201)
}

export function setVendorStatus(vendor: VendorResponse) {
  const payload: MasterStatusUpdate = {
    expected_updated_at: vendor.updated_at,
    status: vendor.status === 'active' ? 'inactive' : 'active',
  }
  return execute<VendorResponse>(() => vendorStatusUpdate(vendor.id, payload, writeOptions()), 200)
}

export function listCatalog(kind: CatalogKind) {
  const request = kind === 'paper-types' ? paperTypeList : paperMillList
  return execute<CatalogListResponse>(() => request({ page_size: 100 }, baseOptions), 200)
}

export function createCatalog(kind: CatalogKind, payload: CatalogCreate) {
  const request = kind === 'paper-types' ? paperTypeCreate : paperMillCreate
  return execute<CatalogResponse>(() => request(payload, writeOptions()), 201)
}

export function setCatalogStatus(kind: CatalogKind, item: CatalogResponse) {
  const request = kind === 'paper-types' ? paperTypeStatusUpdate : paperMillStatusUpdate
  const payload: MasterStatusUpdate = {
    expected_updated_at: item.updated_at,
    status: item.status === 'active' ? 'inactive' : 'active',
  }
  return execute<CatalogResponse>(() => request(item.id, payload, writeOptions()), 200)
}

export function listProcesses() {
  return execute<ProcessDefinitionResponse[]>(() => processDefinitionList(undefined, baseOptions), 200)
}

export function setProcessStatus(item: ProcessDefinitionResponse) {
  const payload: MasterStatusUpdate = {
    expected_updated_at: item.updated_at,
    status: item.status === 'active' ? 'inactive' : 'active',
  }
  return execute<ProcessDefinitionResponse>(
    () => processDefinitionStatusUpdate(item.id, payload, writeOptions()),
    200,
  )
}
