import { QueryClient } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { AppProviders } from './providers'
import { ApiConnectionStatus } from './ApiConnectionStatus'

afterEach(() => vi.unstubAllGlobals())

function renderStatus() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <AppProviders queryClient={queryClient}>
      <ApiConnectionStatus />
    </AppProviders>,
  )
}

it('顯示 503 安全文字，重新檢查後可恢復已連線', async () => {
  const user = userEvent.setup()
  const fetchMock = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(Response.json({
      error: { code: 'SERVICE_NOT_READY', message: '必要相依服務尚未就緒' },
    }, { status: 503 }))
    .mockResolvedValueOnce(Response.json({ checks: [], status: 'ready' }))
  vi.stubGlobal('fetch', fetchMock)

  renderStatus()

  expect(await screen.findByRole('alert')).toHaveTextContent('必要相依服務尚未就緒')
  await user.click(screen.getByRole('button', { name: '重新檢查' }))
  expect(await screen.findByRole('status')).toHaveTextContent('API 與必要相依服務目前可使用')
})

it('離線時顯示可理解文字且不洩漏底層錯誤', async () => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(
    new TypeError('Failed to fetch database secret'),
  ))

  renderStatus()

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('無法連線至系統服務，請確認網路後再試。')
  expect(alert).not.toHaveTextContent('database secret')
})
