// ==============================================================================
// Data Models & Type Definitions for Enterprise Automation Hub
// ==============================================================================

export type ProcessType = 
  | 'INVOICE_PROCESSING'    // 財務会計: 請求書承認・3者照合
  | 'HR_LEAVE_ATTENDANCE'   // HR人事: 勤怠・休暇申請 (代休・特別休暇・フレックス)
  | 'PROCUREMENT_CONTRACT'  // 受発注: 取引基本契約・売買契約変更
  | 'SALARY_ADJUSTMENT';    // 給与項目: 扶養控除・残業手当・役職手当

export type ApprovalStatus = 'PENDING' | 'PROCESSING' | 'APPROVED' | 'DISCREPANCY' | 'REJECTED';

export type AuditFlag = 
  | 'OK'
  | 'RATE_MISMATCH'
  | 'TAX_MISMATCH'
  | 'UNLISTED_VENDOR'
  | 'MISSING_VOUCHER'
  | 'DOCUMENT_EXPIRATION';

export interface VendorContract {
  id: string;
  vendor_code: string;       // e.g. V3005
  vendor_name: string;       // e.g. グローバルテック合同会社
  base_amount: number;       // 税抜基本契約金額
  tax_rate: number;          // 消費税率 0.10
  tax_amount: number;        // 消費税額
  total_amount: number;      // 税込契約金額
  service_scope: string;     // 委託業務範囲 / 契約内容
  payment_terms: string;     // 支払条件
  document_source: string;   // getsujitsu_teigaku_torihikisaki_ichiran.docx
  status: 'ACTIVE' | 'EXPIRED' | 'UNDER_REVIEW';
}

export interface Invoice {
  id: string;
  invoice_number: string;    // e.g. INV-2026-7344
  voucher_code: string;      // e.g. P6-07010448-001
  vendor_code: string;       // e.g. V3005
  vendor_name: string;       // e.g. グローバルテック合同会社
  subtotal_amount: number;   // 請求税抜額
  tax_rate: number;          // 0.10
  tax_amount: number;        // 消費税額
  total_amount: number;      // 請求税込合計額
  status: ApprovalStatus;
  confirmation_comment: string; // 照合確認コメント (41-43文字)
  audit_flag: AuditFlag;
  puter_reasoning?: string;  // Puter LLM による推論・照合結果解説
  processed_at?: string;     // 処理完了タイムスタンプ
  cycle_time_seconds?: number; // 処理時間 (自動化なら 0.3s - 0.5s)
  line_items?: InvoiceLineItem[];
}

export interface InvoiceLineItem {
  item_code: string;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

export interface HRApplication {
  id: string;
  application_id: string;
  voucher_code: string;      // e.g. P2-07046495-012
  employee_id: string;
  employee_name: string;
  department: string;
  application_type: 'フレックス変更申請' | '特別休暇（慶弔）' | '代休申請' | '年次有給休暇';
  target_date: string;
  status: ApprovalStatus;
  confirmation_comment: string;
  processed_at?: string;
}

export interface ProcurementContract {
  id: string;
  contract_id: string;
  voucher_code: string;      // e.g. P12-07046495-012
  contract_type: '取引基本契約 (新規締結)' | '売買契約 (変更)' | '契約解除手続';
  vendor_name: string;
  representative_name: string;
  effective_date: string;
  status: ApprovalStatus;
  confirmation_comment: string;
  processed_at?: string;
}

export interface AutomationRun {
  id: string;
  process_type: ProcessType;
  total_processed: number;
  approved_count: number;
  discrepancy_count: number;
  execution_duration_ms: number;
  time_saved_seconds: number;
  timestamp: string;
  items_summary?: string;
}

export interface AuditLogEntry {
  id: string;
  run_id?: string;
  timestamp: string;
  entity_id: string;
  entity_type: string;
  action_type: string;
  comment_injected: string;
  verification_source: string;
  puter_ai_thought?: string;
  status: 'SUCCESS' | 'DISCREPANCY_FLAGGED' | 'ERROR';
}

export interface SupabaseConfig {
  url: string;
  anonKey: string;
  connected: boolean;
  lastSync?: string;
}

export interface PuterLLMStatus {
  available: boolean;
  model: string;
  reasoningCallsCount: number;
  lastResponseTimeMs: number;
}
