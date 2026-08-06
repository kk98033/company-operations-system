import type { ReactNode } from 'react'

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
