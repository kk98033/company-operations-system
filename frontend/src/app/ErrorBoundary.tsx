import { Component, type ErrorInfo, type ReactNode } from 'react'

import { SystemState } from '../ui/UiPatterns'

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  public state: ErrorBoundaryState = { hasError: false }

  public static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Phase 0 先留在 console；未來接入結構化錯誤紀錄時改由統一 service 上報。
    console.error('React render error', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <SystemState
          action={(
            <button
              className="ui-button ui-button--primary"
              onClick={() => location.reload()}
              type="button"
            >
              重新載入
            </button>
          )}
          code="ERR"
          description="請重新載入頁面。若問題持續發生，請將發生時間提供給系統維護者。"
          eyebrow="SYSTEM / RENDER ERROR"
          fullPage
          role="alert"
          title="頁面無法顯示"
        />
      )
    }

    return this.props.children
  }
}
