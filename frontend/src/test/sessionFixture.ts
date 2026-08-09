import type { CurrentSessionResponse } from '../api/generated/company-system'

export const syntheticCurrentSession: CurrentSessionResponse = {
  expires_at: '2099-08-09T08:00:00Z',
  organization: {
    id: '10000000-0000-4000-8000-000000000001',
    name: '測試印刷股份有限公司（虛構）',
  },
  user: {
    id: '20000000-0000-4000-8000-000000000002',
    login_name: 'test.operator',
    display_name: '測試操作員',
  },
}
