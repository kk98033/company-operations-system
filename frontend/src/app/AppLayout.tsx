import { useState } from 'react'
import { Link, Outlet } from '@tanstack/react-router'

const navigation = [
  { to: '/', icon: '▦', label: '首頁', exact: true },
  { to: '/ui-patterns', icon: 'UI', label: '統一 UI 版型', exact: false },
  { to: '/style-preview', icon: 'Aa', label: '設計比較紀錄', exact: false },
] as const

export function AppLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className={`app-shell${isCollapsed ? ' app-shell--collapsed' : ''}`}>
      <a className="skip-link" href="#main-content">跳到主要內容</a>

      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__mark" aria-hidden="true">UV</span>
          <div className="sidebar__brand-copy">
            <strong>公司管理系統</strong>
            <span>OPERATIONS ERP</span>
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="主要導覽">
          <p className="sidebar__section-label">工作區</p>
          {navigation.map((item) => (
            <Link
              activeOptions={{ exact: item.exact }}
              activeProps={{ className: 'sidebar__link--active' }}
              className="sidebar__link"
              key={item.to}
              to={item.to}
            >
              <span className="sidebar__link-icon" aria-hidden="true">{item.icon}</span>
              <span className="sidebar__link-label">{item.label}</span>
            </Link>
          ))}

          <p className="sidebar__section-label sidebar__section-label--modules">預定模組</p>
          <div className="sidebar__placeholder"><span aria-hidden="true">客</span><span className="sidebar__link-label">客戶與報價</span></div>
          <div className="sidebar__placeholder"><span aria-hidden="true">工</span><span className="sidebar__link-label">工單與生產</span></div>
          <div className="sidebar__placeholder"><span aria-hidden="true">出</span><span className="sidebar__link-label">庫存與出貨</span></div>
          <div className="sidebar__placeholder"><span aria-hidden="true">帳</span><span className="sidebar__link-label">計價與請款</span></div>
        </nav>

        <div className="sidebar__footer">
          <span className="status-dot" aria-hidden="true" />
          <span className="sidebar__link-label">本機服務運作中</span>
        </div>
      </aside>

      <div className="app-shell__workspace">
        <header className="topbar">
          <div className="topbar__left">
            <button
              aria-label={isCollapsed ? '展開側邊欄' : '收合側邊欄'}
              className="topbar__sidebar-toggle"
              onClick={() => setIsCollapsed((value) => !value)}
              type="button"
            >
              <span aria-hidden="true">☰</span>
            </button>
            <div><span className="topbar__label">目前環境</span><strong>本機開發</strong></div>
          </div>
          <div className="topbar__account" aria-label="使用者狀態">
            <div><strong>測試使用者</strong><span>登入功能尚未建立</span></div>
            <span className="topbar__avatar" aria-hidden="true">測</span>
          </div>
        </header>

        <main className="page" id="main-content" tabIndex={-1}><Outlet /></main>
      </div>
    </div>
  )
}
