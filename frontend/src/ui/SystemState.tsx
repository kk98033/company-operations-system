import type { ReactNode } from 'react'

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
