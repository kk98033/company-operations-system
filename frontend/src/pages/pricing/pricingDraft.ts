import type { PricingItemResponse, PricingItemType } from '../../api/generated/company-system'

export type PricingDraftLine = {
  key: string
  source_shipment_item_id: string | null
  item_type: PricingItemType
  content: string
  product_name: string
  specification: string
  quantity: string
  unit_price: string
  plate_fee: string
  die_fee: string
}

const value = (input: string | number) => String(input)

export const responseLine = (item: PricingItemResponse): PricingDraftLine => ({
  key: item.id,
  source_shipment_item_id: item.source_shipment_item_id ?? null,
  item_type: item.item_type,
  content: item.content,
  product_name: item.product_name ?? '',
  specification: item.specification ?? '',
  quantity: value(item.quantity),
  unit_price: value(item.unit_price),
  plate_fee: value(item.plate_fee),
  die_fee: value(item.die_fee),
})

export const manualLine = (): PricingDraftLine => ({
  key: crypto.randomUUID(), source_shipment_item_id: null, item_type: 'manual',
  content: '', product_name: '', specification: '', quantity: '0', unit_price: '0',
  plate_fee: '0', die_fee: '0',
})

export const spareLine = (base: PricingDraftLine): PricingDraftLine => ({
  ...base, key: crypto.randomUUID(), item_type: 'spare', content: `${base.content}｜備品收費`,
  quantity: '0', plate_fee: '0', die_fee: '0',
})

export const subtotal = (line: PricingDraftLine) =>
  Number(line.quantity || 0) * Number(line.unit_price || 0)
  + Number(line.plate_fee || 0) + Number(line.die_fee || 0)
