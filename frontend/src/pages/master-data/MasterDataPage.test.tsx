import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import { renderApp } from '../../test/renderApp'
import { syntheticCurrentSession } from '../../test/sessionFixture'

const session = { ...syntheticCurrentSession, capabilities: ['master_data.read', 'master_data.manage'] }
const meta = { filters: { keyword: null, status: null }, pagination: { has_next: false, has_previous: false, page: 1, page_size: 100, total_items: 0, total_pages: 0 }, sort: { direction: 'asc', field: 'code' } }

afterEach(() => vi.unstubAllGlobals())

it('可切換廠商、紙質、紙廠與固定製程主檔', async () => {
  const user = userEvent.setup()
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async (input) => (
    String(input).includes('process-definitions') ? Response.json([]) : Response.json({ items: [], meta })
  )))
  await renderApp(['/master-data'], { session })
  expect(await screen.findByRole('heading', { level: 1, name: '生產與採購主檔' })).toBeInTheDocument()
  await user.click(screen.getByRole('tab', { name: '製程' }))
  expect(await screen.findByText(/固定 13 道製程/)).toBeInTheDocument()
})

it('沒有主檔權限時拒絕進入', async () => {
  await renderApp(['/master-data'], { session: { ...syntheticCurrentSession, capabilities: [] } })
  expect(await screen.findByRole('heading', { name: '沒有主檔資料權限' })).toBeInTheDocument()
})
