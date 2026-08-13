import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import { ErrorBoundary } from './app/ErrorBoundary'
import { AppProviders } from './app/providers'
import './styles/tokens.css'
import './styles/global.css'
import './styles/layout.css'
// ADR-010 cascade：頁面結構 → 表單 → 資訊 → 系統狀態 → 版型示範。
import './styles/ui-page-patterns.css'
import './styles/ui-form-patterns.css'
import './styles/ui-information-patterns.css'
import './styles/ui-system-state.css'
import './styles/ui-pattern-gallery.css'
import './styles/api-connection-status.css'
import './styles/audit-log.css'
import './styles/company-profile.css'
import './styles/organization-settings.css'
import './styles/customers.css'
import './styles/master-data.css'
import './styles/quotations.css'
import './styles/login.css'
import './styles/module-prototype.css'
import './styles/work-order-prototype.css'
import './styles/production.css'
// 歷史比較頁是正式 UI 之外的唯一例外，必須最後載入且不可供 feature 使用。
import './styles/style-preview.css'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('找不到 React 掛載點 #root')
}

createRoot(rootElement).render(
  <StrictMode>
    <ErrorBoundary>
      <AppProviders>
        <App />
      </AppProviders>
    </ErrorBoundary>
  </StrictMode>,
)
