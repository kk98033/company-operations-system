import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderApp } from '../test/renderApp'

describe('統一 UI 版型頁', () => {
  it('總覽預設顯示 KPI，切到清單後不顯示 KPI 並保留固定工單欄', async () => {
    const user = userEvent.setup()
    await renderApp(['/ui-patterns'])

    expect(screen.getByRole('heading', { level: 1, name: '統一 UI 版型' })).toBeInTheDocument()
    expect(screen.getByLabelText('工單摘要')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '工單總覽版型' })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /清單查詢/ }))

    expect(screen.queryByLabelText('工單摘要')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '工單清單版型' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: '工單號' })).toHaveClass('ui-data-table__sticky')
    expect(screen.getByLabelText('查詢條件')).toBeInTheDocument()
  })

  it('新增編輯與詳細資料採獨立版型且不放 KPI', async () => {
    const user = userEvent.setup()
    await renderApp(['/ui-patterns'])

    await user.click(screen.getByRole('tab', { name: /新增／編輯/ }))
    expect(screen.getByRole('heading', { level: 2, name: '新增工單版型' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: /^客戶/ })).toBeInTheDocument()
    expect(screen.queryByLabelText('工單摘要')).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /詳細資料/ }))
    expect(screen.getByRole('heading', { level: 2, name: '工單 WO-DEMO-001' })).toBeInTheDocument()
    expect(screen.getByText('關聯作業')).toBeInTheDocument()
    expect(screen.queryByLabelText('工單摘要')).not.toBeInTheDocument()
  })

  it('頁籤以方向鍵、Home 與 End 切換，且只有目前頁籤進入 Tab 順序', async () => {
    const user = userEvent.setup()
    await renderApp(['/ui-patterns'])

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(4)
    expect(tabs.map((tab) => tab.tabIndex)).toEqual([0, -1, -1, -1])

    tabs[0].focus()
    await user.keyboard('{ArrowRight}')
    expect(tabs[1]).toHaveFocus()
    expect(tabs[1]).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { level: 2, name: '工單清單版型' })).toBeInTheDocument()

    await user.keyboard('{End}')
    expect(tabs[3]).toHaveFocus()
    expect(screen.getByRole('heading', { level: 2, name: '工單 WO-DEMO-001' })).toBeInTheDocument()

    await user.keyboard('{Home}')
    expect(tabs[0]).toHaveFocus()
    expect(screen.getByRole('heading', { level: 2, name: '工單總覽版型' })).toBeInTheDocument()
  })
})
