export type WorkflowModule = {
  id: string
  path: string
  icon: string
  label: string
  phase: string
  description: string
  responsibilities: readonly string[]
  input: string
  output: string
  requirementIds: readonly string[]
}

export const workflowModules = [
  {
    id: 'customers', path: '/customers', icon: '客', label: '客戶管理', phase: 'Phase 2',
    description: '集中維護客戶基本資料、聯絡方式、帳務條件與常用工作項目。',
    responsibilities: ['依代號、名稱或簡稱查詢', '保存聯絡與帳務設定', '提供報價與工單的客戶快照來源'],
    input: '公司基本設定', output: '報價或直接建立工單', requirementIds: ['CUST-001', 'CUST-002', 'CUST-003'],
  },
  {
    id: 'quotations', path: '/quotations', icon: '報', label: '報價管理', phase: 'Phase 3',
    description: '建立多明細報價、另存新檔與列印；報價不是建立工單的必經流程。',
    responsibilities: ['建立多明細報價', '保存版費、刀模費與價格快照', '選擇報價明細轉入工單'],
    input: '客戶資料', output: '工單（選用流程）', requirementIds: ['QUO-001', 'QUO-003', 'QUO-005'],
  },
  {
    id: 'work-orders', path: '/work-orders', icon: '工', label: '工單管理', phase: 'Phase 4',
    description: '同時支援直接建立工單，以及由報價明細轉入後再調整確認。',
    responsibilities: ['單頁分區完成主要資料', '材料、印刷、製程與附件', '查詢、列印、另存新檔與作廢'],
    input: '客戶或報價明細', output: '生產製程', requirementIds: [
      'WO-001', 'WO-002', 'WO-003', 'WO-004', 'WO-005', 'WO-006',
      'WO-007', 'WO-008', 'WO-009', 'WO-010', 'WO-011', 'WO-012',
    ],
  },
  {
    id: 'production', path: '/production', icon: '生', label: '生產管理', phase: 'Phase 5',
    description: '追蹤各製程狀態，並把一般製程完成與最終完工核定清楚分開。',
    responsibilities: ['製程開始、完成與重開', '交期與異常監管', '最終完工核定與沖銷'],
    input: '已確認工單', output: '完工入庫', requirementIds: ['PROD-001', 'PROD-002', 'PROD-003'],
  },
  {
    id: 'inventory', path: '/inventory', icon: '庫', label: '庫存管理', phase: 'Phase 5',
    description: '以不可變流水追蹤完工、出貨、備品、調整與沖銷後的可出貨量。',
    responsibilities: ['庫存流水與來源追溯', '待出貨存貨查詢', '人工調整與核准'],
    input: '最終完工核定', output: '可出貨品項', requirementIds: ['INV-001', 'INV-002'],
  },
  {
    id: 'shipments', path: '/shipments', icon: '出', label: '出貨管理', phase: 'Phase 6',
    description: '依客戶選取可出貨品項，支援部分、多次、備品與取消出貨。',
    responsibilities: ['先選客戶再選可出貨品項', '部分與多次出貨', '備品、防超量與反向沖銷'],
    input: '正可用庫存', output: '待計價出貨明細', requirementIds: ['SHIP-001', 'SHIP-002', 'SHIP-005'],
  },
  {
    id: 'pricing', path: '/pricing', icon: '價', label: '計價管理', phase: 'Phase 7',
    description: '由出貨建立唯一基礎計價，並提供額外明細與歷史價格建議。',
    responsibilities: ['待計價清單', '防止同一出貨重複計價', '價格歷史與來源追溯'],
    input: '已確認出貨', output: '待請款計價項目', requirementIds: ['PRICE-001', 'PRICE-002', 'PRICE-004'],
  },
  {
    id: 'statements', path: '/statements', icon: '請', label: '請款／對帳', phase: 'Phase 8',
    description: '依客戶與期間彙整已計價項目，保存稅額、取整與文件快照。',
    responsibilities: ['待請款項目選取', '稅額與取整快照', '對帳單列印與取消'],
    input: '已確認計價', output: '應收帳款', requirementIds: ['BILL-001', 'BILL-002', 'BILL-004'],
  },
  {
    id: 'receipts', path: '/receipts', icon: '收', label: '收款管理', phase: 'Phase 8',
    description: '登記並分配收款，追蹤已收、部分收款、未收款與沖銷。',
    responsibilities: ['自動或手動分配收款', '部分收款與餘額', '沖銷與帳齡查詢'],
    input: '有效請款／對帳', output: '可追溯收款結果', requirementIds: ['BILL-005'],
  },
] as const satisfies readonly WorkflowModule[]

export type WorkflowPath = (typeof workflowModules)[number]['path']
