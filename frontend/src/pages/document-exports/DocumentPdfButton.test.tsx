import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { DocumentPdfButton } from './DocumentPdfButton'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('先建立不可變 PDF 紀錄，再以授權網址下載指定檔名', async () => {
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(Response.json({
      id: 'e-1', document_type: 'quotation', document_id: 'q-1',
      document_number: 'QUO-20260813-01', document_version: 'v1',
      template_version: 'quotation-gmail-a4-landscape-v1', filename: 'QUO-20260813-01.pdf',
      content_type: 'application/pdf', byte_size: 8, sha256: 'a'.repeat(64),
      download_url: '/api/v1/document-exports/e-1/content', created_at: '2026-08-13T00:00:00Z',
    }, { status: 201 }))
    .mockResolvedValueOnce(new Response(new Blob(['%PDF-1.7']), { status: 200, headers: { 'Content-Type': 'application/pdf' } }))
  vi.stubGlobal('fetch', fetchMock)
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:synthetic') })
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><DocumentPdfButton documentId="q-1" documentType="quotation" /></QueryClientProvider>)
  await userEvent.click(screen.getByRole('button', { name: '下載 PDF' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  expect(fetchMock.mock.calls[0]).toEqual(expect.arrayContaining(['/api/v1/document-exports/quotation/q-1']))
  expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: 'POST', headers: { 'X-CSRF-Token': 'synthetic-csrf' } }))
  expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/document-exports/e-1/content')
  expect(click).toHaveBeenCalledOnce()
  expect(await screen.findByRole('status')).toHaveTextContent('PDF 已保存')
})
