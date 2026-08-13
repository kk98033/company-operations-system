import { useMutation } from '@tanstack/react-query'
import { downloadDocumentPdf, type PdfDocumentType } from '../../api/documentExports'
import { getApiErrorMessage } from '../../api/errorMessage'

export function DocumentPdfButton({ documentId, documentType }: { documentId: string; documentType: PdfDocumentType }) {
  const mutation = useMutation({ mutationFn: () => downloadDocumentPdf(documentType, documentId) })
  return <div className="document-pdf-action"><button className="ui-button ui-button--primary" disabled={mutation.isPending} onClick={() => mutation.mutate()} type="button">{mutation.isPending ? '產生 PDF…' : '下載 PDF'}</button>{mutation.isSuccess ? <span className="document-pdf-action__status" role="status">PDF 已保存（SHA-256 {mutation.data.sha256.slice(0, 12)}…）</span> : null}{mutation.isError ? <span className="ui-inline-error" role="alert">{getApiErrorMessage(mutation.error)}</span> : null}</div>
}
