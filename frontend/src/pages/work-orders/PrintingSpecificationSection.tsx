import { Field, Section } from '../../ui/UiPatterns'

const processColors = ['C', 'M', 'Y', 'K'] as const

function ColorSide({ side }: { side: '正面' | '反面' }) {
  return (
    <fieldset className="work-order-color-side">
      <legend>印刷－{side}</legend>
      <Field label={`${side}色數`}>
        <input inputMode="numeric" placeholder="0" />
      </Field>
      <div className="work-order-color-options" role="group" aria-label={`${side} CMYK`}>
        {processColors.map((color) => (
          <label key={color}>
            <input type="checkbox" />
            <span>{color}</span>
          </label>
        ))}
      </div>
      <Field label={`${side}特別色`}>
        <textarea placeholder="輸入潘通色號或特別色說明" rows={3} />
      </Field>
    </fieldset>
  )
}

export function PrintingSpecificationSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-printing" tabIndex={-1}>
      <Section
        title="印刷"
        description="保留工單內的 CMYK 與特別色規格；系統不再建立獨立色別設定功能。"
      >
        <div className="work-order-print-summary">
          <Field label="印刷長度">
            <input inputMode="decimal" placeholder="0" />
          </Field>
          <Field label="印刷寬度">
            <input inputMode="decimal" placeholder="0" />
          </Field>
          <Field label="K 數">
            <input inputMode="numeric" placeholder="0" />
          </Field>
          <Field label="模數">
            <input inputMode="numeric" placeholder="0" />
          </Field>
          <Field label="印刷數量">
            <input inputMode="numeric" />
          </Field>
          <Field label="加減量／±量">
            <input inputMode="numeric" placeholder="± 0" />
          </Field>
        </div>
        <div className="work-order-color-grid">
          <ColorSide side="正面" />
          <ColorSide side="反面" />
        </div>
        <div className="work-order-print-summary">
          <Field label="合計色數">
            <input inputMode="numeric" placeholder="0" />
          </Field>
        </div>
      </Section>
    </div>
  )
}
