import { Link, Outlet } from '@tanstack/react-router'

export function AppLayout() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        跳到主要內容
      </a>

      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__mark" aria-hidden="true">
            公
          </span>
          <div>
            <strong>公司管理系統</strong>
            <span>本機測試環境</span>
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="主要導覽">
          <p className="sidebar__section-label">工作區</p>
          <Link
            className="sidebar__link"
            to="/"
            activeOptions={{ exact: true }}
            activeProps={{
              className: 'sidebar__link sidebar__link--active',
            }}
          >
            <span className="sidebar__link-icon" aria-hidden="true">
              ▦
            </span>
            首頁
          </Link>
        </nav>

        <div className="sidebar__footer">
          <span className="status-dot" aria-hidden="true" />
          工程骨架已啟動
        </div>
      </aside>

      <div className="app-shell__workspace">
        <header className="topbar">
          <div>
            <span className="topbar__label">目前環境</span>
            <strong>本機開發</strong>
          </div>
          <div className="topbar__account" aria-label="使用者狀態">
            <span className="topbar__avatar" aria-hidden="true">
              測
            </span>
            <div>
              <strong>測試使用者</strong>
              <span>尚未建立登入功能</span>
            </div>
          </div>
        </header>

        <main className="page" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
