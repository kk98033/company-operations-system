import { useState, type MouseEvent } from 'react'
import { Link, Outlet } from '@tanstack/react-router'

import { workflowModules } from './workflowModules'

const developmentNavigation = [
  { to: '/ui-patterns', icon: 'UI', label: '統一 UI 版型', exact: false },
  { to: '/style-preview', icon: 'Aa', label: '設計比較紀錄', exact: false },
] as const

export function AppLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  function moveFocusToMain(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault()
    document.getElementById('main-content')?.focus()
  }

  return (
    <div className={`app-shell${isCollapsed ? ' app-shell--collapsed' : ''}`}>
      <a className="skip-link" href="#main-content" onClick={moveFocusToMain}>跳到主要內容</a>

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
          <Link
            activeOptions={{ exact: true }}
            activeProps={{ className: 'sidebar__link--active' }}
            className="sidebar__link"
            to="/"
          >
            <span className="sidebar__link-icon" aria-hidden="true">▦</span>
            <span className="sidebar__link-label">首頁</span>
          </Link>

          <p className="sidebar__section-label sidebar__section-label--modules">核心流程</p>
          {workflowModules.map((item) => (
            <Link
              activeOptions={{ exact: true }}
              activeProps={{ className: 'sidebar__link--active' }}
              className="sidebar__link"
              key={item.id}
              to={item.path}
            >
              <span className="sidebar__link-icon" aria-hidden="true">{item.icon}</span>
              <span className="sidebar__link-label">{item.label}</span>
            </Link>
          ))}

          <p className="sidebar__section-label sidebar__section-label--modules">開發基準</p>
          {developmentNavigation.map((item) => (
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
