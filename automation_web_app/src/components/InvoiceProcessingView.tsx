import React, { useState } from 'react';
import { 
  Play, 
  Download, 
  Search, 
  Filter, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  FileText, 
  Sparkles, 
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Check,
  RefreshCw,
  Building
} from 'lucide-react';
import { Invoice, VendorContract } from '../types';
import { exportInvoicesToExcel } from '../services/excelService';

interface InvoiceProcessingViewProps {
  invoices: Invoice[];
  vendors: VendorContract[];
  onProcessSingle: (invoice: Invoice, usePuter: boolean) => Promise<void>;
  onProcessBatch: (usePuter: boolean) => Promise<void>;
  isProcessingBatch: boolean;
  batchProgress: { current: number; total: number; currentItem: string } | null;
  onSelectForSimulation: (invoice: Invoice) => void;
}

export const InvoiceProcessingView: React.FC<InvoiceProcessingViewProps> = ({
  invoices,
  vendors,
  onProcessSingle,
  onProcessBatch,
  isProcessingBatch,
  batchProgress,
  onSelectForSimulation
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PENDING' | 'APPROVED' | 'DISCREPANCY'>('ALL');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [usePuterLLM, setUsePuterLLM] = useState<boolean>(true);
  const [processingSingleId, setProcessingSingleId] = useState<string | null>(null);

  // Filter invoices
  const filteredInvoices = invoices.filter(inv => {
    const matchesSearch = 
      inv.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.vendor_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.voucher_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.vendor_code.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = 
      statusFilter === 'ALL' ? true : inv.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const pendingCount = invoices.filter(i => i.status === 'PENDING').length;

  const handleSingleClick = async (invoice: Invoice) => {
    setProcessingSingleId(invoice.id);
    try {
      await onProcessSingle(invoice, usePuterLLM);
    } finally {
      setProcessingSingleId(null);
    }
  };

  const getMatchedVendor = (invoice: Invoice): VendorContract | undefined => {
    return vendors.find(v => 
      v.vendor_name === invoice.vendor_name || 
      (v.vendor_code && invoice.vendor_code && v.vendor_code === invoice.vendor_code)
    );
  };

  return (
    <div className="space-y-4">

      {/* Action Toolbar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800">
        
        {/* Left: Search & Filter */}
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="請求書番号・社名・伝票コードで検索..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-1 border border-slate-800 rounded-lg p-1 bg-slate-950">
            {(['ALL', 'PENDING', 'APPROVED', 'DISCREPANCY'] as const).map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                  statusFilter === status
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {status === 'ALL' && '全件'}
                {status === 'PENDING' && '未処理'}
                {status === 'APPROVED' && '承認済'}
                {status === 'DISCREPANCY' && '要確認'}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Automation Controls */}
        <div className="flex items-center gap-2.5 justify-end">
          
          {/* Puter LLM Reasoning Toggle */}
          <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 cursor-pointer text-xs text-slate-300 hover:border-slate-700">
            <input
              type="checkbox"
              checked={usePuterLLM}
              onChange={e => setUsePuterLLM(e.target.checked)}
              className="rounded border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0 bg-slate-900"
            />
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Puter LLM 推論連携</span>
          </label>

          {/* Export to Excel */}
          <button
            onClick={() => exportInvoicesToExcel(invoices)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 hover:bg-slate-800 text-xs text-slate-200 font-medium transition-all"
            title="照合結果台帳をExcel形式でダウンロード"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Excel台帳出力</span>
          </button>

          {/* Main Batch Execution Button */}
          <button
            onClick={() => onProcessBatch(usePuterLLM)}
            disabled={isProcessingBatch || pendingCount === 0}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shadow-lg transition-all ${
              pendingCount === 0
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white shadow-indigo-600/30 active:scale-95'
            }`}
          >
            {isProcessingBatch ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>自動処理中 ({batchProgress?.current}/{batchProgress?.total})...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white text-white" />
                <span>未処理 {pendingCount}件 一括自動承認</span>
              </>
            )}
          </button>

        </div>

      </div>

      {/* Batch Processing Live Progress Banner */}
      {isProcessingBatch && batchProgress && (
        <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-700/50 flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-ping"></div>
            <span className="text-indigo-200 font-medium">
              現在照合中: <strong className="text-white">{batchProgress.currentItem}</strong>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-indigo-300">
              進捗: {batchProgress.current} / {batchProgress.total} 件
            </span>
            <div className="w-32 bg-slate-800 rounded-full h-2 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-indigo-500 to-sky-400 h-full transition-all duration-150"
                style={{ width: `${(batchProgress.current / batchProgress.total) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {/* Main Invoices Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-medium">
                <th className="py-3 px-4">請求書番号 / 伝票</th>
                <th className="py-3 px-4">取引先名 (Wordマスタ照合)</th>
                <th className="py-3 px-4 text-right">請求税抜額</th>
                <th className="py-3 px-4 text-right">消費税 (10%)</th>
                <th className="py-3 px-4 text-right">請求税込合計</th>
                <th className="py-3 px-4 text-center">ステータス</th>
                <th className="py-3 px-4">確認コメント (41-43文字)</th>
                <th className="py-3 px-4 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    該当する請求書伝票は見つかりませんでした。
                  </td>
                </tr>
              ) : (
                filteredInvoices.map(invoice => {
                  const matchedContract = getMatchedVendor(invoice);
                  const isProcessingThis = processingSingleId === invoice.id;

                  return (
                    <tr 
                      key={invoice.id} 
                      className={`hover:bg-slate-800/40 transition-colors ${
                        selectedInvoice?.id === invoice.id ? 'bg-indigo-950/20' : ''
                      }`}
                    >
                      {/* Invoice ID & Voucher */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white flex items-center gap-1.5">
                          <span>{invoice.invoice_number}</span>
                          {invoice.cycle_time_seconds && (
                            <span className="text-[10px] text-sky-400 bg-sky-950/40 px-1.5 py-0.2 rounded border border-sky-800/40">
                              {invoice.cycle_time_seconds}s
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {invoice.voucher_code}
                        </div>
                      </td>

                      {/* Vendor Name & Master Match Pill */}
                      <td className="py-3 px-4">
                        <div className="font-medium text-white flex items-center gap-1.5">
                          <span>{invoice.vendor_name}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1">
                          {matchedContract ? (
                            <span className="text-emerald-400 flex items-center gap-0.5">
                              <Check className="w-3 h-3" />
                              Word定額マスタ登録済 ({matchedContract.vendor_code})
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-0.5">
                              <AlertTriangle className="w-3 h-3" />
                              定額マスタ未登録
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Subtotal */}
                      <td className="py-3 px-4 text-right font-mono text-slate-300">
                        ¥{invoice.subtotal_amount.toLocaleString()}
                      </td>

                      {/* Tax (10%) */}
                      <td className="py-3 px-4 text-right font-mono text-slate-400">
                        ¥{invoice.tax_amount.toLocaleString()}
                      </td>

                      {/* Total */}
                      <td className="py-3 px-4 text-right font-mono font-bold text-white">
                        ¥{invoice.total_amount.toLocaleString()}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 text-center">
                        {invoice.status === 'APPROVED' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
                            <CheckCircle2 className="w-3 h-3" />
                            承認済
                          </span>
                        )}
                        {invoice.status === 'PENDING' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-950/40 text-amber-400 border border-amber-800/40">
                            <Clock className="w-3 h-3" />
                            未処理
                          </span>
                        )}
                        {invoice.status === 'DISCREPANCY' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-rose-950/50 text-rose-400 border border-rose-800/50">
                            <AlertTriangle className="w-3 h-3" />
                            要確認
                          </span>
                        )}
                      </td>

                      {/* Injected Audit Comment */}
                      <td className="py-3 px-4 max-w-xs truncate text-[11px] text-slate-300">
                        {invoice.confirmation_comment ? (
                          <span className="text-emerald-300/90" title={invoice.confirmation_comment}>
                            {invoice.confirmation_comment}
                          </span>
                        ) : (
                          <span className="text-slate-500 italic">未挿入 (承認時に自動注入)</span>
                        )}
                      </td>

                      {/* Action Buttons */}
                      <td className="py-3 px-4 text-right space-x-1.5 whitespace-nowrap">
                        
                        {/* Detail / Puter Reasoning Modal */}
                        <button
                          onClick={() => setSelectedInvoice(invoice)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium transition-all"
                          title="照合内訳 & Puter推論思考を表示"
                        >
                          詳細
                        </button>

                        {/* Interactive Replay / Simulator */}
                        <button
                          onClick={() => onSelectForSimulation(invoice)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-300 text-[11px] font-medium transition-all"
                          title="テレメトリ操作手順を再現"
                        >
                          再現
                        </button>

                        {/* Single Auto-Approve Button */}
                        {invoice.status !== 'APPROVED' && (
                          <button
                            onClick={() => handleSingleClick(invoice)}
                            disabled={isProcessingThis || isProcessingBatch}
                            className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-[11px] font-semibold transition-all inline-flex items-center gap-1 shadow-sm"
                          >
                            {isProcessingThis ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : (
                              <ShieldCheck className="w-3 h-3" />
                            )}
                            承認
                          </button>
                        )}

                      </td>

                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invoice Detail & 3-Way Match Inspection Drawer / Modal */}
      {selectedInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span>伝票詳細照合 — {selectedInvoice.invoice_number}</span>
                    <span className="text-xs font-mono text-slate-400">({selectedInvoice.voucher_code})</span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    ERP Webポータル (Edge) × Word定額契約マスタ 3者照合検証
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedInvoice(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Modal Body: 3-Way Reconciliation Comparison */}
            <div className="p-6 overflow-y-auto space-y-6">
              
              {/* Comparison Cards: Invoice vs Word Contract Master */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Card A: Invoice Data (From ERP Queue) */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300 border-b border-slate-800 pb-2">
                    <span className="flex items-center gap-1.5 text-sky-400">
                      <Building className="w-4 h-4" />
                      受領請求書データ (財務会計システム)
                    </span>
                    <span className="text-[10px] text-slate-500">Port 5133</span>
                  </div>

                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">取引先名称:</span>
                      <span className="text-white font-medium">{selectedInvoice.vendor_name}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">取引先コード:</span>
                      <span className="text-slate-300 font-mono">{selectedInvoice.vendor_code || '未割当'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">請求税抜金額:</span>
                      <span className="text-white font-mono font-bold">¥{selectedInvoice.subtotal_amount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">消費税額 (10%):</span>
                      <span className="text-slate-300 font-mono">¥{selectedInvoice.tax_amount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">請求税込合計:</span>
                      <span className="text-emerald-400 font-mono font-bold text-sm">¥{selectedInvoice.total_amount.toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Card B: Word Master Contract Record */}
                {(() => {
                  const contract = getMatchedVendor(selectedInvoice);
                  const isMatch = contract && Math.abs(contract.base_amount - selectedInvoice.subtotal_amount) < 1;

                  return (
                    <div className={`p-4 rounded-xl border space-y-3 ${
                      isMatch 
                        ? 'bg-slate-950 border-emerald-800/40' 
                        : 'bg-rose-950/20 border-rose-800/40'
                    }`}>
                      <div className="flex items-center justify-between text-xs font-bold text-slate-300 border-b border-slate-800 pb-2">
                        <span className="flex items-center gap-1.5 text-emerald-400">
                          <FileText className="w-4 h-4" />
                          Word定額取引先マスタ契約情報
                        </span>
                        <span className="text-[10px] text-slate-500">getsujitsu_teigaku_torihikisaki_ichiran</span>
                      </div>

                      {contract ? (
                        <div className="space-y-1.5 text-xs">
                          <div className="flex justify-between py-1 border-b border-slate-900">
                            <span className="text-slate-400">契約取引先名:</span>
                            <span className="text-white font-medium">{contract.vendor_name}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-900">
                            <span className="text-slate-400">マスタコード:</span>
                            <span className="text-slate-300 font-mono">{contract.vendor_code}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-900">
                            <span className="text-slate-400">月次定額基本料:</span>
                            <span className="text-white font-mono font-bold">¥{contract.base_amount.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-900">
                            <span className="text-slate-400">契約消費税額:</span>
                            <span className="text-slate-300 font-mono">¥{contract.tax_amount.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-900">
                            <span className="text-slate-400">契約税込月額:</span>
                            <span className="text-emerald-400 font-mono font-bold text-sm">¥{contract.total_amount.toLocaleString()}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="p-4 text-center text-xs text-rose-300 bg-rose-950/40 rounded-lg">
                          該当取引先の月次契約レコードがWordマスタ内に見つかりません。
                        </div>
                      )}
                    </div>
                  );
                })()}

              </div>

              {/* Puter LLM Reasoning Box */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950 border border-indigo-800/40 space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-indigo-300">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    Puter LLM 照合推論エンジン思考ログ
                  </span>
                  <span className="text-[10px] text-indigo-400/80">Claude-3.5-Sonnet / Rule Engine</span>
                </div>

                <div className="p-3 bg-slate-950/80 rounded-lg border border-indigo-900/40 text-xs text-slate-200 whitespace-pre-line leading-relaxed font-mono">
                  {selectedInvoice.puter_reasoning || '推論ログは自動承認実行時に生成・記録されます。'}
                </div>
              </div>

              {/* Mandatory Comment Preview Box */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">
                    注入予定の必須監査確認コメント (41〜43文字規格):
                  </span>
                  <span className="text-[11px] font-mono text-emerald-400">
                    文字数: {(selectedInvoice.confirmation_comment || '月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済').length} 文字
                  </span>
                </div>

                <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs font-mono text-emerald-300 select-all">
                  {selectedInvoice.confirmation_comment || '月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済'}
                </div>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 flex items-center justify-between bg-slate-950">
              <button
                onClick={() => {
                  onSelectForSimulation(selectedInvoice);
                  setSelectedInvoice(null);
                }}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 text-xs font-medium transition-all flex items-center gap-1.5"
              >
                <span>テレメトリ操作シミュレータで再現</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedInvoice(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  閉じる
                </button>

                {selectedInvoice.status !== 'APPROVED' && (
                  <button
                    onClick={async () => {
                      await handleSingleClick(selectedInvoice);
                      setSelectedInvoice(null);
                    }}
                    className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-lg shadow-emerald-600/30 flex items-center gap-1.5"
                  >
                    <Check className="w-4 h-4" />
                    <span>即時承認を確定</span>
                  </button>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
