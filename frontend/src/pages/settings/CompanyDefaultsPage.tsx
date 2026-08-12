import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  getOrganizationSettings,
  ORGANIZATION_SETTINGS_QUERY_KEY,
  updateOrganizationSettings,
} from '../../api/organizationSettings'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { PageHeader, SystemState } from '../../ui/UiPatterns'
import { NumberingPolicyTable, PrintPolicyTable } from './SettingsPolicyTables'
import {
  StatementTaxDefaultsForm,
  type StatementTaxDraft,
} from './StatementTaxDefaultsForm'

const emptyTaxDraft: StatementTaxDraft = {
  enabled: false,
  taxRatePercent: '',
  roundingScope: '',
  roundingDecimalPlaces: '',
}

export function CompanyDefaultsPage() {
  const canManage = useHasCapability('settings.manage')
  const queryClient = useQueryClient()
  const [taxDraft, setTaxDraft] = useState(emptyTaxDraft)
  const settingsQuery = useQuery({
    queryKey: ORGANIZATION_SETTINGS_QUERY_KEY,
    queryFn: getOrganizationSettings,
    enabled: canManage,
  })
  const mutation = useMutation({
    mutationFn: updateOrganizationSettings,
    onSuccess: (settings) => queryClient.setQueryData(ORGANIZATION_SETTINGS_QUERY_KEY, settings),
  })

  useEffect(() => {
    if (!settingsQuery.data) return
    const { statement_tax: tax } = settingsQuery.data
    setTaxDraft({
      enabled: tax.enabled,
      taxRatePercent: tax.tax_rate_percent ?? '',
      roundingScope: tax.rounding_scope ?? '',
      roundingDecimalPlaces: tax.rounding_decimal_places?.toString() ?? '',
    })
  }, [settingsQuery.data])

  if (!canManage) {
    return <SystemState action={<span>請聯絡公司系統管理者</span>} code="403" description="只有取得 settings.manage 權限的成員可以維護公司預設設定。" eyebrow="權限限制" role="alert" title="沒有公司預設設定權限" />
  }
  if (settingsQuery.isPending) {
    return <SystemState action={<span>請稍候</span>} code="ORG" description="正在讀取目前公司的帳務與文件預設。" eyebrow="資料讀取" role="status" title="正在載入公司預設" />
  }
  if (settingsQuery.isError) {
    return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void settingsQuery.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(settingsQuery.error)} eyebrow="資料異常" role="alert" title="無法載入公司預設" />
  }

  const settings = settingsQuery.data
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({
      expected_updated_at: settings.updated_at,
      statement_tax_default_enabled: taxDraft.enabled,
      statement_tax_rate_percent: taxDraft.enabled ? taxDraft.taxRatePercent : null,
      statement_rounding_scope: taxDraft.enabled ? taxDraft.roundingScope || null : null,
      statement_rounding_decimal_places: taxDraft.enabled
        ? Number(taxDraft.roundingDecimalPlaces)
        : null,
    })
  }

  return (
    <div className="ui-pattern-stack organization-settings-page">
      <PageHeader
        eyebrow="系統管理 / 公司設定"
        title="文件與帳務預設"
        description="公司由登入 Session 決定；可編輯對帳偏好，已簽認的單號與列印契約則集中唯讀呈現。"
      />
      <StatementTaxDefaultsForm
        draft={taxDraft}
        errorMessage={mutation.isError ? getApiErrorMessage(mutation.error) : undefined}
        isPending={mutation.isPending}
        isSuccess={mutation.isSuccess}
        onChange={setTaxDraft}
        onSubmit={submit}
        updatedAt={settings.updated_at}
      />
      <NumberingPolicyTable policies={settings.document_numbering} />
      <PrintPolicyTable policies={settings.printing} />
    </div>
  )
}
