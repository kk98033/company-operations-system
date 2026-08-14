import { useState } from 'react'

import { downloadCsv, type CsvDataset } from '../api/operations'
import { getApiErrorMessage } from '../api/errorMessage'

export function CsvExportButton({ dataset }: { dataset: CsvDataset }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string>()
  async function download() {
    setPending(true)
    setError(undefined)
    try { await downloadCsv(dataset) } catch (reason) { setError(getApiErrorMessage(reason)) } finally { setPending(false) }
  }
  return <span className="csv-export"><button className="ui-button ui-button--secondary" disabled={pending} onClick={() => void download()} type="button">{pending ? '匯出中…' : '匯出 CSV'}</button>{error ? <span className="ui-inline-error" role="alert">{error}</span> : null}</span>
}
