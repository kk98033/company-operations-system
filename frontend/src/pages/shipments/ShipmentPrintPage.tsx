import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { getShipment, shipmentQueryKey } from '../../api/shipments'
import { getApiErrorMessage } from '../../api/errorMessage'
import { SystemState } from '../../ui/UiPatterns'
import { DocumentPdfButton } from '../document-exports/DocumentPdfButton'

export function ShipmentPrintPage() {
  const { shipmentId } = useParams({ strict: false }) as { shipmentId: string }; const navigate = useNavigate()
  const query = useQuery({ queryKey: shipmentQueryKey(shipmentId), queryFn: () => getShipment(shipmentId) })
  if (query.isPending) return <p>正在準備 A4 出貨單…</p>
  if (query.isError || !query.data) return <SystemState action={<span>返回後重試</span>} code="ERR" description={getApiErrorMessage(query.error)} eyebrow="列印資料異常" role="alert" title="無法產生出貨單" />
  const row = query.data
  return <div className="shipment-print-shell"><div className="shipment-print-toolbar"><button className="ui-button ui-button--secondary" onClick={() => void navigate({ to: '/shipments/$shipmentId', params: { shipmentId } })} type="button">返回</button><button className="ui-button ui-button--secondary" onClick={() => window.print()} type="button">列印 A4</button><DocumentPdfButton documentId={shipmentId} documentType="shipment" /></div><article className="shipment-print-page"><header><p>出貨單</p><h1>{row.document_number}</h1><dl><div><dt>客戶</dt><dd>{row.customer_name}</dd></div><div><dt>出貨日期</dt><dd>{row.shipment_date}</dd></div><div><dt>送貨地址</dt><dd>{row.delivery_address || '—'}</dd></div></dl></header><table><thead><tr><th>項次</th><th>工單／客戶單號</th><th>品名／規格</th><th>正式量</th><th>備品量</th><th>交付合計</th></tr></thead><tbody>{row.items.map((item) => <tr key={item.id}><td>{item.line_no}</td><td>{item.work_order_document_number}<br />{item.customer_order_number || '—'}</td><td>{item.product_name}<br />{item.specification || '—'}</td><td>{item.delivered_quantity}</td><td>{item.spare_quantity}</td><td>{item.inventory_consumed_quantity}</td></tr>)}</tbody></table><footer><p>備註：{row.notes || '—'}</p><div><span>出貨人員：</span><span>客戶簽收：</span></div></footer></article></div>
}
