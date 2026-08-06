import { useQuery } from '@tanstack/react-query'

import { getApiErrorMessage } from '../api/errorMessage'
import { getApiReadiness } from '../api/health'
import { StatusLabel } from '../ui/UiPatterns'

export function ApiConnectionStatus() {
  const readiness = useQuery({
    queryKey: ['api', 'health', 'ready'],
    queryFn: getApiReadiness,
    retry: false,
  })

  if (readiness.isPending) {
    return (
      <div className="api-connection-status" role="status">
        <StatusLabel tone="working">檢查中</StatusLabel>
        <span>正在確認 API 與必要相依服務。</span>
      </div>
    )
  }

  if (readiness.isError) {
    return (
      <div className="api-connection-status" role="alert">
        <StatusLabel tone="warning">未就緒</StatusLabel>
        <span>{getApiErrorMessage(readiness.error)}</span>
        <button
          className="ui-button ui-button--secondary"
          onClick={() => readiness.refetch()}
          type="button"
        >
          重新檢查
        </button>
      </div>
    )
  }

  return (
    <div className="api-connection-status" role="status">
      <StatusLabel tone="success">已連線</StatusLabel>
      <span>API 與必要相依服務目前可使用。</span>
    </div>
  )
}
