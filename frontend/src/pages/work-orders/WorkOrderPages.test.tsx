import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import workOrderCss from '../../styles/work-order-prototype.css?raw'
import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'
import { processDefinitions } from './workOrderDraft'

const orderId = '71000000-0000-4000-8000-000000000071'
const caseId = '72000000-0000-4000-8000-000000000072'
const customerId = '73000000-0000-4000-8000-000000000073'
const session = {
  ...syntheticCurrentSession,
  capabilities: [
    'customers.read', 'cases.read', 'cases.manage',
    'work_orders.read', 'work_orders.manage', 'work_orders.confirm',
  ],
}
const pagination = {
  has_next: false, has_previous: false, page: 1, page_size: 25,
  total_items: 1, total_pages: 1,
}
const customerList = {
  items: [{ id: customerId, code: 'C001', name: '虛構客戶甲' }],
  meta: {
    filters: { keyword: null, status: 'active' }, pagination: { ...pagination, page_size: 100 },
    sort: { direction: 'asc', field: 'code' },
  },
}
const processes = processDefinitions.map(([code, name]) => ({ code, name, content: null, vendor: null }))
const order = {
  id: orderId, case_id: caseId, document_number: 'WO-20260813-001',
  status: 'draft', order_date: '2026-08-13', delivery_date: '2026-08-20',
  customer_id: customerId, customer_order_number: 'PO-001', product_name: '虛構彩盒',
  order_quantity: '1000.0000', specification: '100x120mm', unit_price: '20.5000',
  plate_fee: '7000.0000', die_fee: '3500.0000',
  papers: [{ type: 'face' }, { type: 'back' }, { type: 'flute' }],
  print_specification: { front: {}, back: {} }, processes, notes: '虛構工單備註',
  organization_snapshot: { name: '測試印刷股份有限公司（虛構）' },
  customer_snapshot: { code: 'C001', name: '虛構客戶甲' },
  source_quotation_item_id: null, source_work_order_id: null, legacy_document_number: null,
  document_snapshot: null, print_metadata: null, confirmed_at: null, voided_at: null,
  void_reason: null, created_at: '2026-08-13T08:00:00Z', updated_at: '2026-08-13T08:00:00Z',
}
const orderList = {
  items: [{
    id: orderId, case_id: caseId, document_number: order.document_number,
    legacy_document_number: null, order_date: order.order_date, delivery_date: order.delivery_date,
    customer_order_number: 'PO-001', customer_name: '虛構客戶甲', product_name: '虛構彩盒',
    order_quantity: '1000.0000', unit_price: '20.5000', plate_fee: '7000.0000',
    die_fee: '3500.0000', status: 'draft',
  }],
  meta: {
    filters: { keyword: null, status: null }, pagination,
    sort: { direction: 'desc', field: 'order_date' },
  },
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('工單建檔依公司稿在同一頁提供三紙、印刷與固定 13 道製程', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const url = String(input)
    if (url.includes('/customers?')) return Response.json(customerList)
    if (url.endsWith('/attachments')) return Response.json([])
    if (options?.method === 'POST') return Response.json(order, { status: 201 })
    return Response.json(order)
  })
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/work-orders/new'], { session })

  const form = await screen.findByRole('form', { name: '工單整合建檔' })
  expect(screen.getByRole('heading', { level: 1, name: '工單建檔作業' })).toBeInTheDocument()
  for (const groupName of ['面紙', '底紙', '浪紙', '印刷－正面', '印刷－反面']) {
    expect(within(form).getByRole('group', { name: groupName })).toBeInTheDocument()
  }
  expect(Array.from(form.querySelectorAll('.work-order-process-row > legend')).map((item) => item.textContent))
    .toEqual(processDefinitions.map(([, name]) => name))
  expect(within(form).getByLabelText('印刷數量')).toHaveValue(null)
  expect(within(form).getByLabelText('訂單數量')).toHaveAttribute('step', '0.0001')
  expect(within(form).getByRole('radio', { name: '新版' })).not.toBeChecked()
  expect(within(form).getByRole('radio', { name: '舊版' })).not.toBeChecked()
  expect(within(form).getAllByRole('button', { name: '存檔' })).toHaveLength(2)

  await user.selectOptions(within(form).getByRole('combobox', { name: /客戶/ }), customerId)
  await user.type(within(form).getByLabelText(/品名/), '虛構彩盒')
  await user.type(within(form).getByLabelText(/訂單數量/), '1000')
  fireEvent.submit(form)
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]?.headers).toEqual(expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }))
  const body = JSON.parse(String(request?.[1]?.body))
  expect(body.processes).toHaveLength(13)
  expect(body.papers.map((item: { type: string }) => item.type)).toEqual(['face', 'back', 'flute'])
})

it('工單清單顯示價格欄位並可用關鍵字查詢', async () => {
  const user = userEvent.setup()
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json(orderList))
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/work-orders'], { session })

  expect(await screen.findByRole('heading', { level: 1, name: '工單查詢' })).toBeInTheDocument()
  for (const name of ['單價', '版費', '刀模費']) {
    expect(screen.getByRole('columnheader', { name })).toBeInTheDocument()
  }
  expect(screen.getByRole('rowheader', { name: 'WO-20260813-001' })).toBeInTheDocument()
  await user.type(screen.getByRole('searchbox', { name: '關鍵字' }), '彩盒')
  await user.click(screen.getByRole('button', { name: '查詢' }))
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes('keyword=%E5%BD%A9%E7%9B%92')))
    .toBe(true)
})

it('A4 直向工單列印固定公司稿的 9 道製程', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input) => (
    String(input).endsWith('/attachments')
      ? Response.json([{ id: '74000000-0000-4000-8000-000000000074', work_order_id: orderId, filename: '刀模圖.png', mime_type: 'image/png', size_bytes: 100, sha256: 'a'.repeat(64), created_at: order.created_at }])
      : Response.json(order)
  )))
  await renderApp([`/work-orders/${orderId}/print`], { session })

  expect(await screen.findByText('工 作 單')).toBeInTheDocument()
  const sheet = document.querySelector('.work-order-print-sheet') as HTMLElement
  for (const name of ['製版', '打樣', '印刷', '上光', '裱紙', '軋型', '加工', '糊邊', '其他']) {
    expect(within(sheet).getAllByText(name).length).toBeGreaterThan(0)
  }
  expect(within(sheet).queryByText('美工')).not.toBeInTheDocument()
  expect(within(sheet).queryByText('運送')).not.toBeInTheDocument()
  expect(within(sheet).getByRole('img', { name: '刀模圖.png' })).toHaveAttribute(
    'src', `/api/v1/work-orders/${orderId}/attachments/74000000-0000-4000-8000-000000000074`,
  )
  expect(workOrderCss).toContain('@page { size: A4 portrait;')
})
