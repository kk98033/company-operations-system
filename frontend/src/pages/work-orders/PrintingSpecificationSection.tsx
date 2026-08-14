import { Field, Section } from '../../ui/UiPatterns'
import type { SideDraft, WorkOrderDraft } from './workOrderDraft'

type PrintDraft = WorkOrderDraft['print']
type Props = { value: PrintDraft; editable: boolean; onChange: (value: PrintDraft) => void }
const colors = ['c', 'm', 'y', 'k'] as const

function ColorSide({ label, value, editable, onChange }: { label: string; value: SideDraft; editable: boolean; onChange: (value: SideDraft) => void }) {
  return <fieldset className="work-order-color-side"><legend>印刷－{label}</legend>
    <Field label={`${label}色數`}><input data-error-key={`${label}-color-count`} disabled={!editable} max="20" min="0" onChange={(event) => onChange({ ...value, color_count: event.target.value })} type="number" value={value.color_count} /></Field>
    <div className="work-order-color-options" role="group" aria-label={`${label} CMYK`}>{colors.map((color) => <label key={color}><input checked={value[color]} disabled={!editable} onChange={(event) => onChange({ ...value, [color]: event.target.checked })} type="checkbox" /><span>{color.toUpperCase()}</span></label>)}</div>
    <Field label={`${label}特別色`}><textarea data-error-key={`${label}-special-colors`} disabled={!editable} maxLength={2000} onChange={(event) => onChange({ ...value, special_colors: event.target.value })} rows={3} value={value.special_colors} /></Field>
  </fieldset>
}

export function PrintingSpecificationSection({ value, editable, onChange }: Props) {
  const input = (field: keyof Omit<PrintDraft, 'front'|'back'>) => ({ 'data-error-key': `print-${field}`, disabled: !editable, name: `print-${field}`, onChange: (event: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [field]: event.target.value }), value: value[field] })
  return <div className="work-order-prototype__anchor" id="work-order-printing" tabIndex={-1}>
    <Section title="印刷" description="CMYK 預設全空；特別色可逐行輸入，不另建舊式色別設定頁。">
      <div className="work-order-print-summary">
        <Field label="印刷長度"><input {...input('length')} min="0" step="0.0001" type="number" /></Field>
        <Field label="印刷寬度"><input {...input('width')} min="0" step="0.0001" type="number" /></Field>
        <Field label="K 數"><input {...input('k_count')} min="0" type="number" /></Field>
        <Field label="模數"><input {...input('imposition_count')} min="0" type="number" /></Field>
        <Field label="印刷數量"><input {...input('print_quantity')} min="0" step="0.0001" type="number" /></Field>
        <Field label="加減量／±量"><input {...input('variance')} step="0.0001" type="number" /></Field>
      </div>
      <div className="work-order-color-grid">
        <ColorSide editable={editable} label="正面" onChange={(front) => onChange({ ...value, front })} value={value.front} />
        <ColorSide editable={editable} label="反面" onChange={(back) => onChange({ ...value, back })} value={value.back} />
      </div>
      <div className="work-order-print-summary"><Field label="合計色數"><input {...input('total_color_count')} max="40" min="0" type="number" /></Field></div>
    </Section>
  </div>
}
