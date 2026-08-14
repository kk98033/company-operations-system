export type FormValidationIssue = {
  key: string
  label: string
  message: string
}

export function collectFormValidationIssues(form: HTMLFormElement): FormValidationIssue[] {
  return Array.from(form.elements)
    .filter((element): element is HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement => (
      element instanceof HTMLInputElement
      || element instanceof HTMLSelectElement
      || element instanceof HTMLTextAreaElement
    ))
    .filter((element) => !element.disabled && !element.validity.valid)
    .map((element, index) => {
      const key = element.dataset.errorKey || element.name || `field-${index}`
      const field = element.closest('.ui-field')
      const label = visibleFieldLabel(field?.querySelector('.ui-field__label'))
        || element.getAttribute('aria-label')
        || '欄位'
      return { key, label, message: validationMessage(element) }
    })
}

function visibleFieldLabel(label: Element | null | undefined) {
  if (!label) return ''
  const copy = label.cloneNode(true) as Element
  copy.querySelectorAll('[aria-hidden="true"], .visually-hidden').forEach((item) => item.remove())
  return copy.textContent?.trim() ?? ''
}

function validationMessage(element: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement) {
  const validity = element.validity
  if (validity.valueMissing) return '此欄位為必填'
  if (validity.rangeUnderflow) return `不可小於 ${element.getAttribute('min') ?? '允許值'}`
  if (validity.rangeOverflow) return `不可大於 ${element.getAttribute('max') ?? '允許值'}`
  if (validity.tooLong) return `不可超過 ${element.getAttribute('maxlength') ?? '規定'} 個字元`
  if (validity.typeMismatch || validity.badInput || validity.stepMismatch || validity.patternMismatch) {
    return '格式不正確'
  }
  return '輸入資料無效'
}
