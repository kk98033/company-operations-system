import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { workflowModules } from '../app/workflowModules'
import { renderApp } from '../test/renderApp'

const prototypeModules = workflowModules.filter((module) => module.id !== 'customers')

describe('公司主流程路由', () => {
  it('報價、案件與工單模組追蹤到完整需求編號', () => {
    const quotations = workflowModules.find((module) => module.id === 'quotations')
    const cases = workflowModules.find((module) => module.id === 'cases')
    const workOrders = workflowModules.find((module) => module.id === 'work-orders')

    expect(quotations?.requirementIds).toEqual([
      'QUO-001', 'QUO-002', 'QUO-003', 'QUO-004', 'QUO-005', 'QUO-006', 'QUO-007', 'QUO-008',
    ])
    expect(cases?.requirementIds).toEqual([
      'CASE-001', 'CASE-002', 'CASE-003', 'CASE-004', 'CASE-005',
    ])
    expect(workOrders?.requirementIds).toEqual([
      'WO-001', 'WO-002', 'WO-003', 'WO-004', 'WO-005', 'WO-006',
      'WO-007', 'WO-008', 'WO-009', 'WO-010', 'WO-011', 'WO-012',
      'WO-013', 'WO-014', 'WO-015', 'WO-016',
    ])
  })

  it.each(prototypeModules)('$label 可直接進入且明確標示為展示資料', async (module) => {
    await renderApp([module.path])

    expect(screen.getByRole('heading', { level: 1, name: module.label })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('展示資料')
    expect(within(screen.getByRole('navigation', { name: '主要導覽' }))
      .getByRole('link', { name: module.label }))
      .toHaveAttribute('aria-current', 'page')
  })

  it.each(prototypeModules.filter((module) => module.id !== 'work-orders'))(
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

    const form = screen.getByRole('form', { name: '工單整合建檔展示' })
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
    expect(within(form).getByText('製程欄位依公司附件確認')).toBeInTheDocument()
    expect(within(form).getByLabelText('客編')).not.toBeRequired()
    expect(within(form).getByLabelText(/^工作單號/)).not.toBeRequired()
    expect(within(form).getByLabelText('訂單數量')).toHaveValue('')
    expect(within(form).getByLabelText('印刷數量')).toHaveValue('')

    const processOrder = Array.from(form.querySelectorAll('.work-order-process-row > legend'))
      .map((legend) => legend.textContent)
    expect(processOrder).toEqual([
      '美工', '輸出', '製版', '打樣', '印刷', '上光', '裱紙',
      '模具', '軋型', '加工', '糊邊', '運送', '其他',
    ])

    const topLevelLabels = (processName: string) => {
      const row = Array.from(form.querySelectorAll('.work-order-process-row'))
        .find((candidate) => candidate.querySelector(':scope > legend')?.textContent === processName)
      return Array.from(row?.children ?? []).map((child) => child.textContent?.trim())
    }
    expect(topLevelLabels('上光')).toEqual(['上光', '協力廠', '上光種類', '製程說明'])
    expect(topLevelLabels('軋型')).toEqual(['軋型', '協力廠', '刀模號碼模數', '製程說明'])
    expect(topLevelLabels('製版')).toEqual(['製版', '協力廠', '製程說明', '製版類型新版舊版輪轉方向天地輪轉左右輪轉'])
    expect(topLevelLabels('糊邊')).toEqual(['糊邊', '協力廠', '製程說明', '裝箱裝袋'])
    expect(within(form).getByLabelText('加減量／±量')).toBeInTheDocument()
    for (const linkName of ['客戶與訂單', '備紙', '印刷', '製程', '備註與圖片']) {
      expect(within(sectionNav).getByRole('link', { name: new RegExp(linkName) }))
        .toHaveAttribute('href', expect.stringMatching(/^#work-order-/))
    }
    expect(document.querySelector('.ui-kpi-strip')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '下一站：生產管理' })).not.toBeInTheDocument()
    expect(within(form).getByText('一工單一主要品項已確認')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '存檔' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: '列印' })).toHaveLength(2)

    for (const selector of ['.ui-page-actions', '.work-order-prototype__footer']) {
      const actionArea = document.querySelector(selector)
      expect(actionArea).not.toBeNull()
      const actions = within(actionArea as HTMLElement).getAllByRole('button')
      expect(actions.map((button) => button.textContent)).toEqual(['另存新檔', '存檔', '取消', '列印'])
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
    expect(screen.getAllByRole('button', { name: '尚未啟用' })).toHaveLength(2)
    for (const button of screen.getAllByRole('button', { name: '尚未啟用' })) {
      expect(button).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: '清除' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '查詢' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: '新增工單' }))
    expect(router.state.location.pathname).toBe('/work-orders/new')
    expect(screen.getByRole('heading', { level: 1, name: '工單建檔作業' }))
      .toBeInTheDocument()
  })

  it('案件原型顯示案件、子工單與製程三層責任', async () => {
    await renderApp(['/cases'])

    expect(screen.getByRole('heading', { level: 1, name: '案件管理' })).toBeInTheDocument()
    expect(screen.getByText('DEMO-CASE-001')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: '案件中的子工單假資料' })).toBeInTheDocument()
    expect(screen.getAllByRole('rowheader')).toHaveLength(3)
    expect(screen.getByText('一張工單一個主要品項')).toBeInTheDocument()
  })

  it('可由側邊欄走過客戶到收款的十個模組', async () => {
    const user = userEvent.setup({ skipHover: true })
    await renderApp(['/'])
    const navigation = screen.getByRole('navigation', { name: '主要導覽' })

    for (const module of workflowModules) {
      await user.click(within(navigation).getByRole('link', { name: module.label }))
      const heading = module.id === 'customers' ? '沒有客戶資料權限' : module.label
      expect(screen.getByRole('heading', { level: 1, name: heading }))
        .toBeInTheDocument()
    }
  })
})
