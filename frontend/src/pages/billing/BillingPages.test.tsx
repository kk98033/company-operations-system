import { screen } from '@testing-library/react'
import { vi } from 'vitest'
import { syntheticCurrentSession } from '../../test/sessionFixture'
import { renderApp } from '../../test/renderApp'

const session = { ...syntheticCurrentSession, capabilities: ['statement.read', 'statement.issue', 'statement.cancel', 'receipt.read', 'receipt.record', 'receipt.reverse'] }
vi.mock('../../api/organizationSettings', () => ({ ORGANIZATION_SETTINGS_QUERY_KEY: ['organization-settings'], getOrganizationSettings: vi.fn().mockResolvedValue({ statement_tax: { enabled: false, tax_rate_percent: null, rounding_scope: null, rounding_decimal_places: null } }) }))
vi.mock('../../api/organizationProfile', () => ({ getOrganizationProfile: vi.fn().mockResolvedValue({ name: '虛構印刷公司' }) }))
vi.mock('../../api/billing', async (original) => {
  const actual = await original<typeof import('../../api/billing')>()
  return { ...actual,
    listPendingStatements: vi.fn().mockResolvedValue({ items: [{ pricing_item_id: 'pi-1', pricing_document_id: 'p-1', pricing_document_number: 'PRC-20260813-001', pricing_date: '2026-08-13', customer_id: 'c-1', customer_name: '虛構客戶', content: '彩盒', amount: '1000.0000' }], total_items: 1 }),
    listStatements: vi.fn().mockResolvedValue({ items: [{ id: 's-1', document_number: 'STM-202608-001', statement_date: '2026-08-13', customer_id: 'c-1', customer_name: '虛構客戶', grand_total: '1000.0000', paid_amount: '0.0000', outstanding_amount: '1000.0000', status: 'issued' }], total_items: 1 }),
    listReceipts: vi.fn().mockResolvedValue({ items: [], total_items: 0 }),
    listAging: vi.fn().mockResolvedValue([{ customer_id: 'c-1', customer_name: '虛構客戶', current_amount: '0', days_1_30: '1000', days_31_60: '0', days_61_90: '0', days_over_90: '0', total_outstanding: '1000' }]),
    getStatement: vi.fn().mockResolvedValue({ id: 's-1', document_number: 'STM-202608-001', statement_date: '2026-08-13', period_from: '2026-08-01', period_to: '2026-08-31', customer_id: 'c-1', customer_name: '虛構客戶', status: 'issued', version: 2, tax_enabled: false, tax_rate_percent: null, rounding_scope: null, rounding_decimal_places: null, subtotal_before_rounding: '1000.0000', rounding_adjustment: '0.0000', subtotal: '1000.0000', tax_amount: '0.0000', grand_total: '1000.0000', paid_amount: '0.0000', outstanding_amount: '1000.0000', notes: null, issued_at: '2026-08-13T00:00:00Z', cancelled_at: null, cancel_reason: null, created_at: '2026-08-13T00:00:00Z', items: [{ id: 'si-1', source_pricing_item_id: 'pi-1', source_pricing_document_id: 'p-1', line_no: 1, content: '彩盒', quantity: '1000.0000', unit_price: '1.0000', plate_fee: '0.0000', die_fee: '0.0000', amount: '1000.0000', source_snapshot: {} }] }),
  }
})

describe('Phase 8 帳務頁', () => {
  it('待請款頁顯示單一對帳單流程與稅務預設關閉', async () => {
    await renderApp(['/statements'], { session })
    expect(await screen.findByRole('heading', { level: 1, name: '待請款與對帳單' })).toBeInTheDocument()
    expect(await screen.findByText('PRC-20260813-001')).toBeInTheDocument()
    expect(screen.getByText(/公司預設關閉/)).toBeInTheDocument()
    expect(screen.getByText('STM-202608-001')).toBeInTheDocument()
  })

  it('收款頁顯示部分收款入口與帳齡', async () => {
    await renderApp(['/receipts'], { session })
    expect(await screen.findByRole('heading', { level: 1, name: '收款、未收款與帳齡' })).toBeInTheDocument()
    expect(await screen.findByRole('checkbox', { name: /STM-202608-001/ })).toBeInTheDocument()
    expect(screen.getByText('1～30 天')).toBeInTheDocument()
  })

  it('A4 對帳單預覽使用發行資料與公司抬頭', async () => {
    await renderApp(['/statements/s-1/print'], { session })
    expect(await screen.findByRole('heading', { level: 1, name: '虛構印刷公司' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '對帳單' })).toBeInTheDocument()
    expect(screen.getByText('STM-202608-001')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '列印 A4' })).toBeInTheDocument()
  })
})
