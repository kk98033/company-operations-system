import type { ReactNode } from 'react'

type Action = {
  label: string
  onClick?: () => void
  tone?: 'primary' | 'secondary'
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions = [],
}: {
  eyebrow: string
  title: string
  description?: string
  actions?: Action[]
}) {
  return (
    <header className="ui-page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description ? <p className="ui-page-header__description">{description}</p> : null}
      </div>
      {actions.length > 0 ? (
        <div className="ui-page-actions">
          {actions.map((action) => (
            <button
              className={`ui-button ui-button--${action.tone ?? 'secondary'}`}
              key={action.label}
              onClick={action.onClick}
              type="button"
            >
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </header>
  )
}

export type KpiItem = {
  label: string
  value: string
  hint: string
  tone?: 'default' | 'warning' | 'danger' | 'success'
}

export function KpiStrip({ items, label }: { items: KpiItem[]; label: string }) {
  return (
    <section className="ui-kpi-strip" aria-label={label}>
      {items.map((item) => (
        <article className={`ui-kpi ui-kpi--${item.tone ?? 'default'}`} key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.hint}</small>
        </article>
      ))}
    </section>
  )
}

export function Section({
  title,
  description,
  actions,
  children,
}: {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="ui-section">
      <header className="ui-section__header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div className="ui-section__actions">{actions}</div> : null}
      </header>
      <div className="ui-section__body">{children}</div>
    </section>
  )
}

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

export function StatusLabel({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'working' | 'warning' | 'danger' | 'success'
}) {
  return <span className={`ui-status ui-status--${tone}`}>{children}</span>
}

export function DataTableFrame({ children, footer }: { children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="ui-table-frame">
      <div className="ui-table-scroll">{children}</div>
      {footer ? <footer className="ui-table-footer">{footer}</footer> : null}
    </div>
  )
}

export function DefinitionGrid({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>
}) {
  return (
    <dl className="ui-definition-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function SystemState({
  code,
  eyebrow,
  title,
  description,
  action,
  fullPage = false,
  role,
}: {
  code: string
  eyebrow: string
  title: string
  description: string
  action: ReactNode
  fullPage?: boolean
  role?: 'alert' | 'status'
}) {
  const body = (
    <div className="ui-system-state__body">
      <span className="ui-system-state__code" aria-hidden="true">{code}</span>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
        <div className="ui-system-state__action">{action}</div>
      </div>
    </div>
  )

  if (fullPage) {
    return (
      <main className="ui-system-state ui-system-state--full" role={role}>
        {body}
      </main>
    )
  }

  return (
    <section className="ui-system-state" role={role}>
      {body}
    </section>
  )
}
