import { HRApplication, ProcurementContract } from '../types';

export const INITIAL_HR_APPLICATIONS: HRApplication[] = [
  {
    id: 'hr-001',
    application_id: 'APP-2026-0448-001',
    voucher_code: 'P2-07046495-001',
    employee_id: 'E1082',
    employee_name: '清水 祥平',
    department: '物流部・配車管理課',
    application_type: 'フレックス変更申請',
    target_date: '2026-07-11',
    status: 'PENDING',
    confirmation_comment: ''
  },
  {
    id: 'hr-002',
    application_id: 'APP-2026-0448-002',
    voucher_code: 'P2-07046495-002',
    employee_id: 'E1459',
    employee_name: '岡田 聡',
    department: '情報システム部・インフラ課',
    application_type: '特別休暇（慶弔）',
    target_date: '2026-07-14',
    status: 'PENDING',
    confirmation_comment: ''
  },
  {
    id: 'hr-003',
    application_id: 'APP-2026-0448-003',
    voucher_code: 'P2-07046495-003',
    employee_id: 'E2296',
    employee_name: '原田 直樹',
    department: '経理部・財務会計課',
    application_type: '代休申請',
    target_date: '2026-07-07',
    status: 'PENDING',
    confirmation_comment: ''
  },
  {
    id: 'hr-004',
    application_id: 'APP-2026-0448-004',
    voucher_code: 'P2-07046495-004',
    employee_id: 'E2297',
    employee_name: '原田 明美',
    department: '経営企画部',
    application_type: '年次有給休暇',
    target_date: '2026-07-20',
    status: 'PENDING',
    confirmation_comment: ''
  }
];

export const INITIAL_PROCUREMENT_CONTRACTS: ProcurementContract[] = [
  {
    id: 'proc-001',
    contract_id: 'CT-2026-0911',
    voucher_code: 'P12-07046495-012',
    contract_type: '取引基本契約 (新規締結)',
    vendor_name: '大和商事株式会社',
    representative_name: '代表取締役 山口 雅之',
    effective_date: '2026-08-01',
    status: 'PENDING',
    confirmation_comment: ''
  },
  {
    id: 'proc-002',
    contract_id: 'CT-2026-0912',
    voucher_code: 'P12-07046495-013',
    contract_type: '売買契約 (変更)',
    vendor_name: '関西物流サービス',
    representative_name: '代表取締役 高田 健次',
    effective_date: '2026-08-01',
    status: 'PENDING',
    confirmation_comment: ''
  },
  {
    id: 'proc-003',
    contract_id: 'CT-2026-0913',
    voucher_code: 'P13-07088456-012',
    contract_type: '契約解除手続',
    vendor_name: '北陸部品工業株式会社',
    representative_name: '代表取締役 田中 伸一',
    effective_date: '2026-08-31',
    status: 'PENDING',
    confirmation_comment: ''
  }
];
