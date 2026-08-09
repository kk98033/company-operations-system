import axe, { type ElementContext, type RunOptions } from 'axe-core'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, vi } from 'vitest'

import { workflowModules } from '../app/workflowModules'
import { renderApp } from './renderApp'

const accessibilityOptions: RunOptions = {
  runOnly: {
    type: 'tag',
    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'],
  },
  rules: {
    // JSDOM 沒有真實排版與像素顏色；色彩對比由實際瀏覽器人工基線負責。
    'color-contrast': { enabled: false },
  },
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(
    Response.json({ checks: [], status: 'ready' }),
  ))
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

async function expectNoAccessibilityViolations(context: ElementContext = document.body) {
  const results = await axe.run(context, accessibilityOptions)
  const violations = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    targets: violation.nodes.map((node) => node.target.join(' ')),
  }))

  expect(violations).toEqual([])
}

describe('自動無障礙基線', () => {
  it('登入頁沒有 axe WCAG A／AA 與 best-practice 違規', async () => {
    vi.stubEnv('VITE_ORGANIZATION_ID', '10000000-0000-4000-8000-000000000001')
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation(async () => (
      Response.json({
        error: { code: 'SESSION_INVALID', details: null, message: '請重新登入' },
      }, { status: 401 })
    )))

    await renderApp(['/login'], { session: null })

    expect(await screen.findByRole('heading', { level: 1, name: '公司管理系統' }))
      .toBeInTheDocument()
    await expectNoAccessibilityViolations()
  })

  it.each([
    ['首頁', '/'],
    ['404', '/not-a-real-page'],
  ])('%s 沒有 axe WCAG A／AA 與 best-practice 違規', async (_label, route) => {
    await renderApp([route])
    if (route === '/') {
      expect(await screen.findByRole('status')).toHaveTextContent(
        'API 與必要相依服務目前可使用',
      )
    }
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    await expectNoAccessibilityViolations()
  })

  it('統一 UI 四種版型都沒有 axe 違規', async () => {
    const user = userEvent.setup()
    await renderApp(['/ui-patterns'])

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    await expectNoAccessibilityViolations()

    for (const name of ['清單查詢 篩選與表格', '新增／編輯 分區表單', '詳細資料 唯讀與關聯']) {
      await user.click(screen.getByRole('tab', { name }))
      expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
      await expectNoAccessibilityViolations()
    }
  })

  it.each(workflowModules)(
    '$label 路由沒有 axe WCAG A／AA 與 best-practice 違規',
    async (module) => {
      await renderApp([module.path])
      expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
      await expectNoAccessibilityViolations()
    },
  )

  it('單頁工單新增路由沒有 axe WCAG A／AA 與 best-practice 違規', async () => {
    await renderApp(['/work-orders/new'])
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    await expectNoAccessibilityViolations()
  })
})
