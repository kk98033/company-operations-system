import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const orderId = '81000000-0000-4000-8000-000000000081'
const session = { ...syntheticCurrentSession, capabilities: ['production.read', 'production.manage', 'production.complete', 'inventory.read', 'inventory.adjust'] }
const pagination = { has_next: false, has_previous: false, page: 1, page_size: 25, total_items: 1, total_pages: 1 }
const order = { work_order_id: orderId, document_number: 'WO-20260813-001', customer_name: '虛構客戶', product_name: '虛構彩盒', order_quantity: '1000.0000', delivery_date: '2026-08-20', process_completed_count: 1, transport_state: 'completed', available_quantity: '600.0000' }
const codes = [['artwork', '美工'], ['output', '輸出'], ['plate', '製版'], ['proof', '打樣'], ['printing', '印刷'], ['coating', '上光'], ['mounting', '裱紙'], ['die', '模具'], ['die_cutting', '軋型'], ['finishing', '加工'], ['gluing', '糊邊'], ['transport', '運送'], ['other', '其他']] as const
const detail = {
  order,
  processes: codes.map(([code, name]) => ({ code, name, state: code === 'transport' ? 'completed' : 'not_started', latest_event: code === 'transport' ? { id: '82000000-0000-4000-8000-000000000082', work_order_id: orderId, process_code: code, process_name: name, event_type: 'complete', sequence_no: 2, completed_quantity: null, reason: null, occurred_at: '2026-08-13T09:00:00Z', created_at: '2026-08-13T09:00:00Z' } : null })),
  final_completions: [], ledger: [],
}

afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'company_system_csrf=; Max-Age=0; Path=/' })

it('製程監管只列已確認工單並顯示運送與可用庫存', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json({ items: [order], meta: { filters: { keyword: null }, pagination, sort: { direction: 'asc', field: 'delivery_date' } } })))
  await renderApp(['/production'], { session })
  expect(await screen.findByRole('heading', { name: '製程監管' })).toBeInTheDocument()
  const row = screen.getByRole('row', { name: /WO-20260813-001/ })
  expect(within(row).getByText('已完成')).toBeInTheDocument()
  expect(within(row).getByText('600.0000')).toBeInTheDocument()
})

it('運送完成後才能核定最終完工並送出 signed CSRF', async () => {
  const user = userEvent.setup(); document.cookie = 'company_system_csrf=phase5-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, options) => {
    if (options?.method === 'POST') return Response.json({ id: '83000000-0000-4000-8000-000000000083', work_order_id: orderId, entry_type: 'completion', source_type: 'manual', quantity: '600.0000', transport_process_event_id: '82000000-0000-4000-8000-000000000082', reversal_of_id: null, correlation_id: '84000000-0000-4000-8000-000000000084', reason: '首批實際完工', occurred_at: '2026-08-13T10:00:00Z', created_at: '2026-08-13T10:00:00Z', available_quantity: '600.0000', exceeds_order_quantity: false }, { status: 201 })
    return Response.json(detail)
  })
  vi.stubGlobal('fetch', fetchMock)
  await renderApp([`/production/work-orders/${orderId}`], { session })
  expect(await screen.findAllByText('運送')).not.toHaveLength(0)
  await user.type(screen.getByLabelText('本次實際完工量'), '600')
  await user.type(screen.getByLabelText('核定原因'), '首批實際完工')
  await user.click(screen.getByRole('button', { name: '核定並入庫' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]?.headers).toEqual(expect.objectContaining({ 'X-CSRF-Token': 'phase5-csrf' }))
  expect(JSON.parse(String(request?.[1]?.body))).toEqual(expect.objectContaining({ quantity: '600', reason: '首批實際完工' }))
})

it('庫存頁預設只顯示正可用量並要求原因才能人工調整', async () => {
  const user = userEvent.setup(); document.cookie = 'company_system_csrf=phase5-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, options) => options?.method === 'POST'
    ? Response.json({ id: '85000000-0000-4000-8000-000000000085', work_order_id: orderId, event_type: 'manual_adjustment', quantity: '-5.0000', reason: '盤點減少', final_completion_entry_id: null, inventory_adjustment_id: '86000000-0000-4000-8000-000000000086', occurred_at: '2026-08-13T11:00:00Z', created_at: '2026-08-13T11:00:00Z' }, { status: 201 })
    : Response.json({ items: [order], meta: { filters: { keyword: null, positive_only: true }, pagination, sort: { direction: 'asc', field: 'document_number' } } }))
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/inventory'], { session })
  expect(await screen.findByRole('heading', { name: '待出貨存貨與流水' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: /只顯示正可用量/ })).toBeChecked()
  await user.click(screen.getByRole('button', { name: '人工調整' }))
  const submit = screen.getByRole('button', { name: '核准並調整' })
  expect(submit).toBeDisabled()
  await user.type(screen.getByLabelText('調整量'), '-5')
  await user.type(screen.getByLabelText('調整原因'), '盤點減少')
  await user.click(submit)
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
})
