import React, { useState } from 'react';
import { 
  Database, 
  Check, 
  Copy, 
  ExternalLink, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Key, 
  Globe, 
  UploadCloud 
} from 'lucide-react';
import { SupabaseConfig, Invoice, VendorContract } from '../types';
import { 
  saveSupabaseConfig, 
  testSupabaseConnection, 
  syncInvoicesToSupabase, 
  syncVendorsToSupabase 
} from '../services/supabaseClient';

interface SupabaseConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: SupabaseConfig;
  onConfigUpdated: (newConfig: SupabaseConfig) => void;
  invoices: Invoice[];
  vendors: VendorContract[];
}

export const SupabaseConfigModal: React.FC<SupabaseConfigModalProps> = ({
  isOpen,
  onClose,
  config,
  onConfigUpdated,
  invoices,
  vendors
}) => {
  if (!isOpen) return null;

  const [url, setUrl] = useState<string>(config.url);
  const [anonKey, setAnonKey] = useState<string>(config.anonKey);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; tablesExist?: boolean } | null>(null);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [copiedSql, setCopiedSql] = useState<boolean>(false);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testSupabaseConnection(url, anonKey);
      setTestResult(res);
      if (res.success) {
        saveSupabaseConfig(url, anonKey);
        onConfigUpdated({
          url,
          anonKey,
          connected: true,
          lastSync: new Date().toISOString()
        });
      }
    } catch (e: any) {
      setTestResult({ success: false, message: e.message || '接続失敗' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAndSync = async () => {
    saveSupabaseConfig(url, anonKey);
    setIsSyncing(true);
    try {
      const invOk = await syncInvoicesToSupabase(invoices);
      const venOk = await syncVendorsToSupabase(vendors);
      if (invOk && venOk) {
        alert('Supabase PostgreSQL へのデータ同期（請求書 & 取引先マスタ）が完了しました。');
        onConfigUpdated({
          url,
          anonKey,
          connected: true,
          lastSync: new Date().toISOString()
        });
        onClose();
      } else {
        alert('一部テーブルへの同期で警告が発生しました。テーブル定義が正しいかご確認ください。');
      }
    } catch (err: any) {
      alert(`同期エラー: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCopySchema = () => {
    const sqlScript = `-- Supabase PostgreSQL Schema Migration
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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

CREATE TABLE IF NOT EXISTS public.invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    voucher_code VARCHAR(50) NOT NULL,
    vendor_code VARCHAR(50) REFERENCES public.vendor_contracts(vendor_code) ON DELETE SET NULL,
    vendor_name VARCHAR(255) NOT NULL,
    subtotal_amount NUMERIC(14,2) NOT NULL,
    tax_rate NUMERIC(5,4) DEFAULT 0.1000,
    tax_amount NUMERIC(14,2) NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    confirmation_comment TEXT,
    puter_reasoning TEXT,
    audit_flag VARCHAR(50) DEFAULT 'OK',
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(100) DEFAULT 'SYSTEM_AUTOMATION',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.automation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    process_type VARCHAR(100) NOT NULL,
    total_processed INT NOT NULL DEFAULT 0,
    approved_count INT NOT NULL DEFAULT 0,
    discrepancy_count INT NOT NULL DEFAULT 0,
    execution_duration_ms INT NOT NULL DEFAULT 0,
    time_saved_seconds NUMERIC(10,2) DEFAULT 0.00,
    triggered_by VARCHAR(100) DEFAULT 'WEB_AUTOMATION_HUB',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

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

ALTER TABLE public.vendor_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public demo" ON public.vendor_contracts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public demo" ON public.invoices FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public demo" ON public.automation_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public demo" ON public.audit_logs FOR ALL USING (true) WITH CHECK (true);
`;
    navigator.clipboard.writeText(sqlScript);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>Supabase PostgreSQL 接続設定</span>
                {config.connected ? (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                    接続中
                  </span>
                ) : (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                    オフライン/ローカルモード
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-400">
                本番データベース（PostgreSQL）とリアルタイム連携し、承認ログ・取引先台帳を永続化します
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white text-sm"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">

          {/* Explanation Banner */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 space-y-1.5">
            <div className="font-semibold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Supabase の環境変数（URL &amp; Key）をいつでも接続可能</span>
            </div>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              ユーザー様がいつでも Supabase の Project URL および anon key（または service role key）を入力・更新できるよう設計されています。
              未接続時はブラウザ内インメモリ／LocalStorage DBで全機能が安全に動作します。
            </p>
          </div>

          {/* Form Fields */}
          <div className="space-y-4">
            
            {/* Supabase URL */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-sky-400" />
                <span>Supabase Project URL (SUPABASE_URL):</span>
              </label>
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://your-project.supabase.co"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Supabase Anon Key */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-amber-400" />
                <span>Supabase Anon Public API Key (SUPABASE_ANON_KEY):</span>
              </label>
              <input
                type="password"
                value={anonKey}
                onChange={e => setAnonKey(e.target.value)}
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

          </div>

          {/* Connection Test Response Banner */}
          {testResult && (
            <div className={`p-3.5 rounded-xl border text-xs ${
              testResult.success
                ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
            }`}>
              <div className="font-bold flex items-center gap-1.5">
                {testResult.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                <span>{testResult.success ? '接続テスト成功' : '接続テスト失敗'}</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-300 leading-relaxed font-mono">
                {testResult.message}
              </div>
            </div>
          )}

          {/* Schema Migration Copy Card */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3">
            <div>
              <span className="font-semibold text-white block">PostgreSQL スキーマ定義 (supabase_schema.sql)</span>
              <span className="text-[11px] text-slate-400">
                Supabase の SQL Editor で1クリック実行するだけで全テーブルとRLSが作成されます
              </span>
            </div>

            <button
              onClick={handleCopySchema}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-all"
            >
              {copiedSql ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedSql ? 'コピー完了' : 'SQL をコピー'}</span>
            </button>
          </div>

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between bg-slate-950">
          <button
            onClick={handleTestConnection}
            disabled={isTesting || !url || !anonKey}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
          >
            {isTesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
            <span>接続テストを実行</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
            >
              閉じる
            </button>

            <button
              onClick={handleSaveAndSync}
              disabled={isSyncing || !url || !anonKey}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/30 flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
            >
              {isSyncing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
              <span>保存して全データを同期</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
