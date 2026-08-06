import { render, screen, within } from '@testing-library/react'

import * as UiPatterns from './UiPatterns'

describe('UiPatterns public boundary', () => {
  it('保留既有九個 runtime exports', () => {
    const kpiItem = {
      label: '待處理',
      value: '3',
      hint: '測試型別邊界',
    } satisfies UiPatterns.KpiItem

    expect(kpiItem.label).toBe('待處理')
    expect(Object.keys(UiPatterns).sort()).toEqual([
      'DataTableFrame',
      'DefinitionGrid',
      'Field',
      'FilterBar',
      'KpiStrip',
      'PageHeader',
      'Section',
      'StatusLabel',
      'SystemState',
    ])
  })

  it('拆檔後保留共用元件的 DOM semantics 與 class contract', () => {
    const { container } = render(
      <>
        <UiPatterns.PageHeader
          eyebrow="測試模組"
          title="測試頁面"
          actions={[{ label: '建立資料', tone: 'primary' }]}
        />
        <UiPatterns.FilterBar>
          <UiPatterns.Field label="關鍵字" required hint="輸入測試值">
            <input defaultValue="範例" />
          </UiPatterns.Field>
        </UiPatterns.FilterBar>
        <UiPatterns.Section title="資料區">
          <UiPatterns.DataTableFrame footer={<span>共 1 筆</span>}>
            <table><tbody><tr><td>內容</td></tr></tbody></table>
          </UiPatterns.DataTableFrame>
        </UiPatterns.Section>
        <UiPatterns.DefinitionGrid items={[{ label: '狀態', value: <UiPatterns.StatusLabel tone="working">處理中</UiPatterns.StatusLabel> }]} />
      </>,
    )

    expect(container.querySelector('.ui-page-header')?.tagName).toBe('HEADER')
    expect(screen.getByRole('button', { name: '建立資料' })).toHaveClass('ui-button', 'ui-button--primary')
    expect(screen.getByRole('region', { name: '查詢條件' })).toHaveClass('ui-filter-bar')
    expect(screen.getByRole('textbox', { name: /關鍵字/ }).closest('label')).toHaveClass('ui-field')
    expect(screen.getByRole('heading', { level: 2, name: '資料區' }).closest('section')).toHaveClass('ui-section')
    expect(container.querySelector('.ui-table-scroll')).toContainElement(screen.getByRole('table'))
    expect(container.querySelector('.ui-table-footer')).toHaveTextContent('共 1 筆')
    expect(within(container.querySelector('dl')!).getByText('處理中')).toHaveClass('ui-status', 'ui-status--working')
  })
})
