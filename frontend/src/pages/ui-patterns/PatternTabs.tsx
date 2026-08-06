import { useRef, type KeyboardEvent } from 'react'

export type Pattern = 'overview' | 'list' | 'form' | 'detail'

const patterns: Array<{ id: Pattern; label: string; note: string }> = [
  { id: 'overview', label: '總覽', note: 'KPI 與待辦' },
  { id: 'list', label: '清單查詢', note: '篩選與表格' },
  { id: 'form', label: '新增／編輯', note: '分區表單' },
  { id: 'detail', label: '詳細資料', note: '唯讀與關聯' },
]

export function PatternTabs({
  activePattern,
  onChange,
}: {
  activePattern: Pattern
  onChange: (pattern: Pattern) => void
}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  function moveFocus(event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    let nextIndex: number | undefined

    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % patterns.length
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + patterns.length) % patterns.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = patterns.length - 1

    if (nextIndex === undefined) return

    event.preventDefault()
    const nextPattern = patterns[nextIndex]
    onChange(nextPattern.id)
    tabRefs.current[nextIndex]?.focus()
  }

  return (
    <div className="ui-pattern-tabs" role="tablist" aria-label="通用版型">
      {patterns.map((pattern, index) => {
        const isActive = activePattern === pattern.id

        return (
          <button
            aria-controls="ui-pattern-panel"
            aria-selected={isActive}
            className={isActive ? 'is-active' : ''}
            id={`ui-pattern-tab-${pattern.id}`}
            key={pattern.id}
            onClick={() => onChange(pattern.id)}
            onKeyDown={(event) => moveFocus(event, index)}
            ref={(element) => { tabRefs.current[index] = element }}
            role="tab"
            tabIndex={isActive ? 0 : -1}
            type="button"
          >
            <strong>{pattern.label}</strong>
            <small>{pattern.note}</small>
          </button>
        )
      })}
    </div>
  )
}
