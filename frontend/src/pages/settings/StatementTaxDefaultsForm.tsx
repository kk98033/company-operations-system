import type { FormEvent } from 'react'

import { Field, Section, StatusLabel } from '../../ui/UiPatterns'

export interface StatementTaxDraft {
  enabled: boolean
  taxRatePercent: string
  roundingScope: '' | 'per_line' | 'grand_total'
  roundingDecimalPlaces: string
}

interface StatementTaxDefaultsFormProps {
  draft: StatementTaxDraft
  errorMessage?: string
  isPending: boolean
  isSuccess: boolean
  onChange: (draft: StatementTaxDraft) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  updatedAt: string
}

export function StatementTaxDefaultsForm({
  draft,
  errorMessage,
  isPending,
  isSuccess,
  onChange,
  onSubmit,
  updatedAt,
}: StatementTaxDefaultsFormProps) {
  const setEnabled = (enabled: boolean) => onChange(enabled
    ? { ...draft, enabled }
    : { enabled, taxRatePercent: '', roundingScope: '', roundingDecimalPlaces: '' })

  return (
    <Section
      title="對帳單預設計稅"
      description="新對帳單預設不計稅；報價單與工單不會套用此設定。"
    >
      <form onSubmit={onSubmit}>
        <label className="organization-tax-toggle">
          <input
            checked={draft.enabled}
            onChange={(event) => setEnabled(event.target.checked)}
            type="checkbox"
          />
          <span><strong>新對帳單預設啟用計稅</strong><small>目前預設關閉；每張對帳單仍須保存自己的金額快照。</small></span>
        </label>
        <div className="ui-form-grid organization-tax-grid">
          <Field label="預設稅率（%）" required={draft.enabled}>
            <input
              disabled={!draft.enabled}
              inputMode="decimal"
              max="100"
              min="0.0001"
              onChange={(event) => onChange({ ...draft, taxRatePercent: event.target.value })}
              required={draft.enabled}
              step="0.0001"
              type="number"
              value={draft.taxRatePercent}
            />
          </Field>
          <Field label="取整範圍" required={draft.enabled}>
            <select
              disabled={!draft.enabled}
              onChange={(event) => onChange({
                ...draft,
                roundingScope: event.target.value as StatementTaxDraft['roundingScope'],
              })}
              required={draft.enabled}
              value={draft.roundingScope}
            >
              <option value="">請選擇</option>
              <option value="per_line">逐筆取整</option>
              <option value="grand_total">總計取整</option>
            </select>
          </Field>
          <Field label="保留小數位" required={draft.enabled}>
            <select
              disabled={!draft.enabled}
              onChange={(event) => onChange({ ...draft, roundingDecimalPlaces: event.target.value })}
              required={draft.enabled}
              value={draft.roundingDecimalPlaces}
            >
              <option value="">請選擇</option>
              {[0, 1, 2, 3, 4].map((value) => <option key={value} value={value}>{value} 位</option>)}
            </select>
          </Field>
        </div>
        <div className="organization-settings-warning">
          <StatusLabel tone="warning">正式對帳功能驗收前不計算金額</StatusLabel>
          <p>此處先保存公司偏好；計算方法與去識別金額案例經公司確認後，才會由正式對帳單功能讀取。</p>
        </div>
        {errorMessage ? <p className="company-profile-message company-profile-message--error" role="alert">{errorMessage}</p> : null}
        {isSuccess ? <p className="company-profile-message" role="status">公司預設設定已存檔，並已寫入操作稽核。</p> : null}
        <footer className="ui-form-footer">
          <span>最後更新：{new Intl.DateTimeFormat('zh-TW', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(updatedAt))}</span>
          <div><button className="ui-button ui-button--primary" disabled={isPending} type="submit">{isPending ? '存檔中…' : '存檔'}</button></div>
        </footer>
      </form>
    </Section>
  )
}
