import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { KpiStatsBar } from './components/KpiStatsBar';
import { ProcessSelector, MainTab } from './components/ProcessSelector';
import { InvoiceProcessingView } from './components/InvoiceProcessingView';
import { StepByStepSimulator } from './components/StepByStepSimulator';
import { DocumentsHubView } from './components/DocumentsHubView';
import { PuterConsoleView } from './components/PuterConsoleView';
import { SupabaseConfigModal } from './components/SupabaseConfigModal';
import { AuditTrailView } from './components/AuditTrailView';
import { HRApplicationsView } from './components/HRApplicationsView';
import { ProcurementContractsView } from './components/ProcurementContractsView';

import { INITIAL_INVOICES } from './data/sampleInvoices';
import { INITIAL_VENDOR_CONTRACTS } from './data/sampleVendors';
import { INITIAL_HR_APPLICATIONS, INITIAL_PROCUREMENT_CONTRACTS } from './data/sampleHRProcurement';

import { Invoice, VendorContract, HRApplication, ProcurementContract, AutomationRun, AuditLogEntry, SupabaseConfig } from './types';
import { processSingleInvoice, processAllInvoicesBatch, processHRApplicationBatch, processProcurementContractBatch } from './services/automationEngine';
import { getStoredSupabaseConfig, testSupabaseConnection } from './services/supabaseClient';
import { isPuterAvailable } from './services/puterLLM';

export function App() {
  // Core Entities State
  const [invoices, setInvoices] = useState<Invoice[]>(() => {
    const saved = localStorage.getItem('hub_invoices');
    return saved ? JSON.parse(saved) : INITIAL_INVOICES;
  });

  const [vendors, setVendors] = useState<VendorContract[]>(() => {
    const saved = localStorage.getItem('hub_vendors');
    return saved ? JSON.parse(saved) : INITIAL_VENDOR_CONTRACTS;
  });

  const [hrApplications, setHrApplications] = useState<HRApplication[]>(INITIAL_HR_APPLICATIONS);
  const [procurementContracts, setProcurementContracts] = useState<ProcurementContract[]>(INITIAL_PROCUREMENT_CONTRACTS);

  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [totalSavedSeconds, setTotalSavedSeconds] = useState<number>(() => {
    return (INITIAL_INVOICES.filter(i => i.status === 'APPROVED').length) * 31.8;
  });

  // UI Navigation & Modals
  const [activeTab, setActiveTab] = useState<MainTab>('INVOICE_PROCESSING');
  const [isSupabaseModalOpen, setIsSupabaseModalOpen] = useState<boolean>(false);
  const [simulationInvoice, setSimulationInvoice] = useState<Invoice>(invoices[0] || INITIAL_INVOICES[0]);

  // Batch Execution State
  const [isProcessingBatch, setIsProcessingBatch] = useState<boolean>(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; currentItem: string } | null>(null);

  // Connectivity State
  const [isPuterOnline, setIsPuterOnline] = useState<boolean>(false);
  const [supabaseConfig, setSupabaseConfig] = useState<SupabaseConfig>(() => {
    const stored = getStoredSupabaseConfig();
    return {
      url: stored.url,
      anonKey: stored.anonKey,
      connected: false
    };
  });

  // Save changes to localStorage
  useEffect(() => {
    localStorage.setItem('hub_invoices', JSON.stringify(invoices));
  }, [invoices]);

  useEffect(() => {
    localStorage.setItem('hub_vendors', JSON.stringify(vendors));
  }, [vendors]);

  // Check Puter and Supabase connection on load
  useEffect(() => {
    setIsPuterOnline(isPuterAvailable());

    if (supabaseConfig.url && supabaseConfig.anonKey) {
      testSupabaseConnection(supabaseConfig.url, supabaseConfig.anonKey).then(res => {
        if (res.success) {
          setSupabaseConfig(prev => ({ ...prev, connected: true }));
        }
      });
    }
  }, []);

  // Process single invoice
  const handleProcessSingleInvoice = async (invoice: Invoice, usePuter: boolean) => {
    const { updatedInvoice, auditLog } = await processSingleInvoice(invoice, vendors, usePuter);
    
    setInvoices(prev => prev.map(i => i.id === updatedInvoice.id ? updatedInvoice : i));
    setAuditLogs(prev => [auditLog, ...prev]);

    if (updatedInvoice.status === 'APPROVED') {
      setTotalSavedSeconds(prev => prev + 31.8);
    }
  };

  // Process all invoices batch
  const handleProcessBatch = async (usePuter: boolean) => {
    setIsProcessingBatch(true);
    setBatchProgress(null);

    try {
      const result = await processAllInvoicesBatch(
        invoices,
        vendors,
        (current, total, currentItem) => {
          setBatchProgress({ current, total, currentItem });
        },
        usePuter
      );

      setInvoices(result.updatedInvoices);
      setAuditLogs(prev => [...result.auditLogs, ...prev]);
      setTotalSavedSeconds(prev => prev + result.run.time_saved_seconds);
    } catch (err: any) {
      alert(`バッチ処理中にエラーが発生しました: ${err.message}`);
    } finally {
      setIsProcessingBatch(false);
      setBatchProgress(null);
    }
  };

  // HR batch & single
  const handleApproveAllHR = () => {
    const { updated, run } = processHRApplicationBatch(hrApplications);
    setHrApplications(updated);
    setTotalSavedSeconds(prev => prev + run.time_saved_seconds);
    const logs: AuditLogEntry[] = updated.map(a => ({
      id: `audit-hr-${Date.now()}-${a.id}`,
      timestamp: new Date().toISOString(),
      entity_id: a.application_id,
      entity_type: 'HR_LEAVE_APPLICATION',
      action_type: 'AUTO_APPROVE',
      comment_injected: a.confirmation_comment,
      verification_source: '就業規則・休暇マスタ',
      status: 'SUCCESS'
    }));
    setAuditLogs(prev => [...logs, ...prev]);
  };

  const handleApproveSingleHR = (id: string) => {
    setHrApplications(prev => prev.map(a => 
      a.id === id 
        ? { ...a, status: 'APPROVED', confirmation_comment: '就業規則適合確認済', processed_at: new Date().toISOString() } 
        : a
    ));
    setTotalSavedSeconds(prev => prev + 28.5);
  };

  // Procurement batch & single
  const handleApproveAllProc = () => {
    const { updated, run } = processProcurementContractBatch(procurementContracts);
    setProcurementContracts(updated);
    setTotalSavedSeconds(prev => prev + run.time_saved_seconds);
    const logs: AuditLogEntry[] = updated.map(c => ({
      id: `audit-proc-${Date.now()}-${c.id}`,
      timestamp: new Date().toISOString(),
      entity_id: c.contract_id,
      entity_type: 'PROCUREMENT_CONTRACT',
      action_type: 'AUTO_APPROVE',
      comment_injected: c.confirmation_comment,
      verification_source: '法務標準取引基本規程',
      status: 'SUCCESS'
    }));
    setAuditLogs(prev => [...logs, ...prev]);
  };

  const handleApproveSingleProc = (id: string) => {
    setProcurementContracts(prev => prev.map(c => 
      c.id === id 
        ? { ...c, status: 'APPROVED', confirmation_comment: '取引基本規程整合確認済', processed_at: new Date().toISOString() } 
        : c
    ));
    setTotalSavedSeconds(prev => prev + 45.0);
  };

  // Import handlers from Excel / Word
  const handleImportInvoices = (newInvoices: Partial<Invoice>[]) => {
    const formatted: Invoice[] = newInvoices.map((n, idx) => ({
      id: n.id || `imp-${Date.now()}-${idx}`,
      invoice_number: n.invoice_number || `INV-${1000 + idx}`,
      voucher_code: n.voucher_code || `P6-07010448-${100 + idx}`,
      vendor_code: n.vendor_code || '',
      vendor_name: n.vendor_name || '新規取引先',
      subtotal_amount: n.subtotal_amount || 0,
      tax_rate: n.tax_rate || 0.10,
      tax_amount: n.tax_amount || 0,
      total_amount: n.total_amount || 0,
      status: 'PENDING',
      confirmation_comment: '',
      audit_flag: 'OK'
    }));
    setInvoices(prev => [...formatted, ...prev]);
    setActiveTab('INVOICE_PROCESSING');
  };

  const handleImportVendors = (newVendors: Partial<VendorContract>[]) => {
    const formatted: VendorContract[] = newVendors.map((v, idx) => ({
      id: v.id || `imp-vc-${Date.now()}-${idx}`,
      vendor_code: v.vendor_code || `V${3100 + idx}`,
      vendor_name: v.vendor_name || '新規契約取引先',
      base_amount: v.base_amount || 0,
      tax_rate: 0.10,
      tax_amount: v.tax_amount || Math.floor((v.base_amount || 0) * 0.1),
      total_amount: v.total_amount || (v.base_amount || 0) * 1.1,
      service_scope: v.service_scope || 'Word抽出契約条項',
      payment_terms: v.payment_terms || '月末締め翌月末振込',
      document_source: 'アップロードWord文書',
      status: 'ACTIVE'
    }));
    setVendors(prev => [...formatted, ...prev]);
  };

  // Reset to Dataset B ground truth
  const handleResetData = () => {
    if (confirm('Dataset B の初期サンプルデータにリセットしますか？')) {
      localStorage.removeItem('hub_invoices');
      localStorage.removeItem('hub_vendors');
      setInvoices(INITIAL_INVOICES);
      setVendors(INITIAL_VENDOR_CONTRACTS);
      setHrApplications(INITIAL_HR_APPLICATIONS);
      setProcurementContracts(INITIAL_PROCUREMENT_CONTRACTS);
      setAuditLogs([]);
      setTotalSavedSeconds(INITIAL_INVOICES.filter(i => i.status === 'APPROVED').length * 31.8);
      alert('初期データにリセットしました。');
    }
  };

  const pendingInvoicesCount = invoices.filter(i => i.status === 'PENDING').length;
  const pendingHrCount = hrApplications.filter(a => a.status === 'PENDING').length;
  const pendingProcCount = procurementContracts.filter(c => c.status === 'PENDING').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      
      {/* Top Navbar */}
      <Navbar
        supabaseConfig={supabaseConfig}
        onOpenSupabaseModal={() => setIsSupabaseModalOpen(true)}
        onOpenDocsHub={() => setActiveTab('DOCUMENTS')}
        onOpenPuterConsole={() => setActiveTab('PUTER_CONSOLE')}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isPuterOnline={isPuterOnline}
        onResetData={handleResetData}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* KPI Performance Bar */}
        <KpiStatsBar
          invoices={invoices}
          totalSavedSeconds={totalSavedSeconds}
        />

        {/* Process Navigation Tabs */}
        <ProcessSelector
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          pendingInvoicesCount={pendingInvoicesCount}
          pendingHrCount={pendingHrCount}
          pendingProcCount={pendingProcCount}
        />

        {/* Dynamic Tab Views */}
        {activeTab === 'INVOICE_PROCESSING' && (
          <InvoiceProcessingView
            invoices={invoices}
            vendors={vendors}
            onProcessSingle={handleProcessSingleInvoice}
            onProcessBatch={handleProcessBatch}
            isProcessingBatch={isProcessingBatch}
            batchProgress={batchProgress}
            onSelectForSimulation={(inv) => {
              setSimulationInvoice(inv);
              setActiveTab('STEP_SIMULATOR');
            }}
          />
        )}

        {activeTab === 'HR_APPLICATIONS' && (
          <HRApplicationsView
            applications={hrApplications}
            onApproveAll={handleApproveAllHR}
            onApproveSingle={handleApproveSingleHR}
          />
        )}

        {activeTab === 'PROCUREMENT_CONTRACTS' && (
          <ProcurementContractsView
            contracts={procurementContracts}
            onApproveAll={handleApproveAllProc}
            onApproveSingle={handleApproveSingleProc}
          />
        )}

        {activeTab === 'STEP_SIMULATOR' && (
          <StepByStepSimulator
            invoice={simulationInvoice}
            vendor={vendors.find(v => v.vendor_name === simulationInvoice.vendor_name || v.vendor_code === simulationInvoice.vendor_code)}
            onApproveComplete={(approvedInv) => {
              setInvoices(prev => prev.map(i => i.id === approvedInv.id ? approvedInv : i));
              setTotalSavedSeconds(prev => prev + 31.8);
            }}
          />
        )}

        {activeTab === 'DOCUMENTS' && (
          <DocumentsHubView
            invoices={invoices}
            vendors={vendors}
            onImportInvoices={handleImportInvoices}
            onImportVendors={handleImportVendors}
          />
        )}

        {activeTab === 'PUTER_CONSOLE' && (
          <PuterConsoleView
            invoices={invoices}
            vendors={vendors}
          />
        )}

        {activeTab === 'AUDIT_TRAIL' && (
          <AuditTrailView
            logs={auditLogs}
          />
        )}

      </main>

      {/* Supabase Configuration & Migration Modal */}
      <SupabaseConfigModal
        isOpen={isSupabaseModalOpen}
        onClose={() => setIsSupabaseModalOpen(false)}
        config={supabaseConfig}
        onConfigUpdated={setSupabaseConfig}
        invoices={invoices}
        vendors={vendors}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Enterprise Back-Office Automation Hub &bull; Dataset B Multi-Process Solution</span>
          <span>Puter.js LLM &bull; Mammoth Word &bull; SheetJS Excel &bull; Supabase PostgreSQL</span>
        </div>
      </footer>

    </div>
  );
}
export default App;
