import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  MASTER_DATA_QUERY_KEY,
  createCatalog,
  createVendor,
  listCatalog,
  listProcesses,
  listVendors,
  setCatalogStatus,
  setProcessStatus,
  setVendorStatus,
  type CatalogKind,
} from '../../api/masterData'
import { getApiErrorMessage } from '../../api/errorMessage'
import { useHasCapability } from '../../auth/capabilities'
import type { CatalogResponse, ProcessDefinitionResponse, VendorResponse } from '../../api/generated/company-system'
import { DataTableFrame, Field, PageHeader, StatusLabel, SystemState } from '../../ui/UiPatterns'

type Tab = 'vendors' | CatalogKind | 'processes'
const tabs: { id: Tab; label: string }[] = [
  { id: 'vendors', label: '廠商' },
  { id: 'paper-types', label: '紙質' },
  { id: 'paper-mills', label: '紙廠' },
  { id: 'processes', label: '製程' },
]

export function MasterDataPage() {
  const [tab, setTab] = useState<Tab>('vendors')
  const canRead = useHasCapability('master_data.read')
  const canManage = useHasCapability('master_data.manage')

  if (!canRead) return <SystemState action={<span>請聯絡系統管理者</span>} code="403" description="目前帳號沒有 master_data.read 權限。" eyebrow="權限限制" role="alert" title="沒有主檔資料權限" />

  return (
    <div className="ui-pattern-stack master-data-page">
      <PageHeader eyebrow="系統管理 / 基礎主檔" title="生產與採購主檔" description="集中維護廠商、紙質、紙廠與公司固定製程；停用資料仍保留歷史關聯。" />
      <div aria-label="主檔分類" className="master-data-tabs" role="tablist">
        {tabs.map((item) => <button aria-selected={tab === item.id} className={tab === item.id ? 'master-data-tabs__button master-data-tabs__button--active' : 'master-data-tabs__button'} key={item.id} onClick={() => setTab(item.id)} role="tab" type="button">{item.label}</button>)}
      </div>
      {tab === 'vendors' ? <VendorPanel canManage={canManage} /> : null}
      {tab === 'paper-types' || tab === 'paper-mills' ? <CatalogPanel canManage={canManage} kind={tab} /> : null}
      {tab === 'processes' ? <ProcessPanel canManage={canManage} /> : null}
    </div>
  )
}

function VendorPanel({ canManage }: { canManage: boolean }) {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: [...MASTER_DATA_QUERY_KEY, 'vendors'], queryFn: listVendors })
  const create = useMutation({ mutationFn: createVendor, onSuccess: () => queryClient.invalidateQueries({ queryKey: MASTER_DATA_QUERY_KEY }) })
  const status = useMutation({ mutationFn: setVendorStatus, onSuccess: () => queryClient.invalidateQueries({ queryKey: MASTER_DATA_QUERY_KEY }) })
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    create.mutate({ code: String(data.get('code')), name: String(data.get('name')), category: data.get('category') === 'collaborator' ? 'collaborator' : 'supplier' })
    event.currentTarget.reset()
  }
  return <MasterPanelState query={query} title="廠商主檔">{canManage ? <form className="master-data-create" onSubmit={submit}><Field label="廠商代號" required><input name="code" required /></Field><Field label="廠商名稱" required><input name="name" required /></Field><Field label="分類" required><select name="category"><option value="supplier">供應商</option><option value="collaborator">協力廠</option></select></Field><button className="ui-button ui-button--primary" disabled={create.isPending} type="submit">新增廠商</button></form> : null}{query.data ? <MasterTable rows={query.data.items} canManage={canManage} category={(item) => (item as VendorResponse).category === 'supplier' ? '供應商' : '協力廠'} onToggle={(item) => status.mutate(item as VendorResponse)} /> : null}</MasterPanelState>
}

function CatalogPanel({ canManage, kind }: { canManage: boolean; kind: CatalogKind }) {
  const queryClient = useQueryClient()
  const title = kind === 'paper-types' ? '紙質主檔' : '紙廠主檔'
  const query = useQuery({ queryKey: [...MASTER_DATA_QUERY_KEY, kind], queryFn: () => listCatalog(kind) })
  const create = useMutation({ mutationFn: (payload: { code: string; name: string }) => createCatalog(kind, payload), onSuccess: () => queryClient.invalidateQueries({ queryKey: MASTER_DATA_QUERY_KEY }) })
  const status = useMutation({ mutationFn: (item: CatalogResponse) => setCatalogStatus(kind, item), onSuccess: () => queryClient.invalidateQueries({ queryKey: MASTER_DATA_QUERY_KEY }) })
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    create.mutate({ code: String(data.get('code')), name: String(data.get('name')) })
    event.currentTarget.reset()
  }
  return <MasterPanelState query={query} title={title}>{canManage ? <form className="master-data-create" onSubmit={submit}><Field label="代號" required><input name="code" required /></Field><Field label="名稱" required><input name="name" required /></Field><button className="ui-button ui-button--primary" disabled={create.isPending} type="submit">新增</button></form> : null}{query.data ? <MasterTable rows={query.data.items} canManage={canManage} onToggle={(item) => status.mutate(item as CatalogResponse)} /> : null}</MasterPanelState>
}

function ProcessPanel({ canManage }: { canManage: boolean }) {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: [...MASTER_DATA_QUERY_KEY, 'processes'], queryFn: listProcesses })
  const status = useMutation({ mutationFn: setProcessStatus, onSuccess: () => queryClient.invalidateQueries({ queryKey: MASTER_DATA_QUERY_KEY }) })
  return <MasterPanelState query={query} title="固定製程"><p className="master-data-note">依公司工單建檔稿固定 13 道製程；不可新增或改名，只能停用。</p>{query.data ? <MasterTable rows={query.data} canManage={canManage} category={(item) => `順序 ${String((item as ProcessDefinitionResponse).sort_order).padStart(2, '0')}`} onToggle={(item) => status.mutate(item as ProcessDefinitionResponse)} /> : null}</MasterPanelState>
}

function MasterPanelState({ children, query, title }: { children: React.ReactNode; query: { isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown }; title: string }) {
  if (query.isPending) return <SystemState action={<span>請稍候</span>} code="MST" description={`正在讀取${title}。`} eyebrow="資料讀取" role="status" title="正在載入" />
  if (query.isError) return <SystemState action={<button className="ui-button ui-button--primary" onClick={() => void query.refetch()} type="button">重新載入</button>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="資料異常" role="alert" title="無法載入主檔" />
  return <section aria-label={title}>{children}</section>
}

function MasterTable({ canManage, category, onToggle, rows }: { canManage: boolean; category?: (item: VendorResponse | CatalogResponse | ProcessDefinitionResponse) => string; onToggle: (item: VendorResponse | CatalogResponse | ProcessDefinitionResponse) => void; rows: (VendorResponse | CatalogResponse | ProcessDefinitionResponse)[] }) {
  return <DataTableFrame footer={<span>共 {rows.length} 筆</span>}><table className="ui-data-table"><thead><tr><th scope="col">代號</th><th scope="col">名稱</th>{category ? <th scope="col">分類／順序</th> : null}<th scope="col">狀態</th>{canManage ? <th scope="col">操作</th> : null}</tr></thead><tbody>{rows.map((item) => <tr key={item.id}><th scope="row">{item.code}</th><td>{item.name}</td>{category ? <td>{category(item)}</td> : null}<td><StatusLabel tone={item.status === 'active' ? 'success' : 'neutral'}>{item.status === 'active' ? '使用中' : '已停用'}</StatusLabel></td>{canManage ? <td><button className="ui-button ui-button--secondary" onClick={() => onToggle(item)} type="button">{item.status === 'active' ? '停用' : '啟用'}</button></td> : null}</tr>)}</tbody></table></DataTableFrame>
}
