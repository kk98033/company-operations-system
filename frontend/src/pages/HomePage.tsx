export function HomePage() {
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Phase 0 · 工程基礎</p>
          <h1>首頁</h1>
          <p className="page-header__description">
            前端路由、資料查詢 provider 與桌面版操作殼層已建立。
          </p>
        </div>
        <span className="status-badge status-badge--neutral">尚無正式資料</span>
      </header>

      <section className="content-grid" aria-label="專案骨架狀態">
        <article className="panel panel--primary">
          <p className="eyebrow">目前成果</p>
          <h2>可執行的前端骨架</h2>
          <p>
            這個版本只驗證建置與導覽基礎，尚未實作客戶、工單、出貨或帳務功能。
          </p>
          <ul className="check-list">
            <li>TanStack Router 首頁與 404 路由</li>
            <li>TanStack Query 共用 Provider</li>
            <li>頁面與路由錯誤邊界</li>
            <li>桌面版側欄、頂列與 Design Tokens</li>
          </ul>
        </article>

        <aside className="panel">
          <p className="eyebrow">開發約束</p>
          <h2>依小切片驗證</h2>
          <p>
            所有業務頁面必須依最終實作計畫逐步加入，每次完成後執行測試、更新進度並建立 Git 紀錄。
          </p>
        </aside>
      </section>
    </>
  )
}
