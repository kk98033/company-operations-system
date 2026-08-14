import type { CustomerListResponse } from '../../api/generated/company-system'
import { Field, Section, StatusLabel } from '../../ui/UiPatterns'
import type { WorkOrderDraft } from './workOrderDraft'

type Props = { draft: WorkOrderDraft; editable: boolean; customers?: CustomerListResponse; documentNumber?: string; validationErrors: Record<string, string>; onChange: (field: keyof WorkOrderDraft, value: string) => void }

export function WorkOrderBasicSection({ draft, editable, customers, documentNumber, validationErrors, onChange }: Props) {
  const field = (name: keyof WorkOrderDraft) => ({ 'aria-invalid': Boolean(validationErrors[name]), 'data-error-key': String(name), disabled: !editable, name: String(name), onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => onChange(name, event.target.value), value: String(draft[name]) })
  return <div className="work-order-prototype__anchor" id="work-order-basic" tabIndex={-1}>
    <Section title="客戶與訂單資料" description="選取客編後帶入客戶資料；一張工單只對應一個主要品項並隸屬一個案件。" actions={<StatusLabel tone="success">一工單一主要品項</StatusLabel>}>
      <div className="work-order-prototype__basic-grid">
        <Field error={validationErrors.customer_id} label="客編／客戶" required><select {...field('customer_id')} required><option value="">請選擇客戶</option>{customers?.items.map((customer) => <option key={customer.id} value={customer.id}>{customer.code} {customer.name}</option>)}</select></Field>
        <Field label="客名"><input readOnly value={customers?.items.find((item) => item.id === draft.customer_id)?.name ?? ''} /></Field>
        <Field label="客戶單號"><input {...field('customer_order_number')} maxLength={100} /></Field>
        <Field label="電話"><input readOnly value={customers?.items.find((item) => item.id === draft.customer_id)?.phone ?? ''} /></Field>
        <Field label="聯絡人"><input readOnly value={customers?.items.find((item) => item.id === draft.customer_id)?.contact_name ?? ''} /></Field>
        <Field label="地址"><input readOnly value={customers?.items.find((item) => item.id === draft.customer_id)?.address ?? ''} /></Field>
        <Field label="工作單號" hint="WO-YYYYMMDD-SSS"><input readOnly value={documentNumber ?? '存檔後自動產生'} /></Field>
        <Field error={validationErrors.order_date} label="訂購日期" required><input {...field('order_date')} required type="date" /></Field>
        <Field label="交貨日期"><input {...field('delivery_date')} type="date" /></Field>
        <Field error={validationErrors.product_name} label="品名" required><textarea {...field('product_name')} maxLength={500} required rows={2} /></Field>
        <Field error={validationErrors.order_quantity} label="訂單數量" required><input {...field('order_quantity')} inputMode="decimal" min="0.0001" required step="0.0001" type="number" /></Field>
        <Field label="訂單內容／規格補充"><textarea {...field('specification')} maxLength={4000} rows={2} /></Field>
        <Field label="單價" hint="小數點後兩位"><input {...field('unit_price')} inputMode="decimal" min="0" step="0.01" type="number" /></Field>
        <Field label="版費"><input {...field('plate_fee')} inputMode="decimal" min="0" step="0.01" type="number" /></Field>
        <Field label="刀模費"><input {...field('die_fee')} inputMode="decimal" min="0" step="0.01" type="number" /></Field>
      </div>
    </Section>
  </div>
}
