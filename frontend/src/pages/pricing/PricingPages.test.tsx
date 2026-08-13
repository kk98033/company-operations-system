import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const pricingId = 'a1000000-0000-4000-8000-0000000000a1'
const sourceId = 'a2000000-0000-4000-8000-0000000000a2'
const customerId = 'a3000000-0000-4000-8000-0000000000a3'
const session = { ...syntheticCurrentSession, capabilities: ['pricing.read', 'pricing.create', 'pricing.confirm', 'pricing.cancel', 'price_default.update'] }
const pagination = { has_next: false, has_previous: false, page: 1, page_size: 100, total_items: 1, total_pages: 1 }
const listMeta = { filters: { keyword: null, status: null }, pagination, sort: { direction: 'desc', field: 'pricing_date' } }
const pendingItem = { shipment_item_id: sourceId, shipment_id: 'a4000000-0000-4000-8000-0000000000a4', shipment_document_number: 'SHP-202608-001', shipment_date: '2026-08-13', customer_id: customerId, customer_name: '虛構客戶', work_order_document_number: 'WO-20260813-001', product_name: '虛構彩盒', specification: '100x120', delivered_quantity: '500.0000', spare_quantity: '10.0000', suggested_unit_price: '20.5000', pricing_status: 'pending', pricing_document_id: null, pricing_document_number: null }
const detail = { id: pricingId, document_number: 'PRC-20260813-001', pricing_date: '2026-08-13', customer_id: customerId, customer_name: '虛構客戶', notes: null, status: 'draft', version: 1, legacy_document_number: null, total_amount: '10250.0000', confirmed_at: null, cancelled_at: null, cancel_reason: null, created_at: '2026-08-13T01:00:00Z', updated_at: '2026-08-13T01:00:00Z', items: [{ id: 'a5000000-0000-4000-8000-0000000000a5', source_shipment_item_id: sourceId, line_no: 1, item_type: 'base', content: '虛構彩盒', product_name: '虛構彩盒', specification: '100x120', quantity: '500.0000', unit_price: '20.5000', plate_fee: '0.0000', die_fee: '0.0000', subtotal: '10250.0000', source_snapshot: { spare_quantity: '10.0000' } }] }

afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'company_system_csrf=; Max-Age=0; Path=/' })

it('待計價頁以文字狀態顯示正式量與免費備品，並可建立草稿', async () => {
  const user = userEvent.setup(); document.cookie = 'company_system_csrf=phase7-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const url = String(input)
    if (options?.method === 'POST') return Response.json(detail, { status: 201 })
    if (url.includes('/pending-items')) return Response.json({ items: [pendingItem], meta: listMeta })
    if (url.includes(`/pricing-documents/${pricingId}`)) return Response.json(detail)
    return Response.json({ items: [], meta: listMeta })
  })
  vi.stubGlobal('fetch', fetchMock); await renderApp(['/pricing'], { session })
  const row = await screen.findByRole('row', { name: /SHP-202608-001/ })
  expect(within(row).getByText('待計價')).toBeInTheDocument()
  expect(within(row).getByText('500.0000')).toBeInTheDocument()
  expect(within(row).getByText('10.0000')).toBeInTheDocument()
  await user.click(within(row).getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: '建立計價草稿（1）' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]?.headers).toEqual(expect.objectContaining({ 'X-CSRF-Token': 'phase7-csrf' }))
  expect(JSON.parse(String(request?.[1]?.body)).shipment_item_ids).toEqual([sourceId])
})

it('草稿預設只有正式出貨，備品收費與額外版費必須明確新增', async () => {
  const user = userEvent.setup(); document.cookie = 'company_system_csrf=phase7-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, options) => options?.method === 'PUT' ? Response.json({ ...detail, version: 2 }) : Response.json(detail))
  vi.stubGlobal('fetch', fetchMock); await renderApp([`/pricing/${pricingId}`], { session })
  expect(await screen.findByText('正式出貨')).toBeInTheDocument()
  expect(screen.queryByText('明確備品收費')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '新增備品收費' }))
  expect(screen.getByText('明確備品收費')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '新增額外明細' }))
  expect(screen.getByText('額外手動明細')).toBeInTheDocument()
  await user.type(screen.getByLabelText('第 3 筆內容'), '追加版費')
  await user.clear(screen.getByLabelText('第 3 筆版費')); await user.type(screen.getByLabelText('第 3 筆版費'), '7000')
  await user.click(screen.getByRole('button', { name: '存檔' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(true))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
  const body = JSON.parse(String(request?.[1]?.body))
  expect(body.items.map((item: { item_type: string }) => item.item_type)).toEqual(['base', 'spare', 'manual'])
  expect(body.items[2].plate_fee).toBe('7000')
})

it('價格建議只套用本次，更新預設必須另行勾選', async () => {
  const user = userEvent.setup()
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => String(input).includes('/price-suggestions') ? Response.json({ items: [{ id: 'a6000000-0000-4000-8000-0000000000a6', content: '歷史彩盒', product_name: '虛構彩盒', specification: '100x120', unit_price: '22.0000', plate_fee: '100.0000', die_fee: '50.0000', price_date: '2026-08-01', source_pricing_item_id: 'a7000000-0000-4000-8000-0000000000a7', is_default: true }] }) : Response.json(detail))
  vi.stubGlobal('fetch', fetchMock); await renderApp([`/pricing/${pricingId}`], { session })
  await user.click(await screen.findByRole('button', { name: '歷史價格' }))
  const suggestion = await screen.findByRole('row', { name: /歷史彩盒/ })
  expect(within(suggestion).getByText('是')).toBeInTheDocument()
  expect(screen.getByText(/只供本次套用/)).toBeInTheDocument()
  await user.click(within(suggestion).getByRole('button', { name: '套用本次' }))
  expect(screen.getByLabelText('第 1 筆單價')).toHaveValue(22)
  expect(screen.getByRole('checkbox', { name: /確認時更新預設/ })).not.toBeChecked()
})
