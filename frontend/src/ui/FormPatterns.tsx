import type { ReactNode } from 'react'

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <section className="ui-filter-bar" aria-label="查詢條件">
      <div className="ui-filter-bar__title">查詢條件</div>
      <div className="ui-filter-grid">{children}</div>
    </section>
  )
}

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string
  required?: boolean
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="ui-field">
      <span className="ui-field__label">
        {label}
        {required ? <b aria-label="必填">＊</b> : null}
      </span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  )
}
