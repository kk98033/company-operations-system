import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { workflowModules } from '../app/workflowModules'
import { renderApp } from '../test/renderApp'

const prototypeModules = workflowModules.filter(
  (module) => ![
    'customers', 'quotations', 'cases', 'work-orders', 'production', 'inventory', 'shipments',
  ].includes(module.id),
)

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

  it('可由側邊欄走過客戶到收款的十個模組', async () => {
    const user = userEvent.setup({ skipHover: true })
    await renderApp(['/'])
    const navigation = screen.getByRole('navigation', { name: '主要導覽' })

    for (const module of workflowModules) {
      await user.click(within(navigation).getByRole('link', { name: module.label }))
      const heading = module.id === 'customers'
        ? '沒有客戶資料權限'
        : module.id === 'quotations'
          ? '沒有報價資料權限'
          : module.id === 'cases'
            ? '沒有案件權限'
            : module.id === 'work-orders'
              ? '沒有工單資料權限'
              : module.id === 'production'
                ? '沒有生產資料權限'
                : module.id === 'inventory'
                  ? '沒有庫存資料權限'
                : module.id === 'shipments'
                  ? '沒有出貨資料權限'
          : module.label
      expect(screen.getByRole('heading', { level: 1, name: heading }))
        .toBeInTheDocument()
    }
  })
})
