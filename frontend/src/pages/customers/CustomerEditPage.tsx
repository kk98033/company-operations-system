import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'

import { customerQueryKey, CUSTOMER_LIST_QUERY_KEY, getCustomer, updateCustomer, updateCustomerStatus } from '../../api/customers'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { DefinitionGrid, PageHeader, Section, StatusLabel, SystemState } from '../../ui/UiPatterns'
import { CustomerForm } from './CustomerForm'
import { CustomerWorkItemsSection } from './CustomerWorkItemsSection'
import { customerPayload, emptyCustomerDraft, type CustomerDraft } from './customerDraft'

export function CustomerEditPage() {
  const { customerId } = useParams({ from: '/authenticated/customers/$customerId' })
  const canRead = useHasCapability('customers.read')
  const canManage = useHasCapability('customers.manage')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<CustomerDraft>(emptyCustomerDraft)
  const query = useQuery({ queryKey: customerQueryKey(customerId), queryFn: () => getCustomer(customerId), enabled: canRead })
  useEffect(() => {
    if (!query.data) return
    const { code, name, short_name, tax_identifier, contact_name, phone, phone_secondary, mobile, fax, email, postal_code, city, address, payment_terms } = query.data
    setDraft({ code, name, short_name: short_name ?? '', tax_identifier: tax_identifier ?? '', contact_name: contact_name ?? '', phone: phone ?? '', phone_secondary: phone_secondary ?? '', mobile: mobile ?? '', fax: fax ?? '', email: email ?? '', postal_code: postal_code ?? '', city: city ?? '', address: address ?? '', payment_terms: payment_terms ?? '' })
  }, [query.data])
  const mutation = useMutation({
    mutationFn: (value: CustomerDraft) => updateCustomer(customerId, {
      ...customerPayload(value),
      expected_updated_at: query.data!.updated_at,
    }),
    onSuccess: (customer) => {
      queryClient.setQueryData(customerQueryKey(customerId), customer)
      void queryClient.invalidateQueries({ queryKey: CUSTOMER_LIST_QUERY_KEY })
    },
  })
  const statusMutation = useMutation({
    mutationFn: () => updateCustomerStatus(customerId, {
      expected_updated_at: query.data!.updated_at,
      status: query.data!.status === 'active' ? 'inactive' : 'active',
    }),
    onSuccess: (customer) => {
      queryClient.setQueryData(customerQueryKey(customerId), customer)
      void queryClient.invalidateQueries({ queryKey: CUSTOMER_LIST_QUERY_KEY })
    },
  })
  if (!canRead) {
    return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 customers.read 權限。" eyebrow="權限限制" role="alert" title="沒有客戶資料權限" />
  }
  if (query.isPending) {
    return <SystemState action={<span>請稍候</span>} code="CUS" description="正在讀取客戶資料。" eyebrow="資料讀取" role="status" title="正在載入客戶" />
  }
  if (query.isError) {
    return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入客戶" />
  }
  const customer = query.data
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate(draft)
  }
  const readOnlyItems = [
    { label: '簡稱', value: customer.short_name || '—' },
    { label: '統一編號', value: customer.tax_identifier || '—' },
    { label: '聯絡人', value: customer.contact_name || '—' },
    { label: '電話', value: customer.phone || '—' },
    { label: '電話 2', value: customer.phone_secondary || '—' },
    { label: '行動電話', value: customer.mobile || '—' },
    { label: '傳真', value: customer.fax || '—' },
    { label: 'Email', value: customer.email || '—' },
    { label: '郵遞區號', value: customer.postal_code || '—' },
    { label: '縣市', value: customer.city || '—' },
    { label: '完整地址', value: customer.address || '—' },
    { label: '付款條件', value: customer.payment_terms || '—' },
  ]
  return (
    <div className="ui-pattern-stack customer-page">
      <PageHeader eyebrow="客戶管理 / 編輯" title={`${customer.code} ${customer.name}`} description="代號、基本資料與主要聯絡方式會供後續文件建立時帶入。" actions={[{ label: '返回清單', onClick: () => void navigate({ to: '/customers' }) }]} />
      <Section title="目前狀態" actions={canManage ? <button className="ui-button ui-button--secondary" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate()} type="button">{customer.status === 'active' ? '停用客戶' : '重新啟用'}</button> : undefined}><StatusLabel tone={customer.status === 'active' ? 'success' : 'neutral'}>{customer.status === 'active' ? '使用中' : '已停用'}</StatusLabel>{statusMutation.isError ? <p className="company-profile-message company-profile-message--error" role="alert">{getApiErrorMessage(statusMutation.error)}</p> : null}</Section>
      {canManage ? (
        <CustomerForm
          draft={draft}
          errorMessage={mutation.isError ? getApiErrorMessage(mutation.error) : undefined}
          isPending={mutation.isPending}
          onChange={setDraft}
          onSubmit={submit}
          submitLabel="存檔"
        />
      ) : (
        <Section title="主要資料">
          <DefinitionGrid items={readOnlyItems} />
        </Section>
      )}
      {customer.legacy_source_table ? (
        <Section title="舊系統帳務對照" description="只供核對舊資料，不會自動開啟新版對帳單計稅。">
          <DefinitionGrid items={[
            { label: '來源', value: `${customer.legacy_source_table} / ${customer.legacy_source_key}` },
            { label: '舊稅額請款值', value: customer.legacy_tax_setting_raw || '—' },
            { label: '舊每筆合計值', value: customer.legacy_rounding_setting_raw || '—' },
          ]} />
        </Section>
      ) : null}
      <CustomerWorkItemsSection canManage={canManage} customerId={customerId} />
    </div>
  )
}
