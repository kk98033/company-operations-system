import type { WorkflowModule } from '../../app/workflowModules'
import { DataTableFrame, DefinitionGrid, Section, StatusLabel } from '../../ui/UiPatterns'
import { ModulePrototypePage } from '../ModulePrototypePage'

const sampleWorkOrders = [
  { number: 'DEMO-WO-001', product: '彩盒外盒（假資料）', dueDate: '2026-08-14', process: '印刷', status: '進行中' },
  { number: 'DEMO-WO-002', product: '內襯紙卡（假資料）', dueDate: '2026-08-15', process: '待開始', status: '未開始' },
  { number: 'DEMO-WO-003', product: '產品貼紙（假資料）', dueDate: '2026-08-12', process: '完成', status: '已完成' },
] as const

export function CasePrototypePage({ module }: { module: WorkflowModule }) {
  return (
    <ModulePrototypePage module={module}>
      <Section
        title="案件與子工單（DEMO）"
        description="案件負責分組；每張工單仍各自保存品名、數量、材料、製程、完工、庫存與出貨。"
      >
        <DefinitionGrid
          items={[
            { label: '案件編號', value: 'DEMO-CASE-001' },
            { label: '客戶', value: '範例客戶（假資料）' },
            { label: '來源報價', value: 'DEMO-QT-001' },
            { label: '案件狀態', value: <StatusLabel tone="working">部分進行中</StatusLabel> },
          ]}
        />
        <DataTableFrame footer={<><span>共 3 張假資料工單</span><span>一張工單一個主要品項</span></>}>
          <table className="ui-data-table">
            <caption className="visually-hidden">案件中的子工單假資料</caption>
            <thead>
              <tr>
                <th className="ui-data-table__sticky" scope="col">工單號</th>
                <th scope="col">主要品項</th>
                <th scope="col">交期</th>
                <th scope="col">目前製程</th>
                <th scope="col">工單狀態</th>
              </tr>
            </thead>
            <tbody>
              {sampleWorkOrders.map((workOrder) => (
                <tr key={workOrder.number}>
                  <th className="ui-data-table__sticky" scope="row">{workOrder.number}</th>
                  <td>{workOrder.product}</td>
                  <td>{workOrder.dueDate}</td>
                  <td>{workOrder.process}</td>
                  <td>
                    <StatusLabel tone={workOrder.status === '已完成' ? 'success' : workOrder.status === '進行中' ? 'working' : 'neutral'}>
                      {workOrder.status}
                    </StatusLabel>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataTableFrame>
      </Section>
    </ModulePrototypePage>
  )
}
