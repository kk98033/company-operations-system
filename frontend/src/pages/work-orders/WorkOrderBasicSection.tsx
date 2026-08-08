import { Field, Section, StatusLabel } from '../../ui/UiPatterns'

export function WorkOrderBasicSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-basic" tabIndex={-1}>
      <Section
        title="客戶與訂單資料"
        description="選取客編後帶入客戶資料；一張工單只對應一個主要品項並隸屬一個案件。正式工單號已定為 WO-YYYYMMDD-SSS，本頁仍是未連接 API 的假資料原型。"
        actions={<StatusLabel tone="success">一工單一主要品項已確認</StatusLabel>}
      >
        <div className="work-order-prototype__basic-grid">
          <Field label="客編" required>
            <input defaultValue="DEMO-C001" placeholder="輸入代號或名稱查詢" />
          </Field>
          <Field label="客名">
            <input defaultValue="範例客戶（假資料）" readOnly />
          </Field>
          <Field label="客戶單號">
            <input defaultValue="PO-DEMO-001" />
          </Field>
          <Field label="電話">
            <input defaultValue="04-0000-0000" readOnly />
          </Field>
          <Field label="聯絡人">
            <input defaultValue="王小姐（假資料）" readOnly />
          </Field>
          <Field label="地址">
            <input defaultValue="示範地址，不是真實公司資料" readOnly />
          </Field>
          <Field label="工作單號" required hint="正式格式：WO-YYYYMMDD-SSS">
            <input defaultValue="WO-20260808-001（假資料）" readOnly />
          </Field>
          <Field label="訂購日期" required>
            <input defaultValue="2026-08-07" type="date" />
          </Field>
          <Field label="交貨日期" required>
            <input defaultValue="2026-08-14" type="date" />
          </Field>
          <Field label="品名" required>
            <textarea defaultValue="彩盒外包裝（假資料）" rows={2} />
          </Field>
          <Field label="訂單數量" required>
            <input defaultValue="1000" inputMode="numeric" />
          </Field>
          <Field label="訂單內容／規格補充">
            <textarea placeholder="例如：交貨正負量或包裝說明" rows={2} />
          </Field>
          <Field label="單價" hint="顯示至小數點後兩位">
            <input defaultValue="0.00" inputMode="decimal" />
          </Field>
          <Field label="版費">
            <input defaultValue="0.00" inputMode="decimal" />
          </Field>
          <Field label="刀模費">
            <input defaultValue="0.00" inputMode="decimal" />
          </Field>
        </div>
      </Section>
    </div>
  )
}
