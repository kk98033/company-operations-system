import { Field, Section, StatusLabel } from '../../ui/UiPatterns'
import type { ProcessDraft } from './workOrderDraft'

type Props = { processes: ProcessDraft[]; editable: boolean; onChange: (index: number, field: keyof ProcessDraft, value: string) => void }

function ProcessRow({ process, index, editable, onChange }: { process: ProcessDraft; index: number; editable: boolean; onChange: Props['onChange'] }) {
  const input = (field: keyof ProcessDraft) => ({ 'data-error-key': `processes-${index}-${field}`, disabled: !editable, name: `processes-${index}-${field}`, onChange: (event: React.ChangeEvent<HTMLInputElement>) => onChange(index, field, event.target.value), value: process[field] })
  return <fieldset className="work-order-process-row"><legend>{process.name}</legend>
    <Field label="協力廠"><input {...input('vendor')} maxLength={200} placeholder="搜尋或輸入協力廠" /></Field>
    {process.code === 'plate' || process.code === 'gluing' ? <Field label="製程說明"><input {...input('content')} maxLength={2000} /></Field> : null}
    {process.code === 'plate' ? <div className="work-order-plate-options">
      <fieldset className="work-order-process-option-group"><legend>製版類型</legend><div className="work-order-process-options">{[['new','新版'],['existing','舊版']].map(([value,label]) => <label key={value}><input checked={process.plate_version === value} disabled={!editable} name={`plate-version-${index}`} onChange={() => onChange(index, 'plate_version', value)} type="radio" /><span>{label}</span></label>)}</div></fieldset>
      <fieldset className="work-order-process-option-group"><legend>輪轉方向</legend><div className="work-order-process-options">{[['top_bottom','天地輪轉'],['left_right','左右輪轉']].map(([value,label]) => <label key={value}><input checked={process.plate_rotation === value} disabled={!editable} name={`plate-rotation-${index}`} onChange={() => onChange(index, 'plate_rotation', value)} type="radio" /><span>{label}</span></label>)}</div></fieldset>
    </div> : null}
    {process.code === 'coating' ? <Field label="上光種類"><input {...input('coating_type')} maxLength={200} /></Field> : null}
    {process.code === 'die_cutting' ? <div className="work-order-process-extras"><Field label="刀模號碼"><input {...input('die_number')} maxLength={100} /></Field><Field label="模數"><input {...input('die_count')} min="0" type="number" /></Field></div> : null}
    {process.code === 'gluing' ? <div className="work-order-process-options" role="group" aria-label="糊邊包裝方式">{[['box','裝箱'],['bag','裝袋']].map(([value,label]) => <label key={value}><input checked={process.packing === value} disabled={!editable} name={`packing-${index}`} onChange={() => onChange(index, 'packing', value)} type="radio" /><span>{label}</span></label>)}</div> : null}
    {process.code !== 'plate' && process.code !== 'gluing' ? <Field label="製程說明"><input {...input('content')} maxLength={2000} /></Field> : null}
  </fieldset>
}

export function ProcessPlanningSection({ processes, editable, onChange }: Props) {
  return <div className="work-order-prototype__anchor" id="work-order-process" tabIndex={-1}>
    <Section title="製程規劃" description="建檔固定保存公司稿 13 道順序；開始、完成與重開留給生產管理。" actions={<StatusLabel tone="success">13 道建檔製程</StatusLabel>}>
      <div className="work-order-process-list">{processes.map((process, index) => <ProcessRow editable={editable} index={index} key={process.code} onChange={onChange} process={process} />)}</div>
    </Section>
  </div>
}
