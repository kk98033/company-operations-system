import { CSRF_COOKIE_NAME, readCookie } from '../auth/session'
import { createApiResponseError, createApiTransportError } from './errorMessage'
import type { DocumentExportResponse } from './generated/company-system'

export type PdfDocumentType = 'quotation' | 'work_order' | 'shipment' | 'statement'

async function createPdfExport(documentType: PdfDocumentType, documentId: string) {
  const csrf = readCookie(CSRF_COOKIE_NAME)
  try {
    const response = await fetch(`/api/v1/document-exports/${documentType}/${documentId}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: csrf ? { 'X-CSRF-Token': csrf } : {},
    })
    const data = await response.json()
    if (response.status !== 201) throw createApiResponseError(response.status, data)
    return data as DocumentExportResponse
  } catch (error) {
    throw createApiTransportError(error)
  }
}

export async function downloadDocumentPdf(documentType: PdfDocumentType, documentId: string) {
  const metadata = await createPdfExport(documentType, documentId)
  try {
    const response = await fetch(metadata.download_url, { credentials: 'same-origin' })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw createApiResponseError(response.status, data)
    }
    const blobUrl = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = metadata.filename
    anchor.click()
    URL.revokeObjectURL(blobUrl)
    return metadata
  } catch (error) {
    throw createApiTransportError(error)
  }
}
