import { useState } from 'react'

import {
  DataTableFrame,
  DefinitionGrid,
  Field,
  FilterBar,
  KpiStrip,
  PageHeader,
  Section,
  StatusLabel,
} from '../ui/UiPatterns'

type Pattern = 'overview' | 'list' | 'form' | 'detail'

const patterns: Array<{ id: Pattern; label: string; note: string }> = [
  { id: 'overview', label: '總覽', note: 'KPI 與待辦' },
  { id: 'list', label: '清單查詢', note: '篩選與表格' },
  { id: 'form', label: '新增／編輯', note: '分區表單' },
  { id: 'detail', label: '詳細資料', note: '唯讀與關聯' },
]

const sampleOrders = [
  ['WO-DEMO-001', '範例客戶甲', '彩盒外包裝', '1,000', '四色印刷', '2026-08-08', '印刷中', 'working'],
  ['WO-DEMO-002', '範例客戶乙', '產品說明卡', '2,500', '裁切', '2026-08-09', '待加工', 'neutral'],
  ['WO-DEMO-003', '範例客戶丙', '食品包裝貼紙', '5,000', '品檢', '2026-08-07', '即將逾期', 'danger'],
] as const

function OverviewPattern({ onOpenList }: { onOpenList: () => void }) {
  return (
    <div className="ui-pattern-stack">
      <PageHeader
        eyebrow="PRODUCTION / OVERVIEW"
        title="工單總覽版型"
        description="只有總覽頁放 KPI；新增、編輯與詳細資料頁不重複顯示統計卡。"
        actions={[
          { label: '查看全部工單', onClick: onOpenList },
          { label: '新增工單', tone: 'primary' },
        ]}
      />
      <KpiStrip
        label="工單摘要"
        items={[
          { label: '進行中', value: '18', hint: '較昨日 +2' },
          { label: '今日到期', value: '4', hint: '需優先確認', tone: 'warning' },
          { label: '待入庫', value: '7', hint: '已完成製程', tone: 'success' },
          { label: '異常／逾期', value: '2', hint: '需要處理', tone: 'danger' },
        ]}
      />
      <div className="ui-two-column">
        <Section title="今日優先處理" description="依交期、異常與後續流程排序。">
          <ul className="ui-work-list">
            <li><StatusLabel tone="danger">逾期</StatusLabel><strong>WO-DEMO-003</strong><span>品檢尚未完成</span><time>08/07</time></li>
            <li><StatusLabel tone="warning">今日</StatusLabel><strong>WO-DEMO-005</strong><span>等待完工核定</span><time>08/05</time></li>
            <li><StatusLabel tone="working">進行中</StatusLabel><strong>WO-DEMO-001</strong><span>四色印刷</span><time>08/08</time></li>
          </ul>
        </Section>
        <Section title="流程待辦" description="數字可連到對應清單並保留篩選條件。">
          <div className="ui-task-summary">
            <button type="button"><span>待完工核定</span><strong>3</strong></button>
            <button type="button"><span>待建立出貨單</span><strong>6</strong></button>
            <button type="button"><span>待計價</span><strong>9</strong></button>
            <button type="button"><span>待請款</span><strong>4</strong></button>
          </div>
        </Section>
      </div>
    </div>
  )
}

function ListPattern() {
  return (
    <div className="ui-pattern-stack">
      <PageHeader
        eyebrow="PRODUCTION / WORK ORDERS"
        title="工單清單版型"
        description="高頻查詢條件會自動換行；工單號固定在左側，重要欄位優先顯示。"
        actions={[{ label: '匯出結果' }, { label: '新增工單', tone: 'primary' }]}
      />
      <FilterBar>
        <Field label="快速查詢"><input type="search" placeholder="工單號／客戶／品名" /></Field>
        <Field label="狀態"><select defaultValue="active"><option value="active">進行中</option><option>全部</option></select></Field>
        <Field label="製程"><select defaultValue="all"><option value="all">全部製程</option></select></Field>
        <Field label="交期起日"><input type="date" defaultValue="2026-08-01" /></Field>
        <Field label="交期迄日"><input type="date" defaultValue="2026-08-31" /></Field>
        <div className="ui-filter-actions"><button className="ui-button ui-button--secondary" type="button">清除</button><button className="ui-button ui-button--primary" type="button">查詢</button></div>
      </FilterBar>
      <Section
        title="查詢結果"
        description="共 31 筆；目前為不含真實公司資料的版型示範。"
        actions={<button className="ui-text-button" type="button">設定顯示欄位</button>}
      >
        <DataTableFrame footer={<><span>顯示 1–3，共 31 筆</span><span>每頁 30 筆 · ‹ 1 / 2 ›</span></>}>
          <table className="ui-data-table">
            <caption className="visually-hidden">範例工單查詢結果</caption>
            <thead><tr><th className="ui-data-table__sticky" scope="col">工單號</th><th scope="col">客戶</th><th scope="col">品名</th><th className="ui-data-table__number" scope="col">數量</th><th scope="col">目前製程</th><th scope="col">交期</th><th scope="col">狀態</th><th scope="col">操作</th></tr></thead>
            <tbody>
              {sampleOrders.map((order) => (
                <tr key={order[0]}><th className="ui-data-table__sticky" scope="row"><button className="ui-table-link" type="button">{order[0]}</button></th><td>{order[1]}</td><td>{order[2]}</td><td className="ui-data-table__number">{order[3]}</td><td>{order[4]}</td><td>{order[5]}</td><td><StatusLabel tone={order[7]}>{order[6]}</StatusLabel></td><td><button className="ui-text-button" type="button">查看</button></td></tr>
              ))}
            </tbody>
          </table>
        </DataTableFrame>
      </Section>
    </div>
  )
}

function FormPattern() {
  return (
    <form className="ui-pattern-stack" onSubmit={(event) => event.preventDefault()}>
      <PageHeader eyebrow="PRODUCTION / WORK ORDERS / NEW" title="新增工單版型" description="欄位依工作流程分區，不顯示 KPI；主要儲存動作固定放在頁首與頁尾同一側。" actions={[{ label: '取消' }, { label: '儲存草稿' }, { label: '儲存工單', tone: 'primary' }]} />
      <Section title="基本資料" description="先選客戶，再填寫工單與交期資訊。">
        <div className="ui-form-grid">
          <Field label="客戶" required><select defaultValue=""><option value="" disabled>選擇客戶</option><option>範例客戶甲</option></select></Field>
          <Field label="工單日期" required><input type="date" defaultValue="2026-08-05" /></Field>
          <Field label="預計交期" required><input type="date" /></Field>
          <Field label="客戶訂單號"><input placeholder="例如：PO-DEMO-001" /></Field>
          <Field label="品名" required><input placeholder="輸入印件品名" /></Field>
          <Field label="生產數量" required hint="正式量與備品量會分欄保存。"><input inputMode="decimal" placeholder="0" /></Field>
          <Field label="業務備註"><textarea rows={3} placeholder="只填寫需要交接的資訊" /></Field>
        </div>
      </Section>
      <Section title="材料與印刷" description="複雜明細使用可增減列，不把所有欄位塞進同一行。">
        <div className="ui-inline-placeholder"><span>尚未新增材料明細</span><button className="ui-button ui-button--secondary" type="button">＋ 新增材料</button></div>
      </Section>
      <footer className="ui-form-footer"><span>＊ 為必填欄位</span><div><button className="ui-button ui-button--secondary" type="button">取消</button><button className="ui-button ui-button--primary" type="submit">儲存工單</button></div></footer>
    </form>
  )
}

function DetailPattern() {
  return (
    <div className="ui-pattern-stack">
      <PageHeader eyebrow="PRODUCTION / WORK ORDERS / WO-DEMO-001" title="工單 WO-DEMO-001" description="詳細頁以唯讀資訊和關聯流程為主，不複製總覽 KPI。" actions={[{ label: '列印' }, { label: '編輯工單', tone: 'primary' }]} />
      <div className="ui-detail-banner"><div><span>目前狀態</span><StatusLabel tone="working">印刷中</StatusLabel></div><div><span>客戶</span><strong>範例客戶甲</strong></div><div><span>預計交期</span><strong>2026-08-08</strong></div><div><span>生產數量</span><strong>1,000</strong></div></div>
      <div className="ui-two-column ui-two-column--detail">
        <Section title="工單資料"><DefinitionGrid items={[{ label: '品名', value: '彩盒外包裝' }, { label: '客戶訂單號', value: 'PO-DEMO-001' }, { label: '工單日期', value: '2026-08-05' }, { label: '建立者', value: '測試使用者' }, { label: '備註', value: '本頁全部為假資料版型。' }]} /></Section>
        <Section title="關聯作業" description="依實際流程顯示可以前往或尚未建立的單據。"><ol className="ui-process-list"><li className="is-done"><span>1</span><div><strong>工單已建立</strong><small>2026-08-05 09:30</small></div></li><li className="is-current"><span>2</span><div><strong>生產進行中</strong><small>目前：四色印刷</small></div></li><li><span>3</span><div><strong>最終完工核定</strong><small>尚未完成</small></div></li><li><span>4</span><div><strong>出貨與計價</strong><small>尚未建立</small></div></li></ol></Section>
      </div>
      <Section title="製程明細" description="事件與時間由後端稽核資料提供。"><div className="ui-inline-placeholder"><span>製程明細元件將在正式工單切片實作</span><button className="ui-text-button" type="button">查看版型規範</button></div></Section>
    </div>
  )
}

export function UiPatternsPage() {
  const [activePattern, setActivePattern] = useState<Pattern>('overview')

  return (
    <div className="ui-patterns-page">
      <section className="ui-pattern-intro" aria-labelledby="ui-pattern-title">
        <div><p className="eyebrow">UI BASELINE / ADR-010</p><h1 id="ui-pattern-title">統一 UI 版型</h1><p>A 的工業系統架構，加上 C 的表單留白與清晰度；B 只保留鍵盤操作與工作狀態的習慣。</p></div>
        <span>全部為假資料</span>
      </section>
      <nav className="ui-pattern-tabs" aria-label="通用版型">
        {patterns.map((pattern) => <button aria-current={activePattern === pattern.id ? 'page' : undefined} className={activePattern === pattern.id ? 'is-active' : ''} key={pattern.id} onClick={() => setActivePattern(pattern.id)} type="button"><strong>{pattern.label}</strong><small>{pattern.note}</small></button>)}
      </nav>
      <div className="ui-pattern-canvas">
        {activePattern === 'overview' ? <OverviewPattern onOpenList={() => setActivePattern('list')} /> : null}
        {activePattern === 'list' ? <ListPattern /> : null}
        {activePattern === 'form' ? <FormPattern /> : null}
        {activePattern === 'detail' ? <DetailPattern /> : null}
      </div>
    </div>
  )
}
