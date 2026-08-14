import type { RefObject } from 'react'
import type { FormValidationIssue } from './formValidation'

export function FormValidationSummary({
  issues,
  formRef,
}: {
  issues: readonly FormValidationIssue[]
  formRef: RefObject<HTMLFormElement | null>
}) {
  if (!issues.length) return null
  return <section aria-labelledby="form-validation-title" className="ui-validation-summary" role="alert">
    <strong id="form-validation-title">請完成以下欄位後再存檔</strong>
    <ul>{issues.map((issue) => <li key={issue.key}><button onClick={() => formRef.current?.querySelector<HTMLElement>(`[data-error-key="${issue.key}"]`)?.focus()} type="button">{issue.label}：{issue.message}</button></li>)}</ul>
  </section>
}
