import {
  getOperationsExportCsvUrl,
  operationsCustomerOverview,
  operationsDashboard,
  operationsSearch,
  type CustomerOverviewResponse,
  type DashboardResponse,
  type OperationsDashboardParams,
  type SearchResponse,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'

const options = { credentials: 'same-origin' as const }

async function execute<T>(request: () => Promise<{ status: number; data: unknown }>) {
  try {
    const response = await request()
    if (response.status === 200) return response.data as T
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export function getDashboard(params: OperationsDashboardParams = {}) {
  return execute<DashboardResponse>(() => operationsDashboard(params, options))
}

export function searchOperations(keyword: string) {
  return execute<SearchResponse>(() => operationsSearch({ keyword, limit: 50 }, options))
}

export function getCustomerOverview(customerId: string) {
  return execute<CustomerOverviewResponse>(() => operationsCustomerOverview(customerId, options))
}

export type CsvDataset = 'customers' | 'work-orders' | 'shipments' | 'statements'

export async function downloadCsv(dataset: CsvDataset) {
  const response = await fetch(getOperationsExportCsvUrl(dataset), options)
  if (!response.ok) {
    let body: unknown
    try { body = await response.json() } catch { body = undefined }
    throw createApiResponseError(response.status, body)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${dataset}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}
