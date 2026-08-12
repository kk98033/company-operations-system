import { FormEvent, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  getOrganizationProfile,
  ORGANIZATION_PROFILE_QUERY_KEY,
  updateOrganizationProfile,
} from '../../api/organizationProfile'
import type {
  CurrentSessionResponse,
  OrganizationProfileResponse,
} from '../../api/generated/company-system'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { CURRENT_SESSION_QUERY_KEY } from '../../auth/session'
import { Field, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'

type ProfileDraft = Pick<
  OrganizationProfileResponse,
  | 'name'
  | 'tax_identifier'
  | 'representative_name'
  | 'phone'
  | 'fax'
  | 'email'
  | 'address'
>

const emptyDraft: ProfileDraft = {
  name: '',
  tax_identifier: null,
  representative_name: null,
  phone: null,
  fax: null,
  email: null,
  address: null,
}

function display(value: string | null) {
  return value || '尚未設定'
}

function CompanyLetterheadPreview({ draft }: { draft: ProfileDraft }) {
  return (
    <div className="company-letterhead" aria-label="公司頁首預覽">
      <div className="company-letterhead__logo" aria-label="Logo 尚未設定">LOGO</div>
      <div className="company-letterhead__identity">
        <strong>{draft.name || '公司名稱'}</strong>
        <span>統一編號：{display(draft.tax_identifier)}</span>
      </div>
      <dl>
        <div><dt>電話</dt><dd>{display(draft.phone)}</dd></div>
        <div><dt>傳真</dt><dd>{display(draft.fax)}</dd></div>
        <div><dt>Email</dt><dd>{display(draft.email)}</dd></div>
        <div><dt>地址</dt><dd>{display(draft.address)}</dd></div>
      </dl>
    </div>
  )
}

export function CompanyProfilePage() {
  const canManage = useHasCapability('settings.manage')
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<ProfileDraft>(emptyDraft)
  const profileQuery = useQuery({
    queryKey: ORGANIZATION_PROFILE_QUERY_KEY,
    queryFn: getOrganizationProfile,
    enabled: canManage,
  })
  const mutation = useMutation({
    mutationFn: updateOrganizationProfile,
    onSuccess: (profile) => {
      queryClient.setQueryData(ORGANIZATION_PROFILE_QUERY_KEY, profile)
      queryClient.setQueryData<CurrentSessionResponse>(
        CURRENT_SESSION_QUERY_KEY,
        (current) => current
          ? {
              ...current,
              organization: { ...current.organization, name: profile.name },
            }
          : current,
      )
    },
  })

  useEffect(() => {
    if (profileQuery.data) {
      const { name, tax_identifier, representative_name, phone, fax, email, address } = profileQuery.data
      setDraft({ name, tax_identifier, representative_name, phone, fax, email, address })
    }
  }, [profileQuery.data])

  if (!canManage) {
    return (
      <SystemState
        action={<span>請聯絡公司系統管理者</span>}
        code="403"
        description="只有取得 settings.manage 權限的成員可以維護公司基本資料。"
        eyebrow="權限限制"
        role="alert"
        title="沒有公司資料維護權限"
      />
    )
  }

  if (profileQuery.isPending) {
    return <SystemState action={<span>請稍候</span>} code="ORG" description="正在讀取目前公司的資料。" eyebrow="資料讀取" role="status" title="正在載入公司資料" />
  }

  if (profileQuery.isError) {
    return (
      <SystemState
        action={<button className="ui-button ui-button--primary" onClick={() => void profileQuery.refetch()} type="button">重新載入</button>}
        code="ERR"
        description={getApiErrorMessage(profileQuery.error)}
        eyebrow="資料異常"
        role="alert"
        title="無法載入公司資料"
      />
    )
  }

  const profile = profileQuery.data
  function setField(field: keyof ProfileDraft, value: string) {
    setDraft((current) => (
      field === 'name'
        ? { ...current, name: value }
        : { ...current, [field]: value || null }
    ))
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ ...draft, name: draft.name.trim(), expected_updated_at: profile.updated_at })
  }

  return (
    <div className="ui-pattern-stack company-profile-page">
      <PageHeader
        eyebrow="系統管理 / 公司設定"
        title="公司基本資料"
        description="此處資料會供報價單、工單與後續正式列印頁首共用；目前公司由登入 Session 決定。"
      />
      <div className="company-profile-layout">
        <Section title="基本資料" description="欄位依公司附件與舊系統公司資料畫面整理。">
          <form onSubmit={submit}>
            <div className="ui-form-grid company-profile-form">
              <Field label="公司名稱" required>
                <input maxLength={200} onChange={(event) => setField('name', event.target.value)} required value={draft.name} />
              </Field>
              <Field label="統一編號">
                <input maxLength={20} onChange={(event) => setField('tax_identifier', event.target.value)} value={draft.tax_identifier ?? ''} />
              </Field>
              <Field label="負責人">
                <input maxLength={100} onChange={(event) => setField('representative_name', event.target.value)} value={draft.representative_name ?? ''} />
              </Field>
              <Field label="電話">
                <input maxLength={32} onChange={(event) => setField('phone', event.target.value)} type="tel" value={draft.phone ?? ''} />
              </Field>
              <Field label="傳真">
                <input maxLength={32} onChange={(event) => setField('fax', event.target.value)} value={draft.fax ?? ''} />
              </Field>
              <Field label="Email">
                <input maxLength={254} onChange={(event) => setField('email', event.target.value)} type="email" value={draft.email ?? ''} />
              </Field>
              <Field label="地址">
                <textarea maxLength={500} onChange={(event) => setField('address', event.target.value)} rows={3} value={draft.address ?? ''} />
              </Field>
            </div>
            {mutation.isError ? <p className="company-profile-message company-profile-message--error" role="alert">{getApiErrorMessage(mutation.error)}</p> : null}
            {mutation.isSuccess ? <p className="company-profile-message" role="status">公司資料已存檔，並已寫入操作稽核。</p> : null}
            <footer className="ui-form-footer">
              <span>最後更新：{new Intl.DateTimeFormat('zh-TW', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(profile.updated_at))}</span>
              <div><button className="ui-button ui-button--primary" disabled={mutation.isPending} type="submit">{mutation.isPending ? '存檔中…' : '存檔'}</button></div>
            </footer>
          </form>
        </Section>
        <div className="company-profile-side">
          <Section title="文件頁首預覽" description="確認共用資訊排列，不代表報價單或工單的完整列印版面。">
            <CompanyLetterheadPreview draft={draft} />
          </Section>
          <Section title="公司 Logo" description="檔案內容不存進公司基本資料表。">
            <div className="company-logo-status">
              <StatusLabel tone={profile.logo ? 'success' : 'neutral'}>{profile.logo ? '已設定 metadata' : '尚未設定'}</StatusLabel>
              <p>{profile.logo ? `檔名：${profile.logo.original_filename}` : 'Logo 上傳與物件儲存將在附件儲存切片實作；本頁不允許手填檔案路徑。'}</p>
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}
