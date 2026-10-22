-- ==============================================================================
-- Enterprise Back-Office Automation Hub - Supabase PostgreSQL Schema
-- Supports Invoice Processing, HR Applications, Procurement Contracts & Audit Trail
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. VENDOR CONTRACT MASTER (月次定額取引先マスタ - getsujitsu_teigaku_torihikisaki_ichiran)
CREATE TABLE IF NOT EXISTS public.vendor_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_code VARCHAR(50) UNIQUE NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    base_amount NUMERIC(14,2) NOT NULL,
    tax_rate NUMERIC(5,4) DEFAULT 0.1000,
    tax_amount NUMERIC(14,2) NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL,
    service_scope TEXT,
    payment_terms VARCHAR(100) DEFAULT '月末締め翌月末払い',
    document_source VARCHAR(255) DEFAULT 'getsujitsu_teigaku_torihikisaki_ichiran.docx',
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. INVOICE PROCESSING QUEUE & RESULTS (請求書処理・承認台帳)
CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,      -- e.g. 'INV-2026-7344'
    voucher_code VARCHAR(50) NOT NULL,              -- e.g. 'P6-07010448-001'
    vendor_code VARCHAR(50) REFERENCES public.vendor_contracts(vendor_code) ON DELETE SET NULL,
    vendor_name VARCHAR(255) NOT NULL,
    subtotal_amount NUMERIC(14,2) NOT NULL,
    tax_rate NUMERIC(5,4) DEFAULT 0.1000,
    tax_amount NUMERIC(14,2) NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'APPROVED', 'DISCREPANCY', 'REJECTED')),
    confirmation_comment TEXT,
    puter_reasoning TEXT,                           -- Puter LLM 3-way match & anomaly assessment
    audit_flag VARCHAR(50) DEFAULT 'OK',            -- 'OK', 'RATE_MISMATCH', 'TAX_MISMATCH', 'UNLISTED_VENDOR'
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(100) DEFAULT 'SYSTEM_AUTOMATION',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. HR LEAVE & ATTENDANCE APPLICATIONS (HR人事給与システム - 勤怠・休暇申請)
CREATE TABLE IF NOT EXISTS public.hr_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id VARCHAR(50) UNIQUE NOT NULL,     -- e.g. 'APP-2026-0448'
    voucher_code VARCHAR(50) NOT NULL,              -- e.g. 'P2-07046495-012'
    employee_id VARCHAR(50) NOT NULL,
    employee_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    application_type VARCHAR(100) NOT NULL,         -- 'フレックス変更申請', '特別休暇（慶弔）', '代休申請', '年次有給休暇'
    target_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'APPROVED', 'REJECTED')),
    confirmation_comment TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. PROCUREMENT & CONTRACT AMENDMENTS (受発注在庫管理システム - 契約管理)
CREATE TABLE IF NOT EXISTS public.procurement_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id VARCHAR(50) UNIQUE NOT NULL,
    voucher_code VARCHAR(50) NOT NULL,              -- e.g. 'P12-07046495-012', 'P13-07088456-012'
    contract_type VARCHAR(100) NOT NULL,            -- '取引基本契約 (新規締結)', '売買契約 (変更)'
    vendor_name VARCHAR(255) NOT NULL,
    representative_name VARCHAR(100),
    effective_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'APPROVED', 'REJECTED')),
    confirmation_comment TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. AUTOMATION EXECUTION RUNS (バッチ実行履歴 & KPIログ)
CREATE TABLE IF NOT EXISTS public.automation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    process_type VARCHAR(100) NOT NULL,             -- 'INVOICE_PROCESSING', 'HR_LEAVE', 'PROCUREMENT_CONTRACT'
    total_processed INT NOT NULL DEFAULT 0,
    approved_count INT NOT NULL DEFAULT 0,
    discrepancy_count INT NOT NULL DEFAULT 0,
    execution_duration_ms INT NOT NULL DEFAULT 0,
    time_saved_seconds NUMERIC(10,2) DEFAULT 0.00,
    triggered_by VARCHAR(100) DEFAULT 'WEB_AUTOMATION_HUB',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. SYSTEM AUDIT TRAIL (操作監査・証跡記録)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES public.automation_runs(id) ON DELETE SET NULL,
    entity_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    comment_injected TEXT,
    verification_source VARCHAR(255),
    puter_ai_thought TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- INITIAL SEED DATA: GROUND TRUTH FROM DATASET B (MONTHLY FIXED VENDORS)
-- ==============================================================================

INSERT INTO public.vendor_contracts (vendor_code, vendor_name, base_amount, tax_rate, tax_amount, total_amount, service_scope)
VALUES 
('V3001', '株式会社山田製作所', 340285.00, 0.1000, 34028.00, 374313.00, '定期機械保守・プレス金型メンテナンス'),
('V3002', '大和商事株式会社', 1124945.00, 0.1000, 112494.00, 1237439.00, 'オフィス消耗品・基幹物流パレット定額供給'),
('V3003', '東京電子工業株式会社', 478182.00, 0.1000, 47818.00, 526000.00, '基板定期検査・ファームウェアアップデート'),
('V3004', '関西物流サービス', 2948300.00, 0.1000, 294830.00, 3243130.00, '西日本エリア定期幹線輸送便 (便数保証)'),
('V3005', 'グローバルテック合同会社', 651120.00, 0.1000, 65112.00, 716232.00, 'クラウド基幹インフラ24/365保守監視'),
('V3006', '北陸部品工業株式会社', 413753.00, 0.1000, 41375.00, 455128.00, '精密成型部品定額納入'),
('V3007', '福岡システム設計', 1532168.00, 0.1000, 153216.00, 1685384.00, '生産管理サブシステム運用サポートSE常駐'),
('V3008', '沖縄物流センター', 273839.00, 0.1000, 27384.00, 301223.00, '南西諸島定期海上コンテナ輸送ハブ中継')
ON CONFLICT (vendor_code) DO UPDATE SET 
    base_amount = EXCLUDED.base_amount,
    tax_amount = EXCLUDED.tax_amount,
    total_amount = EXCLUDED.total_amount;

-- Row Level Security (RLS) - Permissive for authenticated & anon app demo
ALTER TABLE public.vendor_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hr_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read-write for demo" ON public.vendor_contracts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for demo" ON public.invoices FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for demo" ON public.hr_applications FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for demo" ON public.procurement_contracts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for demo" ON public.automation_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for demo" ON public.audit_logs FOR ALL USING (true) WITH CHECK (true);
