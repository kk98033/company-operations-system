import axe, { type ElementContext, type RunOptions } from 'axe-core'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

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
  it.each([
    ['首頁', '/'],
    ['404', '/not-a-real-page'],
  ])('%s 沒有 axe WCAG A／AA 與 best-practice 違規', async (_label, route) => {
    await renderApp([route])
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
})
