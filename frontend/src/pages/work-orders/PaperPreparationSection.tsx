import { Field, Section, StatusLabel } from '../../ui/UiPatterns'

const paperGroups = [
  { id: 'face', label: '面紙', millLabel: '廠別' },
  { id: 'back', label: '底紙', millLabel: '廠別' },
  { id: 'flute', label: '浪紙', millLabel: '尺寸' },
] as const

function PaperGroup({
  id,
  label,
  millLabel,
}: (typeof paperGroups)[number]) {
  return (
    <fieldset className="work-order-paper-group">
      <legend>{label}</legend>
      <Field label="供應商">
        <input list="demo-paper-vendors" placeholder="搜尋供應商" />
      </Field>
      <Field label="紙質">
        <input placeholder="輸入或選擇紙質" />
      </Field>
      <Field label={millLabel}>
        <input aria-label={`${label}${millLabel}`} />
      </Field>
      {id !== 'flute' ? (
        <Field label="尺寸">
          <input placeholder="例如：31 × 43 吋" />
        </Field>
      ) : null}
      <Field label="數量">
        <input inputMode="numeric" placeholder="0" />
      </Field>
      <Field label={`${label}備註`}>
        <textarea placeholder="紙張方向、特殊規格或交接事項" rows={3} />
      </Field>
    </fieldset>
  )
}

export function PaperPreparationSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-paper" tabIndex={-1}>
      <Section
        title="備紙"
        description="面紙、底紙與浪紙同頁並列；供應商與紙質將由主檔搜尋，不另建裁紙設定頁。浪紙廠別在來源文件間有差異，原型不據此鎖定 schema。"
        actions={<StatusLabel tone="warning">浪紙欄位待確認</StatusLabel>}
      >
        <datalist id="demo-paper-vendors">
          <option value="範例紙行（假資料）" />
        </datalist>
        <div className="work-order-paper-grid">
          {paperGroups.map((group) => <PaperGroup key={group.id} {...group} />)}
        </div>
      </Section>
    </div>
  )
}
