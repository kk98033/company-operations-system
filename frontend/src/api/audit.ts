import {
  auditList,
  type AuditListParams,
  type ListResponseAuditLogResponseAuditFilterSummary,
} from './generated/company-system'
import { createApiResponseError, createApiTransportError } from './errorMessage'

export const AUDIT_LOGS_QUERY_KEY = ['audit-logs'] as const

export async function getAuditLogs(
  params: AuditListParams,
): Promise<ListResponseAuditLogResponseAuditFilterSummary> {
  try {
    const response = await auditList(params, { credentials: 'same-origin' })
    if (response.status === 200) return response.data
    throw createApiResponseError(response.status, response.data)
  } catch (error) {
    throw createApiTransportError(error)
  }
}
