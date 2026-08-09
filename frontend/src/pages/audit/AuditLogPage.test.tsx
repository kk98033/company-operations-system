import { screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const auditSession = {
  ...syntheticCurrentSession,
  capabilities: ['audit.read'],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

it('只有 audit.read 成員會看到導覽並讀取目前公司的遮罩紀錄', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json({
    items: [{
      action: 'role.update',
      actor_user_id: syntheticCurrentSession.user.id,
      after_data: { name: '新版名稱' },
      before_data: { name: '舊版名稱', password: '[REDACTED]' },
      created_at: '2026-08-09T08:00:00Z',
      document_number: null,
      entity_id: '30000000-0000-4000-8000-000000000003',
      entity_type: 'role',
      event_status: 'success',
      id: '40000000-0000-4000-8000-000000000004',
      reason: '權限名稱調整',
      request_id: '50000000-0000-4000-8000-000000000005',
    }],
    meta: {
      filters: { action: null, entity_type: null, keyword: null, request_id: null },
      pagination: {
        has_next: false,
        has_previous: false,
        page: 1,
        page_size: 25,
        total_items: 1,
        total_pages: 1,
      },
      sort: { direction: 'desc', field: 'created_at' },
    },
  }))
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/audit-logs'], { session: auditSession })

  expect(await screen.findByRole('heading', { level: 1, name: '操作稽核' }))
    .toBeInTheDocument()
  const navigation = screen.getByRole('navigation', { name: '主要導覽' })
  expect(within(navigation).getByRole('link', { name: '操作稽核' }))
    .toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('table', { name: '目前公司的操作稽核紀錄' }))
    .toHaveTextContent('role.update')
  expect(screen.getByText('權限名稱調整')).toBeInTheDocument()
  expect(document.body).not.toHaveTextContent('must-never-leak')
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/api/v1/audit-logs?'),
    expect.objectContaining({ credentials: 'same-origin' }),
  )
})

it('沒有 audit.read 時不呼叫 API 並顯示權限限制', async () => {
  const fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/audit-logs'])

  expect(await screen.findByRole('heading', { name: '沒有稽核查詢權限' }))
    .toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '操作稽核' })).not.toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
})
