import { PageHeader, StatusLabel } from '../../ui/UiPatterns'
import { PaperPreparationSection } from './PaperPreparationSection'
import { PrintingSpecificationSection } from './PrintingSpecificationSection'
import { ProcessPlanningSection } from './ProcessPlanningSection'
import { WorkOrderBasicSection } from './WorkOrderBasicSection'
import { WorkOrderNotesSection } from './WorkOrderNotesSection'

const sections = [
  ['basic', '客戶與訂單'],
  ['paper', '備紙'],
  ['printing', '印刷'],
  ['process', '製程'],
  ['notes', '備註與圖片'],
] as const

type PrototypeAction = {
  label: string
  tone?: 'primary' | 'secondary'
  disabled: true
}

const prototypeActions: PrototypeAction[] = [
  { label: '另存新檔', disabled: true },
  { label: '存檔', tone: 'primary' as const, disabled: true },
  { label: '取消', disabled: true },
  { label: '列印', disabled: true },
]

function PrototypeFooterActions() {
  return (
    <footer className="ui-form-footer work-order-prototype__footer">
      <span>目前為展示資料；操作按鈕尚未連接 API、資料庫與正式列印。</span>
      <div>
        {prototypeActions.map((action) => (
          <button
            className={`ui-button ui-button--${action.tone ?? 'secondary'}`}
            disabled
            key={action.label}
            type="button"
          >
            {action.label}
          </button>
        ))}
      </div>
    </footer>
  )
}

export function WorkOrderPrototypePage() {
  return (
    <form
      aria-label="工單整合建檔展示"
      className="ui-pattern-stack work-order-prototype"
      onSubmit={(event) => event.preventDefault()}
    >
      <PageHeader
        actions={prototypeActions}
        description="客戶、訂單、備紙、印刷、製程、備註與圖片集中在同一張工單；生產管理只負責存檔後的實際執行追蹤。"
        eyebrow="工單管理 / 建檔展示"
        title="工單建檔作業"
      />

      <div className="module-prototype__notice" role="status">
        <StatusLabel tone="warning">展示資料／尚未連接正式資料</StatusLabel>
        <span>本版依公司工單 PDF 的欄位、分區、順序與單頁流程整理，採現代化 RWD 呈現而非複製 XP 外觀；目前不會存檔、列印或載入公司正式資料。</span>
      </div>

      <nav className="work-order-prototype__section-nav" aria-label="工單頁內區段">
        {sections.map(([id, label]) => (
          <a
            href={`#work-order-${id}`}
            key={id}
            onClick={() => document.getElementById(`work-order-${id}`)?.focus()}
          >
            {label}
          </a>
        ))}
      </nav>

      <WorkOrderBasicSection />
      <PaperPreparationSection />
      <PrintingSpecificationSection />
      <ProcessPlanningSection />
      <WorkOrderNotesSection />
      <PrototypeFooterActions />
    </form>
  )
}
