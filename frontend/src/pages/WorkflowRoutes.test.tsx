import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { workflowModules } from '../app/workflowModules'
import { renderApp } from '../test/renderApp'

describe('公司主流程路由', () => {
  it.each(workflowModules)('$label 可直接進入且明確標示為假資料原型', async (module) => {
    await renderApp([module.path])

    expect(screen.getByRole('heading', { level: 1, name: module.label })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Phase 0 假資料原型')
    expect(screen.getByRole('navigation', { name: '公司主流程' }))
      .toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: module.label }))
      .toEqual(expect.arrayContaining([expect.any(HTMLAnchorElement)]))
    expect(screen.getAllByRole('link', { name: module.label })[0])
      .toHaveAttribute('aria-current', 'page')
    expect(document.querySelector('.module-flow__link.is-active'))
      .toHaveTextContent(module.label)
  })

  it('可由客戶管理逐站走到收款管理，再回到首頁', async () => {
    const user = userEvent.setup({ skipHover: true })
    await renderApp([workflowModules[0].path])

    for (const [index, module] of workflowModules.entries()) {
      expect(screen.getByRole('heading', { level: 1, name: module.label }))
        .toBeInTheDocument()

      const nextModule = workflowModules[index + 1]
      if (nextModule) {
        await user.click(screen.getByRole('link', { name: `下一站：${nextModule.label}` }))
      }
    }

    await user.click(screen.getByRole('link', { name: '回到首頁' }))
    expect(screen.getByRole('heading', { level: 1, name: '首頁' })).toBeInTheDocument()
  })
})
