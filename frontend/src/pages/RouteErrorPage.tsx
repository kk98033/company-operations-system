import { Link } from '@tanstack/react-router'

import { SystemState } from '../ui/UiPatterns'

export function RouteErrorPage() {
  return (
    <SystemState
      action={<Link className="ui-button ui-button--primary" to="/">回到首頁</Link>}
      code="ERR"
      description="系統無法完成這次頁面導覽，請回到首頁後再試一次。若問題持續發生，請記錄發生時間。"
      eyebrow="SYSTEM / ROUTE ERROR"
      fullPage
      role="alert"
      title="頁面載入失敗"
    />
  )
}
