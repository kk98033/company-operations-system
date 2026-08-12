import type { CustomerCreate } from '../../api/generated/company-system'

export type CustomerDraft = {
  code: string
  name: string
  short_name: string
  tax_identifier: string
  contact_name: string
  phone: string
  phone_secondary: string
  mobile: string
  fax: string
  email: string
  postal_code: string
  city: string
  address: string
  payment_terms: string
}

export const emptyCustomerDraft: CustomerDraft = {
  code: '', name: '', short_name: '', tax_identifier: '', contact_name: '', phone: '',
  phone_secondary: '', mobile: '', fax: '', email: '', postal_code: '', city: '', address: '',
  payment_terms: '',
}

export function customerPayload(draft: CustomerDraft): CustomerCreate {
  const optional = (value: string) => value.trim() || null
  return {
    code: draft.code.trim(), name: draft.name.trim(),
    short_name: optional(draft.short_name), tax_identifier: optional(draft.tax_identifier),
    contact_name: optional(draft.contact_name), phone: optional(draft.phone),
    phone_secondary: optional(draft.phone_secondary), mobile: optional(draft.mobile),
    fax: optional(draft.fax), email: optional(draft.email),
    postal_code: optional(draft.postal_code), city: optional(draft.city),
    address: optional(draft.address), payment_terms: optional(draft.payment_terms),
  }
}
