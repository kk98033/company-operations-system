import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const customerSession = {
  ...syntheticCurrentSession,
  capabilities: ['customers.read', 'customers.manage'],
}
const customer = {
  id: '30000000-0000-4000-8000-000000000003', code: 'C001', name: '虛構客戶甲',
  short_name: '虛構甲', tax_identifier: '12345678', contact_name: '測試聯絡人',
  phone: '02-0000-0000', phone_secondary: null, mobile: null, fax: null,
  email: null, postal_code: '000', city: '測試市', address: '測試地址',
  payment_terms: '月結 30 天（虛構）', legacy_tax_setting_raw: null,
  legacy_rounding_setting_raw: null, legacy_source_table: null, legacy_source_key: null,
  status: 'active', created_at: '2026-08-13T08:00:00Z', updated_at: '2026-08-13T08:00:00Z',
}
const list = {
  items: [customer],
  meta: {
    filters: { keyword: null, status: 'active' },
    pagination: { has_next: false, has_previous: false, page: 1, page_size: 25, total_items: 1, total_pages: 1 },
    sort: { direction: 'asc', field: 'code' },
  },
}
const workItemList = {
  items: [],
  meta: {
    filters: { keyword: null, status: null },
    pagination: { has_next: false, has_previous: false, page: 1, page_size: 100, total_items: 0, total_pages: 0 },
    sort: { direction: 'asc', field: 'name' },
  },
}

afterEach(() => { vi.unstubAllGlobals(); document.cookie = 'company_system_csrf=; Max-Age=0; Path=/' })

it('依代號名稱簡稱查詢並由清單進入編輯頁', async () => {
  const user = userEvent.setup()
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => (
    String(input).includes('/work-items')
      ? Response.json(workItemList)
      : String(input).includes('/api/v1/customers?')
      ? Response.json(list)
      : Response.json(customer)
  ))
  vi.stubGlobal('fetch', fetchMock)
  const { router } = await renderApp(['/customers'], { session: customerSession })

  expect(await screen.findByRole('heading', { level: 1, name: '客戶資料' })).toBeInTheDocument()
  expect(screen.getByRole('row', { name: /C001 虛構客戶甲/ })).toBeInTheDocument()
  await user.type(screen.getByRole('textbox', { name: '關鍵字' }), '虛構甲')
  await user.click(screen.getByRole('button', { name: '查詢' }))
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes('keyword='))).toBe(true)
  await user.click(screen.getByRole('button', { name: '編輯' }))
  expect(router.state.location.pathname).toBe(`/customers/${customer.id}`)
})

it('新增客戶使用共用表單並附帶 signed CSRF', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => (
    String(input).includes('/work-items')
      ? Response.json(workItemList)
      : options?.method === 'POST'
      ? Response.json(customer, { status: 201 })
      : Response.json(customer)
  ))
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/customers/new'], { session: customerSession })

  await user.type(screen.getByRole('textbox', { name: /客戶代號/ }), 'C001')
  await user.type(screen.getByRole('textbox', { name: /客戶名稱/ }), '虛構客戶甲')
  await user.click(screen.getByRole('button', { name: '存檔' }))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]).toEqual(expect.objectContaining({
    credentials: 'same-origin',
    headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }),
  }))
})

it('可編輯及停用客戶，沒有 manage 時只顯示唯讀資料', async () => {
  const readOnlySession = { ...syntheticCurrentSession, capabilities: ['customers.read'] }
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input) => (
    String(input).includes('/work-items') ? Response.json(workItemList) : Response.json(customer)
  )))
  await renderApp([`/customers/${customer.id}`], { session: readOnlySession })
  expect(await screen.findByRole('heading', { level: 1, name: /C001 虛構客戶甲/ })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '停用客戶' })).not.toBeInTheDocument()
  expect(within(screen.getByRole('main')).getByText('測試聯絡人')).toBeInTheDocument()
})

it('有 manage 權限時可停用客戶並帶入目前版本', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const inactiveCustomer = { ...customer, status: 'inactive' }
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => (
    String(input).includes('/work-items')
      ? Response.json(workItemList)
      : options?.method === 'PUT'
      ? Response.json(inactiveCustomer)
      : Response.json(customer)
  ))
  vi.stubGlobal('fetch', fetchMock)
  await renderApp([`/customers/${customer.id}`], { session: customerSession })

  await user.click(await screen.findByRole('button', { name: '停用客戶' }))
  const request = fetchMock.mock.calls.find(([input, options]) => (
    String(input).endsWith(`/customers/${customer.id}/status`) && options?.method === 'PUT'
  ))
  expect(request?.[1]).toEqual(expect.objectContaining({
    body: JSON.stringify({ expected_updated_at: customer.updated_at, status: 'inactive' }),
    headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }),
  }))
  expect(await screen.findByText('已停用')).toBeInTheDocument()
})

it('在客戶頁建立常用工作項目並附帶 signed CSRF', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const createdItem = { id: '40000000-0000-4000-8000-000000000004', customer_id: customer.id, code: 'BOX-A', name: '虛構彩盒', specification: null, unit_price: '12.5000', source: 'manual', source_reference: null, legacy_source_table: null, legacy_source_key: null, status: 'active', created_at: customer.created_at, updated_at: customer.updated_at }
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    if (String(input).includes('/work-items') && options?.method === 'POST') return Response.json(createdItem, { status: 201 })
    if (String(input).includes('/work-items')) return Response.json(workItemList)
    return Response.json(customer)
  })
  vi.stubGlobal('fetch', fetchMock)
  await renderApp([`/customers/${customer.id}`], { session: customerSession })
  await user.click(await screen.findByRole('button', { name: '新增項目' }))
  await user.type(screen.getByRole('textbox', { name: /項目代號/ }), 'BOX-A')
  await user.type(screen.getByRole('textbox', { name: /品名/ }), '虛構彩盒')
  await user.click(screen.getByRole('button', { name: '新增項目' }))
  const request = fetchMock.mock.calls.find(([input, options]) => String(input).includes('/work-items') && options?.method === 'POST')
  expect(request?.[1]).toEqual(expect.objectContaining({ headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }) }))
})
