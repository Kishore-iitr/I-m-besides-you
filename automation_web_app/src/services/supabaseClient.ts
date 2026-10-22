import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { Invoice, VendorContract, AutomationRun, AuditLogEntry } from '../types';

const STORAGE_KEY_URL = 'enterprise_hub_supabase_url';
const STORAGE_KEY_KEY = 'enterprise_hub_supabase_key';

let cachedClient: SupabaseClient | null = null;
let cachedUrl = '';
let cachedKey = '';

export function getStoredSupabaseConfig(): { url: string; anonKey: string } {
  const envUrl = (import.meta as any).env?.VITE_SUPABASE_URL || '';
  const envKey = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY || '';

  const storedUrl = localStorage.getItem(STORAGE_KEY_URL) || envUrl;
  const storedKey = localStorage.getItem(STORAGE_KEY_KEY) || envKey;

  return { url: storedUrl, anonKey: storedKey };
}

export function saveSupabaseConfig(url: string, anonKey: string): void {
  localStorage.setItem(STORAGE_KEY_URL, url.trim());
  localStorage.setItem(STORAGE_KEY_KEY, anonKey.trim());
  cachedClient = null; // force re-initialization
}

export function getSupabase(): SupabaseClient | null {
  const { url, anonKey } = getStoredSupabaseConfig();
  if (!url || !anonKey) {
    return null;
  }

  if (cachedClient && cachedUrl === url && cachedKey === anonKey) {
    return cachedClient;
  }

  try {
    cachedClient = createClient(url, anonKey, {
      auth: { persistSession: false }
    });
    cachedUrl = url;
    cachedKey = anonKey;
    return cachedClient;
  } catch (err) {
    console.error('Failed to initialize Supabase client:', err);
    return null;
  }
}

export async function testSupabaseConnection(url?: string, anonKey?: string): Promise<{ success: boolean; message: string; tablesExist?: boolean }> {
  const targetUrl = url || getStoredSupabaseConfig().url;
  const targetKey = anonKey || getStoredSupabaseConfig().anonKey;

  if (!targetUrl || !targetKey) {
    return { success: false, message: 'Supabase URL または Anon Key が未設定です。設定画面より入力してください。' };
  }

  try {
    const tempClient = createClient(targetUrl, targetKey, {
      auth: { persistSession: false }
    });

    // Try reading vendor_contracts table
    const { data, error } = await tempClient.from('vendor_contracts').select('count', { count: 'exact', head: true });
    
    if (error) {
      if (error.code === '42P01') { // relation does not exist
        return { 
          success: true, 
          tablesExist: false, 
          message: 'PostgreSQL への接続は成功しましたが、テーブルが未作成です。提供された supabase_schema.sql を Supabase SQL Editor で実行してください。' 
        };
      }
      return { success: false, message: `接続エラー: ${error.message}` };
    }

    return { 
      success: true, 
      tablesExist: true, 
      message: 'Supabase PostgreSQL への接続およびテーブル照会に成功しました。' 
    };
  } catch (err: any) {
    return { success: false, message: `ネットワークまたは構成エラー: ${err.message || err}` };
  }
}

export async function syncInvoicesToSupabase(invoices: Invoice[]): Promise<boolean> {
  const client = getSupabase();
  if (!client) return false;

  try {
    const payload = invoices.map(inv => ({
      invoice_number: inv.invoice_number,
      voucher_code: inv.voucher_code,
      vendor_code: inv.vendor_code,
      vendor_name: inv.vendor_name,
      subtotal_amount: inv.subtotal_amount,
      tax_rate: inv.tax_rate,
      tax_amount: inv.tax_amount,
      total_amount: inv.total_amount,
      status: inv.status,
      confirmation_comment: inv.confirmation_comment,
      puter_reasoning: inv.puter_reasoning || null,
      audit_flag: inv.audit_flag,
      approved_at: inv.processed_at || null,
      updated_at: new Date().toISOString()
    }));

    const { error } = await client
      .from('invoices')
      .upsert(payload, { onConflict: 'invoice_number' });

    if (error) {
      console.warn('Supabase invoice upsert warning:', error.message);
      return false;
    }
    return true;
  } catch (e) {
    console.error('syncInvoicesToSupabase error:', e);
    return false;
  }
}

export async function syncVendorsToSupabase(vendors: VendorContract[]): Promise<boolean> {
  const client = getSupabase();
  if (!client) return false;

  try {
    const payload = vendors.map(v => ({
      vendor_code: v.vendor_code,
      vendor_name: v.vendor_name,
      base_amount: v.base_amount,
      tax_rate: v.tax_rate,
      tax_amount: v.tax_amount,
      total_amount: v.total_amount,
      service_scope: v.service_scope,
      payment_terms: v.payment_terms,
      document_source: v.document_source,
      status: v.status,
      updated_at: new Date().toISOString()
    }));

    const { error } = await client
      .from('vendor_contracts')
      .upsert(payload, { onConflict: 'vendor_code' });

    if (error) {
      console.warn('Supabase vendor upsert warning:', error.message);
      return false;
    }
    return true;
  } catch (e) {
    console.error('syncVendorsToSupabase error:', e);
    return false;
  }
}

export async function logRunToSupabase(run: AutomationRun): Promise<boolean> {
  const client = getSupabase();
  if (!client) return false;

  try {
    const { error } = await client.from('automation_runs').insert({
      id: run.id,
      process_type: run.process_type,
      total_processed: run.total_processed,
      approved_count: run.approved_count,
      discrepancy_count: run.discrepancy_count,
      execution_duration_ms: run.execution_duration_ms,
      time_saved_seconds: run.time_saved_seconds,
      created_at: run.timestamp
    });

    return !error;
  } catch (e) {
    console.error('logRunToSupabase error:', e);
    return false;
  }
}

export async function logAuditToSupabase(log: AuditLogEntry): Promise<boolean> {
  const client = getSupabase();
  if (!client) return false;

  try {
    const { error } = await client.from('audit_logs').insert({
      id: log.id,
      run_id: log.run_id || null,
      entity_id: log.entity_id,
      entity_type: log.entity_type,
      action_type: log.action_type,
      comment_injected: log.comment_injected,
      verification_source: log.verification_source,
      puter_ai_thought: log.puter_ai_thought || null,
      created_at: log.timestamp
    });

    return !error;
  } catch (e) {
    console.error('logAuditToSupabase error:', e);
    return false;
  }
}
