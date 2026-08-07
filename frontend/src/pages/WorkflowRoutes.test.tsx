import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { workflowModules } from '../app/workflowModules'
import { renderApp } from '../test/renderApp'

describe('公司主流程路由', () => {
  it.each(workflowModules)('$label 可直接進入且明確標示為假資料原型', async (module) => {
    await renderApp([module.path])

    expect(screen.getByRole('heading', { level: 1, name: module.label })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Phase 0 假資料原型')
    expect(within(screen.getByRole('navigation', { name: '主要導覽' }))
      .getByRole('link', { name: module.label }))
      .toHaveAttribute('aria-current', 'page')
  })

  it.each(workflowModules.filter((module) => module.id !== 'work-orders'))(
    '$label 保留跨模組資料流導覽',
    async (module) => {
      await renderApp([module.path])

      expect(screen.getByRole('navigation', { name: '公司主流程' }))
        .toBeInTheDocument()
      expect(document.querySelector('.module-flow__link.is-active'))
        .toHaveTextContent(module.label)
    },
  )

  it('工單的所有規劃區塊都在同一張表單，不顯示跨模組上一站／下一站', async () => {
    const user = userEvent.setup({ skipHover: true })
    await renderApp(['/work-orders/new'])

    const form = screen.getByRole('form', { name: '工單整合建檔原型' })
    const sectionNav = within(form).getByRole('navigation', { name: '工單頁內區段' })

    for (const sectionName of ['客戶與訂單資料', '備紙', '印刷', '製程規劃', '備註與圖片']) {
      expect(within(form).getByRole('heading', { level: 2, name: sectionName }))
        .toBeInTheDocument()
    }
    for (const groupName of ['面紙', '底紙', '浪紙', '印刷－正面', '印刷－反面', '美工', '運送', '其他']) {
      expect(within(form).getByRole('group', { name: groupName })).toBeInTheDocument()
    }
    expect(within(form).getByRole('group', { name: '製版類型' })).toBeInTheDocument()
    expect(within(form).getByRole('group', { name: '輪轉方向' })).toBeInTheDocument()
    expect(within(form).getByRole('radio', { name: '新版' })).not.toBeChecked()
    expect(within(form).getByRole('radio', { name: '舊版' })).not.toBeChecked()
    expect(within(form).getByRole('radio', { name: '天地輪轉' })).not.toBeChecked()
    expect(within(form).getByRole('radio', { name: '左右輪轉' })).not.toBeChecked()
    expect(within(form).getByText('P0-08 已依公司附件確認')).toBeInTheDocument()
    for (const linkName of ['客戶與訂單', '備紙', '印刷', '製程', '備註與圖片']) {
      expect(within(sectionNav).getByRole('link', { name: new RegExp(linkName) }))
        .toHaveAttribute('href', expect.stringMatching(/^#work-order-/))
    }
    expect(document.querySelector('.ui-kpi-strip')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '下一站：生產管理' })).not.toBeInTheDocument()
    expect(within(form).getByText('單一／多成品待 P0-02 確認')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '儲存' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: '列印' })).toHaveLength(2)

    for (const selector of ['.ui-page-actions', '.work-order-prototype__footer']) {
      const actionArea = document.querySelector(selector)
      expect(actionArea).not.toBeNull()
      const actions = within(actionArea as HTMLElement).getAllByRole('button')
      expect(actions.map((button) => button.textContent)).toEqual(['另存新檔', '儲存', '取消', '列印'])
      for (const button of actions) expect(button).toBeDisabled()
    }

    await user.click(within(sectionNav).getByRole('link', { name: /製程/ }))
    expect(document.querySelector('#work-order-process')).toHaveFocus()
    expect(window.location.hash).toBe('#work-order-process')
  })

  it('工單清單保留關鍵字查詢、價格欄位與單頁新增入口', async () => {
    const user = userEvent.setup({ skipHover: true })
    const { router } = await renderApp(['/work-orders'])

    expect(screen.getByRole('searchbox', { name: /關鍵字查詢/ })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: '資料範圍' })).toHaveValue('all')
    for (const columnName of ['單價', '版費', '刀模費']) {
      expect(screen.getByRole('columnheader', { name: columnName })).toBeInTheDocument()
    }
    expect(screen.getByRole('columnheader', { name: '資料狀態' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'DEMO-WO-H01' })).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('歷史／封存')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Phase 4 開啟' })).toHaveLength(2)
    for (const button of screen.getAllByRole('button', { name: 'Phase 4 開啟' })) {
      expect(button).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: '清除' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '查詢' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: '新增工單' }))
    expect(router.state.location.pathname).toBe('/work-orders/new')
    expect(screen.getByRole('heading', { level: 1, name: '工單建檔作業' }))
      .toBeInTheDocument()
  })

  it('可由側邊欄走過客戶到收款的九個模組', async () => {
    const user = userEvent.setup({ skipHover: true })
    await renderApp(['/'])
    const navigation = screen.getByRole('navigation', { name: '主要導覽' })

    for (const module of workflowModules) {
      await user.click(within(navigation).getByRole('link', { name: module.label }))
      expect(screen.getByRole('heading', { level: 1, name: module.label }))
        .toBeInTheDocument()
    }
  })
})
