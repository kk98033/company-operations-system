import { Link } from '@tanstack/react-router'

export function RouteErrorPage() {
  return (
    <main className="system-message" role="alert">
      <div className="system-message__card">
        <p className="eyebrow">系統錯誤</p>
        <h1>頁面載入失敗</h1>
        <p>系統無法完成這次頁面導覽，請回到首頁後再試一次。</p>
        <Link className="button button--primary" to="/">
          回到首頁
        </Link>
      </div>
    </main>
  )
}
