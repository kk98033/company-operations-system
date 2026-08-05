import { useState } from 'react'

type PreviewStyle = 'industrial' | 'desktop' | 'bootstrap'

const styleChoices: Array<{
  id: PreviewStyle
  shortLabel: string
  name: string
  description: string
}> = [
  {
    id: 'industrial',
    shortLabel: 'A',
    name: '平面工業 ERP',
    description: '硬邊界、無陰影、資訊密集，適合長時間處理工單。',
  },
  {
    id: 'desktop',
    shortLabel: 'B',
    name: '現代桌面 ERP',
    description: '上方選單與工作頁籤，保留舊系統熟悉的操作感。',
  },
  {
    id: 'bootstrap',
    shortLabel: 'C',
    name: 'Bootstrap 企業版',
    description: '標準企業網頁結構，元件中性、容易理解與維護。',
  },
]

const sampleOrders = [
  {
    orderNo: 'WO-260805-001',
    customer: '範例客戶甲',
    product: '彩盒外包裝',
    quantity: '1,000',
    process: '四色印刷',
    dueDate: '08/08',
    status: '印刷中',
    tone: 'working',
  },
  {
    orderNo: 'WO-260805-002',
    customer: '範例客戶乙',
    product: '產品說明卡',
    quantity: '2,500',
    process: '裁切',
    dueDate: '08/09',
    status: '待加工',
    tone: 'waiting',
  },
  {
    orderNo: 'WO-260804-006',
    customer: '範例客戶丙',
    product: '食品包裝貼紙',
    quantity: '5,000',
    process: '品檢',
    dueDate: '08/07',
    status: '即將逾期',
    tone: 'urgent',
  },
  {
    orderNo: 'WO-260804-003',
    customer: '範例客戶甲',
    product: '活動邀請卡',
    quantity: '800',
    process: '已完成',
    dueDate: '08/06',
    status: '待入庫',
    tone: 'done',
  },
]

function OrderTable({ variant }: { variant: PreviewStyle }) {
  return (
    <div className={`preview-table-wrap preview-table-wrap--${variant}`}>
      <table className="preview-table">
        <caption>假資料工單清單</caption>
        <thead>
          <tr>
            <th scope="col">工單號</th>
            <th scope="col">客戶</th>
            <th scope="col">品名</th>
            <th scope="col" className="preview-table__number">數量</th>
            <th scope="col">目前製程</th>
            <th scope="col">交期</th>
            <th scope="col">狀態</th>
          </tr>
        </thead>
        <tbody>
          {sampleOrders.map((order) => (
            <tr key={order.orderNo}>
              <td className="preview-table__order">{order.orderNo}</td>
              <td>{order.customer}</td>
              <td>{order.product}</td>
              <td className="preview-table__number">{order.quantity}</td>
              <td>{order.process}</td>
              <td>{order.dueDate}</td>
              <td>
                <span className={`preview-status preview-status--${order.tone}`}>
                  {order.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function IndustrialPreview() {
  return (
    <div className="concept concept--industrial" aria-label="平面工業 ERP 預覽">
      <header className="industrial-bar">
        <div>
          <span className="industrial-bar__system">UV PRINT / OPERATIONS</span>
          <strong>工單生產看板</strong>
        </div>
        <div className="industrial-bar__meta">
          <span>2026.08.05</span>
          <span>本機假資料</span>
          <span>操作員：測試</span>
        </div>
      </header>
      <div className="industrial-workspace">
        <nav className="industrial-rail" aria-label="工業 ERP 模組">
          <strong>作業模組</strong>
          <a className="is-active" href="#industrial-orders">工單管理</a>
          <a href="#industrial-orders">生產進度</a>
          <a href="#industrial-orders">庫存出貨</a>
          <a href="#industrial-orders">計價請款</a>
          <a href="#industrial-orders">主檔設定</a>
        </nav>
        <section className="industrial-main" id="industrial-orders">
          <div className="industrial-title-row">
            <div>
              <span className="industrial-kicker">PRODUCTION / WORK ORDERS</span>
              <h2>工單生產看板</h2>
            </div>
            <div className="industrial-actions">
              <button type="button">匯出</button>
              <button className="is-primary" type="button">＋ 新增工單</button>
            </div>
          </div>
          <div className="industrial-metrics" aria-label="工單摘要">
            <div><span>進行中</span><strong>18</strong></div>
            <div><span>今日到期</span><strong>4</strong></div>
            <div><span>待入庫</span><strong>7</strong></div>
            <div className="is-alert"><span>異常／逾期</span><strong>2</strong></div>
          </div>
          <div className="industrial-filter">
            <label>快速查詢<input type="search" placeholder="工單號／客戶／品名" /></label>
            <label>製程<select defaultValue="all"><option value="all">全部製程</option></select></label>
            <label>交期<select defaultValue="week"><option value="week">本週</option></select></label>
            <button type="button">查詢</button>
            <button className="is-quiet" type="button">清除</button>
          </div>
          <OrderTable variant="industrial" />
          <footer className="industrial-footer">
            <span>顯示 1–4，共 31 筆</span>
            <span>最後更新 14:32</span>
          </footer>
        </section>
      </div>
    </div>
  )
}

function DesktopPreview() {
  return (
    <div className="concept concept--desktop" aria-label="現代桌面 ERP 預覽">
      <header className="desktop-titlebar">
        <strong>公司生產管理系統</strong>
        <span>本機測試環境 — 假資料</span>
      </header>
      <nav className="desktop-menu" aria-label="桌面 ERP 功能選單">
        <button type="button"><u>檔</u>案</button>
        <button type="button"><u>主</u>檔</button>
        <button type="button"><u>工</u>單作業</button>
        <button type="button"><u>出</u>貨作業</button>
        <button type="button"><u>帳</u>務作業</button>
        <button type="button"><u>報</u>表</button>
        <button type="button"><u>系</u>統</button>
      </nav>
      <div className="desktop-toolbar" aria-label="常用功能">
        <button type="button">新增</button>
        <button type="button">查詢</button>
        <button type="button">重新整理</button>
        <span />
        <button type="button">列印</button>
        <button type="button">匯出</button>
      </div>
      <div className="desktop-tabs" role="tablist" aria-label="已開啟作業">
        <button type="button" role="tab">首頁</button>
        <button className="is-active" type="button" role="tab" aria-selected="true">工單作業清單 ×</button>
      </div>
      <main className="desktop-main">
        <div className="desktop-heading">
          <div><span>作業代號：WO-01</span><h2>工單作業清單</h2></div>
          <span>資料日期：2026/08/05</span>
        </div>
        <fieldset className="desktop-query">
          <legend>查詢條件</legend>
          <label>工單日期<input defaultValue="2026/08/01" /></label>
          <span>至</span>
          <label className="desktop-query__end"><span className="sr-label">結束日期</span><input defaultValue="2026/08/05" /></label>
          <label>客戶簡稱<input placeholder="輸入關鍵字" /></label>
          <label>狀態<select defaultValue="open"><option value="open">未結案</option></select></label>
          <button type="button">執行查詢</button>
        </fieldset>
        <div className="desktop-section-title">
          <strong>查詢結果</strong>
          <span>共 31 筆；目前顯示 4 筆假資料</span>
        </div>
        <OrderTable variant="desktop" />
      </main>
      <footer className="desktop-statusbar">
        <span>就緒</span><span>使用者：TEST</span><span>資料庫：LOCAL</span><span>2026/08/05 14:32</span>
      </footer>
    </div>
  )
}

function BootstrapPreview() {
  return (
    <div className="concept concept--bootstrap" aria-label="Bootstrap 企業版預覽">
      <header className="bs-navbar">
        <strong>Company ERP</strong>
        <nav aria-label="Bootstrap 企業版導覽">
          <a href="#bs-orders">儀表板</a>
          <a className="is-active" href="#bs-orders">工單</a>
          <a href="#bs-orders">生產</a>
          <a href="#bs-orders">出貨</a>
          <a href="#bs-orders">帳務</a>
        </nav>
        <span>測試使用者</span>
      </header>
      <main className="bs-main" id="bs-orders">
        <div className="bs-breadcrumb">首頁 / 生產管理 / <strong>工單</strong></div>
        <div className="bs-heading">
          <div><h2>工單管理</h2><p>查詢、追蹤與建立生產工單</p></div>
          <button className="bs-button bs-button--primary" type="button">新增工單</button>
        </div>
        <section className="bs-card bs-filter-card">
          <div className="bs-card__header"><strong>篩選條件</strong></div>
          <div className="bs-card__body">
            <label>關鍵字<input type="search" placeholder="工單號、客戶或品名" /></label>
            <label>狀態<select defaultValue="active"><option value="active">進行中</option></select></label>
            <label>交期<select defaultValue="week"><option value="week">本週</option></select></label>
            <button className="bs-button bs-button--primary" type="button">搜尋</button>
            <button className="bs-button" type="button">重設</button>
          </div>
        </section>
        <section className="bs-card">
          <div className="bs-card__header bs-card__header--split">
            <strong>工單清單</strong><span>共 31 筆</span>
          </div>
          <OrderTable variant="bootstrap" />
          <div className="bs-card__footer"><span>顯示第 1–4 筆</span><button className="bs-button" type="button">下一頁</button></div>
        </section>
      </main>
    </div>
  )
}

export function StylePreviewPage() {
  const [activeStyle, setActiveStyle] = useState<PreviewStyle>('industrial')
  const selected = styleChoices.find((choice) => choice.id === activeStyle) ?? styleChoices[0]

  return (
    <div className="style-preview-page">
      <header className="style-preview-heading">
        <div>
          <p className="eyebrow">Phase 0 · Design Review</p>
          <h1>介面風格比較</h1>
          <p>三個提案使用相同假工單資料。先比較資訊排列與操作密度，選定後才套用到正式頁面。</p>
        </div>
        <span className="style-preview-heading__notice">僅供視覺評估 · 無真實資料</span>
      </header>

      <div className="style-switcher" role="group" aria-label="選擇介面風格">
        {styleChoices.map((choice) => (
          <button
            className={choice.id === activeStyle ? 'is-active' : undefined}
            key={choice.id}
            type="button"
            aria-pressed={choice.id === activeStyle}
            onClick={() => setActiveStyle(choice.id)}
          >
            <span>{choice.shortLabel}</span>
            <strong>{choice.name}</strong>
            <small>{choice.description}</small>
          </button>
        ))}
      </div>

      <div className="style-preview-selection" aria-live="polite">
        <strong>目前顯示：{selected.shortLabel}．{selected.name}</strong>
        <span>{selected.description}</span>
      </div>

      {activeStyle === 'industrial' && <IndustrialPreview />}
      {activeStyle === 'desktop' && <DesktopPreview />}
      {activeStyle === 'bootstrap' && <BootstrapPreview />}
    </div>
  )
}
