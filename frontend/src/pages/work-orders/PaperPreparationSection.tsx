import { Field, Section, StatusLabel } from '../../ui/UiPatterns'
import type { PaperDraft } from './workOrderDraft'

const labels = { face: '面紙', back: '底紙', flute: '浪紙' } as const
type Props = { papers: PaperDraft[]; editable: boolean; onChange: (index: number, field: keyof PaperDraft, value: string) => void }

export function PaperPreparationSection({ papers, editable, onChange }: Props) {
  return <div className="work-order-prototype__anchor" id="work-order-paper" tabIndex={-1}>
    <Section title="備紙" description="面紙、底紙有廠別；浪紙依公司新稿不設廠別。" actions={<StatusLabel tone="success">公司稿三紙結構</StatusLabel>}>
      <div className="work-order-paper-grid">{papers.map((paper, index) => {
        const input = (field: keyof PaperDraft) => ({ disabled: !editable, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(index, field, event.target.value), value: paper[field] })
        return <fieldset className="work-order-paper-group" key={paper.type}><legend>{labels[paper.type]}</legend>
          <Field label="供應商"><input {...input('vendor')} placeholder="搜尋或輸入供應商" /></Field>
          <Field label="紙質"><input {...input('paper')} /></Field>
          {paper.type !== 'flute' ? <Field label="廠別"><input {...input('mill')} /></Field> : null}
          <Field label="尺寸"><input {...input('size')} /></Field>
          <Field label="數量"><input {...input('quantity')} inputMode="decimal" min="0" type="number" /></Field>
          <Field label={`${labels[paper.type]}備註`}><textarea {...input('note')} rows={3} /></Field>
        </fieldset>
      })}</div>
    </Section>
  </div>
}
