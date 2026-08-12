import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { createCustomer, CUSTOMER_LIST_QUERY_KEY } from '../../api/customers'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import { PageHeader, SystemState } from '../../ui/UiPatterns'
import { CustomerForm } from './CustomerForm'
import { customerPayload, emptyCustomerDraft } from './customerDraft'

export function CustomerCreatePage() {
  const canManage = useHasCapability('customers.manage')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState(emptyCustomerDraft)
  const mutation = useMutation({
    mutationFn: createCustomer,
    onSuccess: async (customer) => {
      await queryClient.invalidateQueries({ queryKey: CUSTOMER_LIST_QUERY_KEY })
      await navigate({ to: '/customers/$customerId', params: { customerId: customer.id } })
    },
  })
  if (!canManage) {
    return (
      <SystemState
        action={<span>請聯絡系統管理者</span>}
        code="403"
        description="目前帳號沒有 customers.manage 權限。"
        eyebrow="權限限制"
        role="alert"
        title="沒有新增客戶權限"
      />
    )
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate(customerPayload(draft))
  }
  return (
    <div className="ui-pattern-stack customer-page">
      <PageHeader
        eyebrow="客戶管理 / 新增"
        title="新增客戶"
        description="建立目前公司的客戶主檔；不會寫入其他公司。"
        actions={[{ label: '返回清單', onClick: () => void navigate({ to: '/customers' }) }]}
      />
      <CustomerForm
        draft={draft}
        errorMessage={mutation.isError ? getApiErrorMessage(mutation.error) : undefined}
        isPending={mutation.isPending}
        onChange={setDraft}
        onSubmit={submit}
        submitLabel="存檔"
      />
    </div>
  )
}
