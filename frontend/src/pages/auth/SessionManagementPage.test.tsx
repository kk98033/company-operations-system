import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const managerSession = {
  ...syntheticCurrentSession,
  capabilities: ['sessions.manage'],
}

function sessionItem(overrides: Record<string, unknown> = {}) {
  return {
    id: '30000000-0000-4000-8000-000000000003',
    organization_member_id: '40000000-0000-4000-8000-000000000004',
    user: syntheticCurrentSession.user,
    client_summary: 'Chrome／Windows',
    created_at: '2026-08-20T08:00:00Z',
    expires_at: '2026-08-20T16:00:00Z',
    revoked_at: null,
    status: 'active',
    is_current: true,
    ...overrides,
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('所有員工都能查看自己的安全摘要且不要求公司管理權限', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/api/v1/auth/sessions')) {
      return Response.json({ items: [sessionItem()], total_items: 1 })
    }
    throw new Error(`unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/sessions'])

  expect(await screen.findByRole('heading', { level: 1, name: '登入與工作階段' }))
    .toBeInTheDocument()
  expect(screen.getByRole('table', { name: '我的登入工作階段' }))
    .toHaveTextContent('Chrome／Windows')
  expect(screen.getByText('目前裝置')).toBeInTheDocument()
  expect(screen.getByText('你可以查看自己的紀錄；如發現異常登入，請聯絡公司系統管理者。'))
    .toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalledWith(
    expect.stringContaining('/auth/company-sessions'),
    expect.anything(),
  )
})

it('sessions.manage 可查看公司登入並以原因遠端撤銷', async () => {
  const target = sessionItem({
    id: '50000000-0000-4000-8000-000000000005',
    organization_member_id: '60000000-0000-4000-8000-000000000006',
    user: {
      id: '70000000-0000-4000-8000-000000000007',
      login_name: 'second.operator',
      display_name: '第二位操作員',
    },
    client_summary: 'Edge／Windows',
    is_current: false,
  })
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.includes('/api/v1/auth/sessions')) {
      return Response.json({ items: [sessionItem()], total_items: 1 })
    }
    if (url.endsWith('/api/v1/auth/company-sessions?limit=100')) {
      return Response.json({ items: [sessionItem(), target], total_items: 2 })
    }
    if (url.endsWith(`/api/v1/auth/company-sessions/${target.id}/revoke`)) {
      expect(init?.method).toBe('POST')
      expect(init?.headers).toEqual({ 'X-CSRF-Token': 'signed-csrf' })
      expect(init?.body).toBe(JSON.stringify({ reason: '遺失公司筆電' }))
      return new Response(null, { status: 204 })
    }
    throw new Error(`unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  document.cookie = 'company_system_csrf=signed-csrf; Path=/'

  await renderApp(['/settings/sessions'], { session: managerSession })

  const companyTable = await screen.findByRole('table', { name: '公司尚未撤銷的登入工作階段' })
  const targetRow = within(companyTable).getByText('第二位操作員').closest('tr')
  expect(targetRow).not.toBeNull()
  fireEvent.change(screen.getByLabelText('撤銷原因'), { target: { value: '遺失公司筆電' } })
  fireEvent.click(within(targetRow as HTMLElement).getByRole('button', { name: '撤銷此登入' }))

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/${target.id}/revoke`),
    expect.objectContaining({ method: 'POST' }),
  ))
})

it('目前裝置不可從公司列表誤按遠端撤銷', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/api/v1/auth/sessions')) {
      return Response.json({ items: [sessionItem()], total_items: 1 })
    }
    if (url.includes('/api/v1/auth/company-sessions')) {
      return Response.json({ items: [sessionItem()], total_items: 1 })
    }
    throw new Error(`unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/sessions'], { session: managerSession })

  const companyTable = await screen.findByRole('table', { name: '公司尚未撤銷的登入工作階段' })
  expect(within(companyTable).getByRole('button', { name: '撤銷此登入' })).toBeDisabled()
  expect(within(companyTable).getByRole('button', { name: '撤銷此帳號全部' })).toBeDisabled()
})
