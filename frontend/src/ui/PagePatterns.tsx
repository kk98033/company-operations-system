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
