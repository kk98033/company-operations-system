import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const shipmentId = '91000000-0000-4000-8000-000000000091'
const customerId = '92000000-0000-4000-8000-000000000092'
const orderId = '93000000-0000-4000-8000-000000000093'
const session = { ...syntheticCurrentSession, capabilities: ['shipment.read', 'shipment.create', 'shipment.confirm', 'shipment.cancel', 'shipment.complete_and_confirm'] }
const pagination = { has_next: false, has_previous: false, page: 1, page_size: 25, total_items: 1, total_pages: 1 }
const meta = { filters: { keyword: null, status: null }, pagination, sort: { direction: 'desc', field: 'shipment_date' } }
const detail = { id: shipmentId, document_number: 'SHP-202608-001', shipment_date: '2026-08-13', customer_id: customerId, customer_name: '虛構客戶', delivery_address: '虛構地址', notes: '虛構備註', status: 'draft', version: 1, legacy_document_number: null, confirmed_at: null, cancelled_at: null, cancel_reason: null, created_at: '2026-08-13T01:00:00Z', updated_at: '2026-08-13T01:00:00Z', warnings: [], items: [{ id: '94000000-0000-4000-8000-000000000094', work_order_id: orderId, line_no: 1, work_order_document_number: 'WO-20260813-001', customer_order_number: 'PO-001', product_name: '虛構彩盒', specification: '100x120', delivered_quantity: '500.0000', spare_quantity: '10.0000', inventory_consumed_quantity: '510.0000', available_quantity_snapshot: null, cumulative_delivered_snapshot: null }] }

afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'company_system_csrf=; Max-Age=0; Path=/' })

it('出貨清單顯示正式量、備品量與狀態', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json({ items: [{ id: shipmentId, document_number: 'SHP-202608-001', legacy_document_number: null, shipment_date: '2026-08-13', customer_name: '虛構客戶', status: 'confirmed', line_count: 1, delivered_quantity: '500.0000', spare_quantity: '10.0000', created_at: '2026-08-13T01:00:00Z' }], meta })))
  await renderApp(['/shipments'], { session })
  const row = await screen.findByRole('row', { name: /SHP-202608-001/ })
  expect(within(row).getByText('500.0000')).toBeInTheDocument()
  expect(within(row).getByText('10.0000')).toBeInTheDocument()
  expect(within(row).getByText('已確認')).toBeInTheDocument()
})

it('新增頁先選客戶再選可出貨工單並建立草稿', async () => {
  const user = userEvent.setup(); document.cookie = 'company_system_csrf=phase6-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const url = String(input)
    if (options?.method === 'POST') return Response.json(detail, { status: 201 })
    if (url.includes(shipmentId)) return Response.json(detail)
    if (url.includes('/available-items')) return Response.json({ items: [{ work_order_id: orderId, document_number: 'WO-20260813-001', customer_id: customerId, customer_name: '虛構客戶', customer_order_number: 'PO-001', product_name: '虛構彩盒', specification: '100x120', order_quantity: '1000.0000', available_quantity: '600.0000' }], meta })
    return Response.json({ items: [{ id: customerId, code: 'C001', name: '虛構客戶', address: '虛構地址' }], meta: { ...meta, filters: { keyword: null, status: 'active' } } })
  })
  vi.stubGlobal('fetch', fetchMock); await renderApp(['/shipments/new'], { session })
  await user.selectOptions(await screen.findByLabelText('客戶'), customerId)
  await user.click(await screen.findByRole('checkbox', { name: /選取 WO-20260813-001/ }))
  await user.type(screen.getByLabelText('WO-20260813-001 正式量'), '500')
  await user.clear(screen.getByLabelText('WO-20260813-001 備品量'))
  await user.type(screen.getByLabelText('WO-20260813-001 備品量'), '10')
  await user.click(screen.getByRole('button', { name: '存檔草稿' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]?.headers).toEqual(expect.objectContaining({ 'X-CSRF-Token': 'phase6-csrf' }))
  expect(JSON.parse(String(request?.[1]?.body)).items[0]).toEqual(expect.objectContaining({ delivered_quantity: '500', spare_quantity: '10' }))
})

it('草稿明細清楚標示補登完工不等於負庫存 override', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json(detail)))
  await renderApp([`/shipments/${shipmentId}`], { session })
  expect(await screen.findByRole('heading', { name: '庫存不足時補登真實完工（選用）' })).toBeInTheDocument()
  expect(screen.getByText(/取消出貨不會取消真實完工/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '確認出貨並扣庫' })).toBeInTheDocument()
})
