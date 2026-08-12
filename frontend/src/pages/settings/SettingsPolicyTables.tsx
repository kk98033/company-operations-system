import type {
  DocumentNumberPolicyResponse,
  PrintPolicyResponse,
} from '../../api/generated/company-system'
import { Section, StatusLabel } from '../../ui/UiPatterns'

const resetLabels = { daily: '每日', monthly: '每月' } as const
const orientationLabels = { landscape: '橫向', portrait: '直向' } as const

export function NumberingPolicyTable({ policies }: { policies: DocumentNumberPolicyResponse[] }) {
  return (
    <Section
      title="單號規則"
      description="下列規則已由公司確認；前綴、日期區段與流水位數不可在此任意修改。"
    >
      <div className="ui-table-frame organization-policy-table">
        <table className="ui-data-table">
          <thead><tr><th scope="col">文件</th><th scope="col">顯示格式</th><th scope="col">流水重置</th><th scope="col">狀態</th></tr></thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.document_type}>
                <th scope="row">{policy.label}</th>
                <td><code>{policy.format}</code></td>
                <td>{resetLabels[policy.reset_period]}</td>
                <td><StatusLabel tone="success">公司已確認</StatusLabel></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="organization-settings-note">舊系統單號會原樣保留、標示並可搜尋；新號實際並行配發留在各文件切片。</p>
    </Section>
  )
}

export function PrintPolicyTable({ policies }: { policies: PrintPolicyResponse[] }) {
  return (
    <Section
      title="列印契約"
      description="固定公司樣張已明示的紙張與方向；瀏覽器仍會顯示作業系統列印視窗。"
    >
      <div className="ui-table-frame organization-policy-table">
        <table className="ui-data-table">
          <thead><tr><th scope="col">文件</th><th scope="col">紙張</th><th scope="col">方向</th><th scope="col">驗收狀態</th></tr></thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.document_type}>
                <th scope="row">{policy.label}</th>
                <td>{policy.paper_size}</td>
                <td>{policy.orientation ? orientationLabels[policy.orientation] : '待公司樣張確認'}</td>
                <td>
                  <StatusLabel tone={policy.status === 'confirmed' ? 'success' : 'warning'}>
                    {policy.status === 'confirmed' ? '樣張已確認' : '待公司實印確認'}
                  </StatusLabel>
                  <span className="organization-policy-table__note">{policy.note}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}
