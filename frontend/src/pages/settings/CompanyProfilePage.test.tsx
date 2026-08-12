import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const settingsSession = {
  ...syntheticCurrentSession,
  capabilities: ['settings.manage'],
}

const profile = {
  address: '虛構測試地址 1 號',
  email: 'company@example.invalid',
  fax: '02-0000-0001',
  id: syntheticCurrentSession.organization.id,
  logo: null,
  name: '測試印刷股份有限公司（虛構）',
  phone: '02-0000-0000',
  representative_name: '測試負責人',
  tax_identifier: '00000000',
  updated_at: '2026-08-12T08:00:00Z',
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'company_system_csrf=; Max-Age=0; Path=/'
})

it('有 settings.manage 時可編輯目前公司並即時預覽共用頁首', async () => {
  const user = userEvent.setup()
  document.cookie = 'company_system_csrf=synthetic-csrf; Path=/'
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, init) => {
    if (init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      return Response.json({ ...profile, ...body, updated_at: '2026-08-12T09:00:00Z' })
    }
    return Response.json(profile)
  })
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/company'], { session: settingsSession })

  expect(await screen.findByRole('heading', { level: 1, name: '公司基本資料' }))
    .toBeInTheDocument()
  const navigation = screen.getByRole('navigation', { name: '主要導覽' })
  expect(within(navigation).getByRole('link', { name: '公司基本資料' }))
    .toHaveAttribute('aria-current', 'page')
  const companyName = screen.getByRole('textbox', { name: /公司名稱/ })
  await user.clear(companyName)
  await user.type(companyName, '新版虛構印刷公司')
  expect(within(screen.getByLabelText('公司頁首預覽')).getByText('新版虛構印刷公司'))
    .toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '存檔' }))

  expect(await screen.findByText('公司資料已存檔，並已寫入操作稽核。'))
    .toBeInTheDocument()
  const updateCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
  expect(updateCall?.[1]).toEqual(expect.objectContaining({
    credentials: 'same-origin',
    headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic-csrf' }),
  }))
  expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual(expect.objectContaining({
    expected_updated_at: profile.updated_at,
    name: '新版虛構印刷公司',
  }))
})

it('沒有 settings.manage 時不顯示導覽、不呼叫 API 並顯示權限限制', async () => {
  const fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)

  await renderApp(['/settings/company'])

  expect(await screen.findByRole('heading', { name: '沒有公司資料維護權限' }))
    .toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '公司基本資料' })).not.toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
})
