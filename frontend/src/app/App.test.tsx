import { screen } from '@testing-library/react'
import { useQueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'

import { AppProviders } from './providers'
import { renderApp } from '../test/renderApp'

function QueryClientProbe() {
  const queryClient = useQueryClient()
  return <output>{queryClient ? 'query-ready' : 'query-missing'}</output>
}

describe('應用程式骨架', () => {
  it('顯示首頁、桌面導覽與目前環境', async () => {
    await renderApp(['/'])

    expect(
      screen.getByRole('heading', { level: 1, name: '首頁' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '主要導覽' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '首頁' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByText('本機開發')).toBeInTheDocument()
  })

  it('使用共用 TanStack Query client', () => {
    render(
      <AppProviders>
        <QueryClientProbe />
      </AppProviders>,
    )

    expect(screen.getByText('query-ready')).toBeInTheDocument()
  })

  it('未知路徑顯示 404 並提供返回首頁入口', async () => {
    await renderApp(['/not-a-real-page'])

    expect(
      screen.getByRole('heading', { level: 1, name: '找不到這個頁面' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '回到首頁' })).toHaveAttribute(
      'href',
      '/',
    )
  })
})
