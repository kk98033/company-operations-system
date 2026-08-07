import { Field, Section, StatusLabel } from '../../ui/UiPatterns'

const processNames = [
  '美工', '輸出', '製版', '打樣', '印刷', '上光', '裱紙',
  '模具', '軋型', '加工', '糊邊', '運送', '其他',
] as const

function ProcessRow({ name }: { name: (typeof processNames)[number] }) {
  return (
    <fieldset className="work-order-process-row">
      <legend>{name}</legend>
      <Field label="協力廠">
        <input list="demo-process-vendors" placeholder="搜尋協力廠" />
      </Field>
      <Field label="製程說明">
        <input placeholder={`輸入${name}規格或交接事項`} />
      </Field>
      {name === '製版' ? (
        <div className="work-order-process-options work-order-process-options--pending">
          新版／舊版、天地／左右輪轉的關係與必填規則待 P0-08 確認
        </div>
      ) : null}
      {name === '上光' ? (
        <Field label="上光種類"><input placeholder="輸入或選擇上光種類" /></Field>
      ) : null}
      {name === '軋型' ? (
        <div className="work-order-process-extras">
          <Field label="刀模號碼"><input /></Field>
          <Field label="模數"><input inputMode="numeric" /></Field>
        </div>
      ) : null}
      {name === '糊邊' ? (
        <div className="work-order-process-options" role="group" aria-label="糊邊包裝方式">
          {['裝箱', '裝袋'].map((option) => (
            <label key={option}><input name="packing-option" type="radio" /><span>{option}</span></label>
          ))}
        </div>
      ) : null}
    </fieldset>
  )
}

export function ProcessPlanningSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-process" tabIndex={-1}>
      <Section
        title="製程規劃"
        description="本區保存工單預定製程；開始、完成、重開及最終完工仍由後續生產管理追蹤。"
        actions={<StatusLabel tone="warning">製版欄位待 P0-08 確認</StatusLabel>}
      >
        <datalist id="demo-process-vendors">
          <option value="範例協力廠（假資料）" />
        </datalist>
        <div className="work-order-process-list">
          {processNames.map((name) => <ProcessRow key={name} name={name} />)}
        </div>
      </Section>
    </div>
  )
}
