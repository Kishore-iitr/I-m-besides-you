import { Invoice } from '../types';

export const INITIAL_INVOICES: Invoice[] = [
  {
    id: 'inv-7344',
    invoice_number: 'INV-2026-7344',
    voucher_code: 'P6-07010448-001',
    vendor_code: 'V3005',
    vendor_name: 'グローバルテック合同会社',
    subtotal_amount: 651120,
    tax_rate: 0.10,
    tax_amount: 65112,
    total_amount: 716232,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK',
    line_items: [
      { item_code: 'ITM-INFRA-01', description: '基幹ERPクラウド24/365監視・保守 (当月分)', quantity: 1, unit_price: 651120, amount: 651120 }
    ]
  },
  {
    id: 'inv-7345',
    invoice_number: 'INV-2026-7345',
    voucher_code: 'P6-07010448-002',
    vendor_code: 'V3006',
    vendor_name: '北陸部品工業株式会社',
    subtotal_amount: 413753,
    tax_rate: 0.10,
    tax_amount: 41375,
    total_amount: 455128,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK',
    line_items: [
      { item_code: 'ITM-PART-01', description: '高精度射出成型樹脂パーツ定期枠納入', quantity: 1, unit_price: 413753, amount: 413753 }
    ]
  },
  {
    id: 'inv-7346',
    invoice_number: 'INV-2026-7346',
    voucher_code: 'P6-07010448-003',
    vendor_code: 'V3002',
    vendor_name: '大和商事株式会社',
    subtotal_amount: 1124945,
    tax_rate: 0.10,
    tax_amount: 112494,
    total_amount: 1237439,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK',
    line_items: [
      { item_code: 'ITM-SPL-01', description: '全社共通オフィスサプライ・梱包用パレット定額供給', quantity: 1, unit_price: 1124945, amount: 1124945 }
    ]
  },
  {
    id: 'inv-7347',
    invoice_number: 'INV-2026-7347',
    voucher_code: 'P6-07010448-004',
    vendor_code: 'V3007',
    vendor_name: '福岡システム設計',
    subtotal_amount: 1532168,
    tax_rate: 0.10,
    tax_amount: 153216,
    total_amount: 1685384,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK',
    line_items: [
      { item_code: 'ITM-SYS-01', description: 'EDI受発注連携モジュール常駐運用保守業務', quantity: 1, unit_price: 1532168, amount: 1532168 }
    ]
  },
  {
    id: 'inv-7354',
    invoice_number: 'INV-2026-7354',
    voucher_code: 'P6-07010448-011',
    vendor_code: 'V3001',
    vendor_name: '株式会社山田製作所',
    subtotal_amount: 340285,
    tax_rate: 0.10,
    tax_amount: 34028,
    total_amount: 374313,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK',
    line_items: [
      { item_code: 'ITM-MNT-01', description: 'プレス工作機械定期保全点検・金型校正', quantity: 1, unit_price: 340285, amount: 340285 }
    ]
  },
  {
    id: 'inv-7355',
    invoice_number: 'INV-2026-7355',
    voucher_code: 'P6-07010448-012',
    vendor_code: 'V3007',
    vendor_name: '福岡システム設計',
    subtotal_amount: 1532168,
    tax_rate: 0.10,
    tax_amount: 153216,
    total_amount: 1685384,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-8004',
    invoice_number: 'INV-2026-8004',
    voucher_code: 'P6-07046967-007',
    vendor_code: 'V3003',
    vendor_name: '東京電子工業株式会社',
    subtotal_amount: 478182,
    tax_rate: 0.10,
    tax_amount: 47818,
    total_amount: 526000,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-8005',
    invoice_number: 'INV-2026-8005',
    voucher_code: 'P6-07046967-008',
    vendor_code: 'V3008',
    vendor_name: '沖縄物流センター',
    subtotal_amount: 273839,
    tax_rate: 0.10,
    tax_amount: 27384,
    total_amount: 301223,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-7538',
    invoice_number: 'INV-2026-7538',
    voucher_code: 'P6-07047510-007',
    vendor_code: 'V3004',
    vendor_name: '関西物流サービス',
    subtotal_amount: 2948300,
    tax_rate: 0.10,
    tax_amount: 294830,
    total_amount: 3243130,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-7539',
    invoice_number: 'INV-2026-7539',
    voucher_code: 'P6-07047510-008',
    vendor_code: 'V3006',
    vendor_name: '北陸部品工業株式会社',
    subtotal_amount: 412552, // Slight deviation for discrepancy testing
    tax_rate: 0.10,
    tax_amount: 41255,
    total_amount: 453807,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'RATE_MISMATCH'
  },
  {
    id: 'inv-7540',
    invoice_number: 'INV-2026-7540',
    voucher_code: 'P6-07047510-009',
    vendor_code: 'V3007',
    vendor_name: '福岡システム設計',
    subtotal_amount: 1522358,
    tax_rate: 0.10,
    tax_amount: 152236,
    total_amount: 1674594,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'RATE_MISMATCH'
  },
  {
    id: 'inv-7246',
    invoice_number: 'INV-2026-7246',
    voucher_code: 'P6-07088456-001',
    vendor_code: 'V3005',
    vendor_name: 'グローバルテック合同会社',
    subtotal_amount: 651120,
    tax_rate: 0.10,
    tax_amount: 65112,
    total_amount: 716232,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-7067',
    invoice_number: 'INV-2026-7067',
    voucher_code: 'P6-07101496-001',
    vendor_code: 'V3002',
    vendor_name: '大和商事株式会社',
    subtotal_amount: 1124945,
    tax_rate: 0.10,
    tax_amount: 112494,
    total_amount: 1237439,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-7068',
    invoice_number: 'INV-2026-7068',
    voucher_code: 'P6-07101496-002',
    vendor_code: 'V3001',
    vendor_name: '株式会社山田製作所',
    subtotal_amount: 340285,
    tax_rate: 0.10,
    tax_amount: 34028,
    total_amount: 374313,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  },
  {
    id: 'inv-7070',
    invoice_number: 'INV-2026-7070',
    voucher_code: 'P6-07101496-004',
    vendor_code: 'V3004',
    vendor_name: '関西物流サービス',
    subtotal_amount: 2948300,
    tax_rate: 0.10,
    tax_amount: 294830,
    total_amount: 3243130,
    status: 'PENDING',
    confirmation_comment: '',
    audit_flag: 'OK'
  }
];
