import { useNavigate } from '@tanstack/react-router'

import {
  DataTableFrame,
  Field,
  FilterBar,
  PageHeader,
  Section,
  StatusLabel,
} from '../../ui/UiPatterns'

type SampleOrder = {
  workOrderNumber: string
  createdDate: string
  customerName: string
  productName: string
  orderQuantity: string
  unitPrice: string
  plateFee: string
  dieFee: string
  deliveryDate: string
  recordState: '現行' | '歷史／封存'
}

const sampleOrders: SampleOrder[] = [
  {
    workOrderNumber: 'DEMO-WO-001', createdDate: '2026-08-07', customerName: '範例客戶甲',
    productName: '彩盒外包裝', orderQuantity: '1,000', unitPrice: '12.50', plateFee: '800.00',
    dieFee: '1,200.00', deliveryDate: '2026-08-14', recordState: '現行',
  },
  {
    workOrderNumber: 'DEMO-WO-H01', createdDate: '2024-01-23', customerName: '範例客戶乙',
    productName: '產品說明卡', orderQuantity: '2,500', unitPrice: '3.80', plateFee: '0.00',
    dieFee: '0.00', deliveryDate: '2024-02-01', recordState: '歷史／封存',
  },
]

export function WorkOrderListPrototypePage() {
  const navigate = useNavigate()

  return (
    <div className="ui-pattern-stack">
      <PageHeader
        actions={[{
          label: '新增工單',
          onClick: () => navigate({ to: '/work-orders/new' }),
          tone: 'primary',
        }]}
        description="先查詢現行與歷史工單；新增使用同一張整合表單，正式編輯入口留待 Phase 4。本頁不是把工單內容拆成多個步驟。"
        eyebrow="工單管理 / 查詢原型"
        title="工單管理"
      />

      <div className="module-prototype__notice" role="status">
        <StatusLabel tone="warning">Phase 0 假資料原型</StatusLabel>
        <span>查詢條件與結果欄依系統修改圖排列；目前不會查詢、儲存或載入公司正式資料。</span>
      </div>

      <FilterBar>
        <Field label="關鍵字查詢" hint="預計涵蓋工單號、客戶、品名與備註">
          <input placeholder="輸入工單號、客戶或品名" type="search" />
        </Field>
        <Field label="客戶">
          <input placeholder="輸入客編或客名" />
        </Field>
        <Field label="資料範圍">
          <select defaultValue="all">
            <option value="all">現行與歷史</option>
            <option value="active">僅現行</option>
            <option value="archived">僅歷史／封存</option>
          </select>
        </Field>
        <Field label="建檔起日">
          <input type="date" />
        </Field>
        <Field label="建檔迄日">
          <input type="date" />
        </Field>
        <Field label="交貨起日">
          <input type="date" />
        </Field>
        <Field label="交貨迄日">
          <input type="date" />
        </Field>
        <div className="ui-filter-actions">
          <button className="ui-button ui-button--secondary" disabled type="button">清除</button>
          <button className="ui-button ui-button--primary" disabled type="button">查詢</button>
        </div>
      </FilterBar>

      <Section
        title="查詢結果"
        description="僅顯示 DEMO 假資料；正式版將合併現行與歷史工單。"
      >
        <DataTableFrame footer={<><span>顯示 1–2，共 2 筆假資料</span><span>每頁 30 筆</span></>}>
          <table className="ui-data-table">
            <caption className="visually-hidden">工單查詢假資料結果</caption>
            <thead>
              <tr>
                <th className="ui-data-table__sticky" scope="col">工單號</th>
                <th scope="col">建檔日期</th>
                <th scope="col">客戶</th>
                <th scope="col">品名</th>
                <th className="ui-data-table__number" scope="col">訂購數量</th>
                <th className="ui-data-table__number" scope="col">單價</th>
                <th className="ui-data-table__number" scope="col">版費</th>
                <th className="ui-data-table__number" scope="col">刀模費</th>
                <th scope="col">交貨日期</th>
                <th scope="col">資料狀態</th>
                <th scope="col">操作</th>
              </tr>
            </thead>
            <tbody>
              {sampleOrders.map((order) => (
                <tr key={order.workOrderNumber}>
                  <th className="ui-data-table__sticky" scope="row">{order.workOrderNumber}</th>
                  <td>{order.createdDate}</td>
                  <td>{order.customerName}</td>
                  <td>{order.productName}</td>
                  <td className="ui-data-table__number">{order.orderQuantity}</td>
                  <td className="ui-data-table__number">{order.unitPrice}</td>
                  <td className="ui-data-table__number">{order.plateFee}</td>
                  <td className="ui-data-table__number">{order.dieFee}</td>
                  <td>{order.deliveryDate}</td>
                  <td><StatusLabel tone={order.recordState === '現行' ? 'working' : 'neutral'}>{order.recordState}</StatusLabel></td>
                  <td><button className="ui-text-button" disabled type="button">Phase 4 開啟</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataTableFrame>
      </Section>
    </div>
  )
}
