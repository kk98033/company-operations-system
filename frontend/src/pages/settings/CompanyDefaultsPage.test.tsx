import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const settingsSession = {
  ...syntheticCurrentSession,
  capabilities: ['settings.manage'],
}

const settings = {
  document_number_policy_version: 'adr-018-v1',
  document_numbering: [
    { document_type: 'quotation', format: 'QUO-YYYYMMDD-SS', label: '報價', reset_period: 'daily' },
    { document_type: 'case', format: 'CASE-YYYYMMDD-SSS', label: '案件', reset_period: 'daily' },
    { document_type: 'work_order', format: 'WO-YYYYMMDD-SSS', label: '工單', reset_period: 'daily' },
    { document_type: 'shipment', format: 'SHP-YYYYMM-SSS', label: '出貨', reset_period: 'monthly' },
    { document_type: 'pricing', format: 'PRC-YYYYMMDD-SSS', label: '計價', reset_period: 'daily' },
    { document_type: 'statement', format: 'STM-YYYYMM-SSS', label: '對帳', reset_period: 'monthly' },
    { document_type: 'receipt', format: 'RCT-YYYYMMDD-SSS', label: '收款', reset_period: 'daily' },
  ],
  organization_id: syntheticCurrentSession.organization.id,
  printing: [
    { document_type: 'quotation', label: '報價單', note: '公司稿', orientation: 'landscape', paper_size: 'A4', status: 'confirmed' },
    { document_type: 'work_order', label: '工單', note: '公司稿', orientation: 'portrait', paper_size: 'A4', status: 'confirmed' },
    { document_type: 'statement', label: '對帳單', note: '待樣張', orientation: null, paper_size: 'A4', status: 'pending_uat' },
  ],
  quotation_print_layout_version: 'gmail-a4-landscape-v1',
  statement_tax: {
    calculation_status: 'pending_phase_8_uat',
    enabled: false,
    rounding_decimal_places: null,
    rounding_scope: null,
    tax_rate_percent: null,
  },
  updated_at: '2026-08-13T08:00:00Z',
  work_order_print_layout_version: 'gmail-a4-portrait-9-process-v1',
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('集中呈現固定單號與列印契約，並可保存對帳計稅草稿', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, init) => {
    if (init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      return Response.json({
        ...settings,
        statement_tax: {
          calculation_status: 'pending_phase_8_uat',
          enabled: body.statement_tax_default_enabled,
          rounding_decimal_places: body.statement_rounding_decimal_places,
          rounding_scope: body.statement_rounding_scope,
          tax_rate_percent: body.statement_tax_rate_percent,
        },
        updated_at: '2026-08-13T09:00:00Z',
      })
    }
    return Response.json(settings)
  })
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/defaults'], { session: settingsSession })

  expect(await screen.findByRole('heading', { level: 1, name: '文件與帳務預設' }))
    .toBeInTheDocument()
  expect(screen.getByText('QUO-YYYYMMDD-SS')).toBeInTheDocument()
  expect(screen.getByRole('row', { name: /報價單 A4 橫向/ })).toBeInTheDocument()
  expect(screen.getByRole('row', { name: /對帳單 A4 待公司樣張確認/ }))
    .toBeInTheDocument()
  const navigation = screen.getByRole('navigation', { name: '主要導覽' })
  expect(within(navigation).getByRole('link', { name: '文件與帳務預設' }))
    .toHaveAttribute('aria-current', 'page')

  await user.click(screen.getByRole('checkbox', { name: /新對帳單預設啟用計稅/ }))
  await user.type(screen.getByRole('spinbutton', { name: /預設稅率/ }), '5')
  await user.selectOptions(screen.getByRole('combobox', { name: /取整範圍/ }), 'per_line')
  await user.selectOptions(screen.getByRole('combobox', { name: /保留小數位/ }), '0')
  await user.click(screen.getByRole('button', { name: '存檔' }))

  expect(await screen.findByText('公司預設設定已存檔，並已寫入操作稽核。'))
    .toBeInTheDocument()
  const updateCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
  expect(updateCall?.[1]).toEqual(expect.objectContaining({
    credentials: 'same-origin',
    headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }),
  }))
  expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual({
    expected_updated_at: settings.updated_at,
    statement_rounding_decimal_places: 0,
    statement_rounding_scope: 'per_line',
    statement_tax_default_enabled: true,
    statement_tax_rate_percent: '5',
  })
})

it('關閉計稅時不送出殘留稅率與取整欄位', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const enabledSettings = {
    ...settings,
    statement_tax: {
      ...settings.statement_tax,
      enabled: true,
      rounding_decimal_places: 0,
      rounding_scope: 'per_line',
      tax_rate_percent: '5.0000',
    },
  }
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, init) => (
    init?.method === 'PUT' ? Response.json(settings) : Response.json(enabledSettings)
  ))
  vi.stubGlobal('fetch', fetchMock)
  await renderApp(['/settings/defaults'], { session: settingsSession })

  const checkbox = await screen.findByRole('checkbox', { name: /新對帳單預設啟用計稅/ })
  await user.click(checkbox)
  await user.click(screen.getByRole('button', { name: '存檔' }))

  const updateCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
  expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual(expect.objectContaining({
    statement_rounding_decimal_places: null,
    statement_rounding_scope: null,
    statement_tax_default_enabled: false,
    statement_tax_rate_percent: null,
  }))
})

it('沒有 settings.manage 時不顯示導覽、不呼叫 API 並顯示權限限制', async () => {
  const fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/defaults'])

  expect(await screen.findByRole('heading', { name: '沒有公司預設設定權限' }))
    .toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '文件與帳務預設' })).not.toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
})
