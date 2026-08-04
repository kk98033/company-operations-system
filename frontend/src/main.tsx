import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import { ErrorBoundary } from './app/ErrorBoundary'
import { AppProviders } from './app/providers'
import './styles/tokens.css'
import './styles/global.css'
import './styles/layout.css'

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
