import { Field, Section, StatusLabel } from '../../ui/UiPatterns'

export function WorkOrderBasicSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-basic" tabIndex={-1}>
      <Section
        title="客戶與訂單資料"
        description="選取客編後帶入客戶資料；一張工單只對應一個主要品項並隸屬一個案件。工單號格式為 WO-YYYYMMDD-SSS，實際必填規則將在功能啟用前逐欄驗收。"
        actions={<StatusLabel tone="success">一工單一主要品項已確認</StatusLabel>}
      >
        <div className="work-order-prototype__basic-grid">
          <Field label="客編">
            <input placeholder="輸入代號或名稱查詢" />
          </Field>
          <Field label="客名">
            <input placeholder="選取客編後帶入" readOnly />
          </Field>
          <Field label="客戶單號">
            <input />
          </Field>
          <Field label="電話">
            <input placeholder="選取客編後帶入" readOnly />
          </Field>
          <Field label="聯絡人">
            <input placeholder="選取客編後帶入" readOnly />
          </Field>
          <Field label="地址">
            <input placeholder="選取客編後帶入" readOnly />
          </Field>
          <Field label="工作單號" hint="正式格式：WO-YYYYMMDD-SSS">
            <input placeholder="存檔時產生" readOnly />
          </Field>
          <Field label="訂購日期">
            <input type="date" />
          </Field>
          <Field label="交貨日期">
            <input type="date" />
          </Field>
          <Field label="品名">
            <textarea rows={2} />
          </Field>
          <Field label="訂單數量">
            <input inputMode="numeric" />
          </Field>
          <Field label="訂單內容／規格補充">
            <textarea placeholder="例如：交貨正負量或包裝說明" rows={2} />
          </Field>
          <Field label="單價" hint="顯示至小數點後兩位">
            <input inputMode="decimal" placeholder="0.00" />
          </Field>
          <Field label="版費">
            <input inputMode="decimal" placeholder="0.00" />
          </Field>
          <Field label="刀模費">
            <input inputMode="decimal" placeholder="0.00" />
          </Field>
        </div>
      </Section>
    </div>
  )
}
