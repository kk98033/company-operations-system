import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import quotationCss from '../../styles/quotations.css?raw'
import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const quotationId = '50000000-0000-4000-8000-000000000005'
const customerId = '30000000-0000-4000-8000-000000000003'
const quotationSession = {
  ...syntheticCurrentSession,
  capabilities: ['quotations.read', 'quotations.manage', 'quotations.confirm'],
}
const customerList = {
  items: [{ id: customerId, code: 'C001', name: '虛構客戶甲' }],
  meta: {
    filters: { keyword: null, status: 'active' },
    pagination: {
      has_next: false, has_previous: false, page: 1, page_size: 100,
      total_items: 1, total_pages: 1,
    },
    sort: { direction: 'asc', field: 'code' },
  },
}
const quote = {
  id: quotationId,
  document_number: 'QUO-20260813-01',
  quotation_date: '2026-08-13',
  customer_id: customerId,
  organization_snapshot: {
    name: '測試印刷股份有限公司（虛構）', address: '測試地址',
    phone: '02-0000', fax: '02-0001', email: 'test.invalid@example.invalid',
  },
  customer_snapshot: {
    code: 'C001', name: '虛構客戶甲', contact_name: '測試聯絡人',
    phone: '02-1111', fax: '02-2222', address: '客戶測試地址',
  },
  notes: '整張報價備註',
  status: 'draft',
  source_quotation_id: null,
  legacy_document_number: null,
  legacy_tax_included_raw: null,
  legacy_source_table: null,
  legacy_source_key: null,
  document_snapshot: null,
  print_metadata: null,
  confirmed_at: null,
  voided_at: null,
  void_reason: null,
  created_at: '2026-08-13T08:00:00Z',
  updated_at: '2026-08-13T08:00:00Z',
  items: [{
    id: '60000000-0000-4000-8000-000000000006', line_number: 1,
    product_name: '虛構彩盒', size: '100x100mm', paper: '350g', color: '4/4',
    coating: '亮膜', quantity: '1000.0000', plate_fee: '7000.0000',
    die_fee: '3500.0000', unit_price: '20.0000', note: '明細附註',
  }],
}
const quotationList = {
  items: [{
    id: quotationId, document_number: quote.document_number,
    legacy_document_number: null, quotation_date: quote.quotation_date,
    customer_name: '虛構客戶甲', first_product_name: '虛構彩盒',
    item_count: 1, status: 'draft', updated_at: quote.updated_at,
  }],
  meta: {
    filters: { keyword: null, status: null, date_from: null, date_to: null },
    pagination: {
      has_next: false, has_previous: false, page: 1, page_size: 25,
      total_items: 1, total_pages: 1,
    },
    sort: { direction: 'desc', field: 'quotation_date' },
  },
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('報價清單可查詢並進入同頁編輯', async () => {
  const user = userEvent.setup()
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    if (String(input).includes('/customers?')) return Response.json(customerList)
    if (String(input).endsWith(`/quotations/${quotationId}`)) return Response.json(quote)
    return Response.json(quotationList)
  })
  vi.stubGlobal('fetch', fetchMock)
  const { router } = await renderApp(['/quotations'], { session: quotationSession })

  expect(await screen.findByRole('heading', { level: 1, name: '報價單查詢' }))
    .toBeInTheDocument()
  expect(screen.getByRole('row', { name: /QUO-20260813-01.*虛構客戶甲.*虛構彩盒/ }))
    .toBeInTheDocument()
  await user.type(screen.getByRole('searchbox', { name: '關鍵字' }), 'C001')
  await user.click(screen.getByRole('button', { name: '查詢' }))
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes('keyword=C001'))).toBe(true)
  await user.click(screen.getByRole('button', { name: '編輯' }))
  expect(router.state.location.pathname).toBe(`/quotations/${quotationId}`)
})

it('報價同頁建檔提供四個公司稿動作、動態明細與 CSRF 存檔', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    if (String(input).includes('/customers?')) return Response.json(customerList)
    if (options?.method === 'POST') return Response.json(quote, { status: 201 })
    return Response.json(quote)
  })
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/quotations/new'], { session: quotationSession })

  expect(await screen.findByRole('heading', { level: 1, name: '新增報價單' }))
    .toBeInTheDocument()
  const pageActions = document.querySelector('.ui-page-actions') as HTMLElement
  expect(within(pageActions).getAllByRole('button').map((button) => button.textContent))
    .toEqual(['另存新檔', '存檔', '取消', '列印'])
  expect(within(pageActions).getByRole('button', { name: '另存新檔' })).toBeDisabled()
  expect(within(pageActions).getByRole('button', { name: '列印' })).toBeDisabled()
  const footer = document.querySelector('.quotation-action-bar') as HTMLElement
  await user.click(within(footer).getByRole('button', { name: '存檔' }))
  const validation = await screen.findByRole('alert')
  expect(validation).toHaveTextContent('客戶：此欄位為必填')
  expect(validation).toHaveTextContent('第 1 筆品名：此欄位為必填')
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false)
  await user.selectOptions(screen.getByRole('combobox', { name: /客戶/ }), customerId)
  await user.type(screen.getByRole('textbox', { name: '第 1 筆品名' }), '虛構彩盒')
  await user.click(screen.getByRole('button', { name: '新增明細' }))
  expect(screen.getByRole('textbox', { name: '第 2 筆品名' })).toBeInTheDocument()
  const secondRow = screen.getByRole('textbox', { name: '第 2 筆品名' }).closest('tr')
  await user.click(within(secondRow as HTMLElement).getByRole('button', { name: '刪除' }))
  expect(screen.queryByRole('textbox', { name: '第 2 筆品名' })).not.toBeInTheDocument()
  await user.click(within(footer).getByRole('button', { name: '存檔' }))
  const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(request?.[1]).toEqual(expect.objectContaining({
    headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }),
  }))
  expect(JSON.parse(String(request?.[1]?.body))).toEqual(expect.objectContaining({
    customer_id: customerId,
    items: [expect.objectContaining({ product_name: '虛構彩盒' })],
  }))
})

it('草稿可確認與作廢，作廢必須保存原因', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const confirmed = {
    ...quote, status: 'confirmed', confirmed_at: '2026-08-13T09:00:00Z',
    updated_at: '2026-08-13T09:00:00Z', document_snapshot: { ...quote },
    print_metadata: { paper_size: 'A4', orientation: 'landscape' },
  }
  const voided = {
    ...confirmed, status: 'void', voided_at: '2026-08-13T10:00:00Z',
    void_reason: '客戶取消（虛構）', updated_at: '2026-08-13T10:00:00Z',
  }
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    if (String(input).includes('/customers?')) return Response.json(customerList)
    if (String(input).endsWith('/confirm') && options?.method === 'POST') {
      return Response.json(confirmed)
    }
    if (String(input).endsWith('/void') && options?.method === 'POST') {
      return Response.json(voided)
    }
    return Response.json(quote)
  })
  vi.stubGlobal('fetch', fetchMock)
  await renderApp([`/quotations/${quotationId}`], { session: quotationSession })

  await user.click(await screen.findByRole('button', { name: '確認報價' }))
  expect(await screen.findByText('已確認')).toBeInTheDocument()
  await user.type(screen.getByRole('textbox', { name: /作廢原因/ }), '客戶取消（虛構）')
  await user.click(screen.getByRole('button', { name: '作廢報價' }))
  expect(await screen.findByText('已作廢')).toBeInTheDocument()
  expect(screen.getByText('作廢原因：客戶取消（虛構）')).toBeInTheDocument()
  const request = fetchMock.mock.calls.find(([input]) => String(input).endsWith('/void'))
  expect(JSON.parse(String(request?.[1]?.body))).toEqual({
    expected_updated_at: confirmed.updated_at,
    reason: '客戶取消（虛構）',
  })
})

it('A4 橫向列印頁含完整快照欄位且列印時隱藏操作', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json(quote)))
  await renderApp([`/quotations/${quotationId}/print`], { session: quotationSession })

  expect(await screen.findByText('報 價 單')).toBeInTheDocument()
  expect(screen.getByText(/客戶：C001 虛構客戶甲/)).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: '版費' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: '刀模費' })).toBeInTheDocument()
  expect(screen.getByText('整張報價備註')).toBeInTheDocument()
  expect(quotationCss).toContain('@page { size: A4 landscape;')
  expect(quotationCss).toContain('.quotation-print-actions { display: none !important; }')
})
