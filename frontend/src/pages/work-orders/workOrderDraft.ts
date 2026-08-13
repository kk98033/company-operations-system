import type { WorkOrderCreate, WorkOrderResponse } from '../../api/generated/company-system'

export const processDefinitions = [
  ['artwork', '美工'], ['output', '輸出'], ['plate', '製版'], ['proof', '打樣'],
  ['printing', '印刷'], ['coating', '上光'], ['mounting', '裱紙'], ['die', '模具'],
  ['die_cutting', '軋型'], ['finishing', '加工'], ['gluing', '糊邊'],
  ['transport', '運送'], ['other', '其他'],
] as const

export type PaperDraft = { type: 'face'|'back'|'flute'; vendor: string; paper: string; mill: string; size: string; quantity: string; note: string }
export type SideDraft = { color_count: string; c: boolean; m: boolean; y: boolean; k: boolean; special_colors: string }
export type ProcessDraft = { code: string; name: string; vendor: string; content: string; plate_version: string; plate_rotation: string; coating_type: string; die_number: string; die_count: string; packing: string }
export type WorkOrderDraft = {
  case_id: string; customer_id: string; customer_order_number: string;
  order_date: string; delivery_date: string; product_name: string;
  order_quantity: string; specification: string; unit_price: string;
  plate_fee: string; die_fee: string; papers: PaperDraft[];
  print: { length: string; width: string; k_count: string; imposition_count: string; print_quantity: string; variance: string; front: SideDraft; back: SideDraft; total_color_count: string };
  processes: ProcessDraft[]; notes: string;
}

const side = (): SideDraft => ({ color_count: '', c: false, m: false, y: false, k: false, special_colors: '' })
const paper = (type: PaperDraft['type']): PaperDraft => ({ type, vendor: '', paper: '', mill: '', size: '', quantity: '', note: '' })
const process = ([code, name]: readonly [string, string]): ProcessDraft => ({ code, name, vendor: '', content: '', plate_version: '', plate_rotation: '', coating_type: '', die_number: '', die_count: '', packing: '' })

export function emptyWorkOrderDraft(): WorkOrderDraft {
  return {
    case_id: '', customer_id: '', customer_order_number: '',
    order_date: new Date().toLocaleDateString('en-CA'), delivery_date: '',
    product_name: '', order_quantity: '', specification: '', unit_price: '0.00',
    plate_fee: '0.00', die_fee: '0.00',
    papers: [paper('face'), paper('back'), paper('flute')],
    print: { length: '', width: '', k_count: '', imposition_count: '', print_quantity: '', variance: '', front: side(), back: side(), total_color_count: '' },
    processes: processDefinitions.map(process), notes: '',
  }
}

const value = (item: unknown) => item == null ? '' : String(item)
export function responseToDraft(item: WorkOrderResponse): WorkOrderDraft {
  const print = item.print_specification ?? {}
  const front = print.front ?? {}
  const back = print.back ?? {}
  return {
    case_id: item.case_id, customer_id: item.customer_id,
    customer_order_number: item.customer_order_number ?? '', order_date: item.order_date,
    delivery_date: item.delivery_date ?? '', product_name: item.product_name,
    order_quantity: value(item.order_quantity), specification: item.specification ?? '',
    unit_price: value(item.unit_price), plate_fee: value(item.plate_fee), die_fee: value(item.die_fee),
    papers: item.papers.map((entry) => ({ type: entry.type as PaperDraft['type'], vendor: entry.vendor ?? '', paper: entry.paper ?? '', mill: entry.mill ?? '', size: entry.size ?? '', quantity: value(entry.quantity), note: entry.note ?? '' })),
    print: {
      length: value(print.length), width: value(print.width),
      k_count: value(print.k_count), imposition_count: value(print.imposition_count),
      print_quantity: value(print.print_quantity), variance: value(print.variance),
      front: { color_count: value(front.color_count), c: front.c ?? false, m: front.m ?? false, y: front.y ?? false, k: front.k ?? false, special_colors: front.special_colors ?? '' },
      back: { color_count: value(back.color_count), c: back.c ?? false, m: back.m ?? false, y: back.y ?? false, k: back.k ?? false, special_colors: back.special_colors ?? '' },
      total_color_count: value(print.total_color_count),
    },
    processes: item.processes.map((entry) => ({ code: entry.code, name: entry.name, vendor: entry.vendor ?? '', content: entry.content ?? '', plate_version: entry.plate_version ?? '', plate_rotation: entry.plate_rotation ?? '', coating_type: entry.coating_type ?? '', die_number: entry.die_number ?? '', die_count: value(entry.die_count), packing: entry.packing ?? '' })),
    notes: item.notes ?? '',
  }
}

const optionalNumber = (input: string) => input === '' ? null : input
const optionalInteger = (input: string) => input === '' ? null : Number(input)
const optional = (input: string) => input.trim() || null
export function toPayload(draft: WorkOrderDraft): WorkOrderCreate {
  return {
    case_id: optional(draft.case_id), customer_id: draft.customer_id,
    customer_order_number: optional(draft.customer_order_number), order_date: draft.order_date,
    delivery_date: optional(draft.delivery_date), product_name: draft.product_name,
    order_quantity: draft.order_quantity, specification: optional(draft.specification),
    unit_price: draft.unit_price || '0', plate_fee: draft.plate_fee || '0', die_fee: draft.die_fee || '0',
    papers: draft.papers.map((entry) => ({ ...entry, vendor: optional(entry.vendor), paper: optional(entry.paper), mill: entry.type === 'flute' ? null : optional(entry.mill), size: optional(entry.size), quantity: optionalNumber(entry.quantity), note: optional(entry.note) })),
    print_specification: {
      length: optionalNumber(draft.print.length), width: optionalNumber(draft.print.width),
      k_count: optionalInteger(draft.print.k_count),
      imposition_count: optionalInteger(draft.print.imposition_count),
      print_quantity: optionalNumber(draft.print.print_quantity), variance: optionalNumber(draft.print.variance),
      front: { ...draft.print.front, color_count: optionalInteger(draft.print.front.color_count), special_colors: optional(draft.print.front.special_colors) },
      back: { ...draft.print.back, color_count: optionalInteger(draft.print.back.color_count), special_colors: optional(draft.print.back.special_colors) },
      total_color_count: optionalInteger(draft.print.total_color_count),
    },
    processes: draft.processes.map((entry) => ({ ...entry, vendor: optional(entry.vendor), content: optional(entry.content), plate_version: optional(entry.plate_version), plate_rotation: optional(entry.plate_rotation), coating_type: optional(entry.coating_type), die_number: optional(entry.die_number), die_count: optionalInteger(entry.die_count), packing: optional(entry.packing) })),
    notes: optional(draft.notes),
  }
}
