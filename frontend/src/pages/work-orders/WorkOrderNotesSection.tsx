import { Field, Section } from '../../ui/UiPatterns'

export function WorkOrderNotesSection() {
  return (
    <div className="work-order-prototype__anchor" id="work-order-notes" tabIndex={-1}>
      <Section
        title="備註與圖片"
        description="長文字與刀模圖屬於同一張工單；正式附件會使用私人儲存與權限下載。"
      >
        <div className="work-order-notes-grid">
          <Field label="工單備註" hint="至少可輸入 150 字；正式上限待公司確認">
            <textarea placeholder="輸入工單整體交接事項" rows={10} />
          </Field>
          <fieldset className="work-order-attachment-placeholder">
            <legend>圖片附件</legend>
            <div aria-label="刀模圖預覽區" role="img">刀模圖／成品參考圖預覽區</div>
            <button className="ui-button ui-button--secondary" disabled type="button">選擇圖片（Phase 4 實作）</button>
          </fieldset>
        </div>
      </Section>
    </div>
  )
}
