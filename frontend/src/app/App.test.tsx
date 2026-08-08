import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useQueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'

import { AppProviders } from './providers'
import { workflowModules } from './workflowModules'
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
    const pendingKpi = screen.getByText('P0 待確認').closest('article')
    expect(pendingKpi).not.toBeNull()
    expect(within(pendingKpi as HTMLElement).getByText('1')).toBeInTheDocument()
    expect(within(pendingKpi as HTMLElement).getByText('9／10 已由公司確認')).toBeInTheDocument()
    expect(screen.getByText(/P0 已確認 9／10，只剩 P0-05/)).toBeInTheDocument()
  })

  it('可收合與展開正式側邊欄', async () => {
    const user = userEvent.setup()
    await renderApp(['/'])

    const collapseButton = screen.getByRole('button', { name: '收合側邊欄' })
    await user.click(collapseButton)

    expect(screen.getByRole('button', { name: '展開側邊欄' })).toBeInTheDocument()
    expect(document.querySelector('.app-shell')).toHaveClass('app-shell--collapsed')
  })

  it('鍵盤焦點先進入跳轉連結，並可用 Enter 操作側邊欄按鈕', async () => {
    const user = userEvent.setup()
    await renderApp(['/'])

    await user.tab()
    const skipLink = screen.getByRole('link', { name: '跳到主要內容' })
    expect(skipLink).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(document.querySelector('#main-content')).toHaveFocus()

    skipLink.focus()

    await user.tab()
    expect(screen.getByRole('link', { name: '首頁' })).toHaveFocus()

    for (const module of workflowModules) {
      await user.tab()
      expect(screen.getByRole('link', { name: module.label })).toHaveFocus()
    }

    await user.tab()
    expect(screen.getByRole('link', { name: '統一 UI 版型' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('link', { name: '設計比較紀錄' })).toHaveFocus()
    await user.tab()

    const collapseButton = screen.getByRole('button', { name: '收合側邊欄' })
    expect(collapseButton).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: '展開側邊欄' })).toHaveFocus()
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
    expect(document.querySelector('.ui-system-state')).toBeInTheDocument()
  })
})
