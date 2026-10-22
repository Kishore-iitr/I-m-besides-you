import React, { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  Cpu, 
  Terminal, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw,
  HelpCircle,
  FileCode
} from 'lucide-react';
import { Invoice, VendorContract } from '../types';
import { isPuterAvailable, reasonInvoiceWithPuter, askPuterCopilot } from '../services/puterLLM';

interface PuterConsoleViewProps {
  invoices: Invoice[];
  vendors: VendorContract[];
}

export const PuterConsoleView: React.FC<PuterConsoleViewProps> = ({
  invoices,
  vendors
}) => {
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string>(invoices[0]?.id || '');
  const [isReasoning, setIsReasoning] = useState<boolean>(false);
  const [reasoningOutput, setReasoningOutput] = useState<any>(null);

  // Copilot chat state
  const [chatInput, setChatInput] = useState<string>('');
  const [chatMessages, setChatMessages] = useState<Array<{ sender: 'user' | 'puter'; text: string; time: string }>>([
    {
      sender: 'puter',
      text: 'こんにちは。Puter.js 推論エージェントです。経理・財務会計の3者照合（請求書 × 契約書 × 法定税率）の推論や、要確認案件の抽出・分析をリアルタイムで行えます。質問があれば入力してください。',
      time: new Date().toLocaleTimeString()
    }
  ]);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);

  const targetInvoice = invoices.find(i => i.id === selectedInvoiceId) || invoices[0];
  const targetVendor = vendors.find(v => 
    v.vendor_name === targetInvoice?.vendor_name || 
    v.vendor_code === targetInvoice?.vendor_code
  );

  const handleRunPuterReasoning = async () => {
    if (!targetInvoice) return;
    setIsReasoning(true);
    try {
      const res = await reasonInvoiceWithPuter(targetInvoice, targetVendor);
      setReasoningOutput(res);
    } catch (e: any) {
      alert(`Puter 推論エラー: ${e.message}`);
    } finally {
      setIsReasoning(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const query = chatInput.trim();
    setChatInput('');
    const userMsg = { sender: 'user' as const, text: query, time: new Date().toLocaleTimeString() };
    setChatMessages(prev => [...prev, userMsg]);

    setIsChatLoading(true);
    try {
      const summaryContext = {
        totalInvoices: invoices.length,
        discrepancies: invoices.filter(i => i.status === 'DISCREPANCY').map(i => ({
          inv: i.invoice_number,
          vendor: i.vendor_name,
          subtotal: i.subtotal_amount,
          tax: i.tax_amount,
          reason: i.puter_reasoning
        })),
        vendorsCount: vendors.length
      };

      const reply = await askPuterCopilot(query, summaryContext);
      setChatMessages(prev => [...prev, {
        sender: 'puter',
        text: reply,
        time: new Date().toLocaleTimeString()
      }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, {
        sender: 'puter',
        text: `推論エラーが発生しました: ${err.message}`,
        time: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="space-y-6">

      {/* Top Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-slate-900 border border-indigo-800/50 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <span>Puter LLM クラウド推論エンジン &amp; 監査Copilot</span>
          </h2>
          <p className="text-xs text-indigo-200/80 mt-0.5">
            Puter.js SDK (<code className="text-amber-300">window.puter.ai.chat</code>) により、ブラウザ上で直接 Claude-3.5-Sonnet / GPT-4o による契約条項推論・差異分析を実行
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Puter SDK: {isPuterAvailable() ? 'Active (js.puter.com)' : 'Local Fallback'}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Panel 1: Invoice Reasoning Studio */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Terminal className="w-4 h-4 text-sky-400" />
              <span>伝票単位 リアルタイム照合推論テスト</span>
            </h3>
            <span className="text-[11px] text-slate-400">3-Way Match Verification</span>
          </div>

          {/* Invoice Picker */}
          <div className="space-y-1">
            <label className="text-xs text-slate-400">検証対象の請求書伝票を選択:</label>
            <select
              value={selectedInvoiceId}
              onChange={e => {
                setSelectedInvoiceId(e.target.value);
                setReasoningOutput(null);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              {invoices.map(inv => (
                <option key={inv.id} value={inv.id}>
                  {inv.invoice_number} | {inv.vendor_name} (¥{inv.total_amount.toLocaleString()}) - [{inv.status}]
                </option>
              ))}
            </select>
          </div>

          {/* Context Peek */}
          {targetInvoice && (
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80 space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>伝票コード: {targetInvoice.voucher_code}</span>
                <span className="text-white font-bold">税込 ¥{targetInvoice.total_amount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>取引先: {targetInvoice.vendor_name}</span>
                <span className={targetVendor ? 'text-emerald-400' : 'text-rose-400'}>
                  {targetVendor ? `Wordマスタ登録 (定額 ¥${targetVendor.base_amount.toLocaleString()})` : 'Wordマスタ未登録'}
                </span>
              </div>
            </div>
          )}

          {/* Trigger Reasoning Button */}
          <button
            onClick={handleRunPuterReasoning}
            disabled={isReasoning}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white text-xs font-bold shadow-md shadow-indigo-600/25 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            {isReasoning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>Puter LLM 推論中...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-amber-300" />
                <span>Puter LLM 推論を実行 (Claude-3.5-Sonnet)</span>
              </>
            )}
          </button>

          {/* Output Box */}
          {reasoningOutput && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 animate-fade-in text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-bold flex items-center gap-1.5 text-white">
                  {reasoningOutput.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                  )}
                  <span>照合判定: {reasoningOutput.passed ? '合格 (承認可)' : '不合格 (保留)'}</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {reasoningOutput.sourceModel} ({reasoningOutput.latencyMs}ms)
                </span>
              </div>

              <div className="p-3 bg-slate-900 rounded-lg text-slate-300 font-mono whitespace-pre-line leading-relaxed text-[11px]">
                {reasoningOutput.thought}
              </div>

              <div className="space-y-1">
                <span className="text-[10px] text-slate-400 block font-semibold">生成された監査コメント:</span>
                <div className="p-2 rounded bg-slate-900 text-emerald-300 font-mono text-[11px] border border-slate-800">
                  {reasoningOutput.recommendedComment}
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Panel 2: Interactive Puter Copilot Chat */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col h-[520px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>監査・経理 Copilot 対話チャット</span>
            </h3>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              LLM Online
            </span>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            {chatMessages.map((msg, index) => (
              <div
                key={index}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className="text-[10px] text-slate-500 mb-0.5 px-1">
                  {msg.sender === 'user' ? 'オペレーター' : 'Puter Copilot'} • {msg.time}
                </div>
                <div className={`p-3 rounded-xl max-w-[85%] leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none whitespace-pre-line'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {isChatLoading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs py-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                <span>Puter LLM が回答を生成中...</span>
              </div>
            )}
          </div>

          {/* Quick Prompts */}
          <div className="pt-2 pb-2 flex gap-1.5 overflow-x-auto text-[11px]">
            <button
              onClick={() => setChatInput('金額に差異のある請求書の一覧と原因を教えてください。')}
              className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 whitespace-nowrap"
            >
              金額差異のある伝票は？
            </button>
            <button
              onClick={() => setChatInput('Wordマスタと照合する際の消費税端数処理ルールを解説してください。')}
              className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 whitespace-nowrap"
            >
              消費税端数ルールは？
            </button>
          </div>

          {/* Input Form */}
          <form onSubmit={handleSendMessage} className="pt-2 border-t border-slate-800 flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              placeholder="質問や監査サマリーの指示を入力..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={isChatLoading || !chatInput.trim()}
              className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50 transition-all flex items-center justify-center cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>

        </div>

      </div>

    </div>
  );
};
