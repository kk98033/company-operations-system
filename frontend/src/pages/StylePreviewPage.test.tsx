import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderApp } from '../test/renderApp'

describe('介面風格比較頁', () => {
  it('預設顯示平面工業 ERP，並可切換三種提案', async () => {
    const user = userEvent.setup()
    await renderApp(['/style-preview'])

    expect(
      screen.getByRole('heading', { level: 1, name: '介面風格比較' }),
    ).toBeInTheDocument()

    const industrialButton = screen.getByRole('button', {
      name: /A 平面工業 ERP/,
    })
    const desktopButton = screen.getByRole('button', {
      name: /B 現代桌面 ERP/,
    })
    const bootstrapButton = screen.getByRole('button', {
      name: /C Bootstrap 企業版/,
    })

    expect(industrialButton).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('heading', { level: 2, name: '工單生產看板' }),
    ).toBeInTheDocument()

    await user.click(desktopButton)
    expect(desktopButton).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('heading', { level: 2, name: '工單作業清單' }),
    ).toBeInTheDocument()

    await user.click(bootstrapButton)
    expect(bootstrapButton).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('heading', { level: 2, name: '工單管理' }),
    ).toBeInTheDocument()
  })
})
