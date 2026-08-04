import { Component, type ErrorInfo, type ReactNode } from 'react'

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
        <main className="system-message" role="alert">
          <div className="system-message__card">
            <p className="eyebrow">系統錯誤</p>
            <h1>頁面無法顯示</h1>
            <p>
              請重新載入頁面。若問題持續發生，請將發生時間提供給系統維護者。
            </p>
            <button className="button button--primary" onClick={() => location.reload()}>
              重新載入
            </button>
          </div>
        </main>
      )
    }

    return this.props.children
  }
}
