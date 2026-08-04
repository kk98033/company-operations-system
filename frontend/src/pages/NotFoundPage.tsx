import { Link } from '@tanstack/react-router'

export function NotFoundPage() {
  return (
    <section className="empty-state">
      <p className="eyebrow">404</p>
      <h1>找不到這個頁面</h1>
      <p>這個網址不存在，或功能尚未開放。</p>
      <Link className="button button--primary" to="/">
        回到首頁
      </Link>
    </section>
  )
}
