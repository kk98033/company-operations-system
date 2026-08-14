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
  error,
  children,
}: {
  label: string
  required?: boolean
  hint?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className={`ui-field${error ? ' ui-field--error' : ''}`}>
      <span className="ui-field__label">
        {label}
        {required ? <><b aria-hidden="true">＊</b><span className="visually-hidden">必填</span></> : null}
      </span>
      {children}
      {hint ? <small>{hint}</small> : null}
      {error ? <small className="ui-field__error">{error}</small> : null}
    </label>
  )
}
