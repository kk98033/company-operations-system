import type { FormEvent } from 'react'

import { Field, Section } from '../../ui/UiPatterns'
import type { CustomerDraft } from './customerDraft'

export function CustomerForm({
  draft, errorMessage, isPending, onChange, onSubmit, submitLabel,
}: {
  draft: CustomerDraft
  errorMessage?: string
  isPending: boolean
  onChange: (draft: CustomerDraft) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  submitLabel: string
}) {
  const field = (key: keyof CustomerDraft) => (value: string) => onChange({ ...draft, [key]: value })
  return (
    <form className="customer-form" onSubmit={onSubmit}>
      <Section title="識別資料" description="客戶代號在同一家公司內不分大小寫且唯一；舊代號的前導零會保留。">
        <div className="ui-form-grid">
          <Field label="客戶代號" required><input autoFocus maxLength={32} onChange={(event) => field('code')(event.target.value)} required value={draft.code} /></Field>
          <Field label="客戶名稱" required><input maxLength={200} onChange={(event) => field('name')(event.target.value)} required value={draft.name} /></Field>
          <Field label="客戶簡稱"><input maxLength={100} onChange={(event) => field('short_name')(event.target.value)} value={draft.short_name} /></Field>
          <Field label="統一編號"><input maxLength={20} onChange={(event) => field('tax_identifier')(event.target.value)} value={draft.tax_identifier} /></Field>
        </div>
      </Section>
      <Section title="交易條件" description="供報價與工單帶入的文字條件；新對帳單計稅仍依公司設定且預設關閉。">
        <div className="ui-form-grid">
          <Field label="付款條件"><textarea maxLength={200} onChange={(event) => field('payment_terms')(event.target.value)} rows={3} value={draft.payment_terms} /></Field>
        </div>
      </Section>
      <Section title="主要聯絡方式" description="先保存公司日常最常使用的一組聯絡資料；多聯絡人會在後續主檔擴充。">
        <div className="ui-form-grid">
          <Field label="聯絡人"><input maxLength={100} onChange={(event) => field('contact_name')(event.target.value)} value={draft.contact_name} /></Field>
          <Field label="電話"><input maxLength={32} onChange={(event) => field('phone')(event.target.value)} type="tel" value={draft.phone} /></Field>
          <Field label="電話 2"><input maxLength={32} onChange={(event) => field('phone_secondary')(event.target.value)} type="tel" value={draft.phone_secondary} /></Field>
          <Field label="行動電話"><input maxLength={32} onChange={(event) => field('mobile')(event.target.value)} type="tel" value={draft.mobile} /></Field>
          <Field label="傳真"><input maxLength={32} onChange={(event) => field('fax')(event.target.value)} value={draft.fax} /></Field>
          <Field label="Email"><input maxLength={254} onChange={(event) => field('email')(event.target.value)} type="email" value={draft.email} /></Field>
        </div>
      </Section>
      <Section title="郵寄地址">
        <div className="ui-form-grid customer-address-grid">
          <Field label="郵遞區號"><input maxLength={16} onChange={(event) => field('postal_code')(event.target.value)} value={draft.postal_code} /></Field>
          <Field label="縣市"><input maxLength={100} onChange={(event) => field('city')(event.target.value)} value={draft.city} /></Field>
          <Field label="完整地址"><textarea maxLength={500} onChange={(event) => field('address')(event.target.value)} rows={3} value={draft.address} /></Field>
        </div>
      </Section>
      {errorMessage ? <p className="company-profile-message company-profile-message--error" role="alert">{errorMessage}</p> : null}
      <footer className="ui-form-footer customer-form-footer">
        <span>必填欄位只有客戶代號與名稱。</span>
        <button className="ui-button ui-button--primary" disabled={isPending} type="submit">{isPending ? '存檔中…' : submitLabel}</button>
      </footer>
    </form>
  )
}
