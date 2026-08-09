import { Link } from '@tanstack/react-router'

import { SystemState } from '../ui/UiPatterns'

export function NotFoundPage() {
  return (
    <SystemState
      action={<Link className="ui-button ui-button--primary" to="/">回到首頁</Link>}
      code="404"
      description="這個網址不存在，或功能尚未開放。請由左側模組導覽重新進入作業。"
      eyebrow="ROUTE / NOT FOUND"
      fullPage
      title="找不到這個頁面"
    />
  )
}
