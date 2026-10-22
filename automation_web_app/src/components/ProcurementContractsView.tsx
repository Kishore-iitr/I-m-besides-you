import React from 'react';
import { Briefcase, CheckCircle2, Clock, Play } from 'lucide-react';
import { ProcurementContract } from '../types';

interface ProcurementContractsViewProps {
  contracts: ProcurementContract[];
  onApproveAll: () => void;
  onApproveSingle: (id: string) => void;
}

export const ProcurementContractsView: React.FC<ProcurementContractsViewProps> = ({
  contracts,
  onApproveAll,
  onApproveSingle
}) => {
  const pendingCount = contracts.filter(c => c.status === 'PENDING').length;

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-sky-400" />
            <span>受発注在庫管理システム — 取引基本契約・売買契約管理</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            取引基本契約（新規締結）、売買契約（変更）、契約解除手続の法務条項・電子捺印整合性確認
          </p>
        </div>

        <button
          onClick={onApproveAll}
          disabled={pendingCount === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer disabled:opacity-50"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>全件一括自動承認 ({pendingCount}件)</span>
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-medium">
              <th className="p-3">契約管理番号 / 伝票</th>
              <th className="p-3">契約種別</th>
              <th className="p-3">契約相手先企業</th>
              <th className="p-3">代表者名</th>
              <th className="p-3">発効日</th>
              <th className="p-3">確認コメント</th>
              <th className="p-3 text-center">状態</th>
              <th className="p-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200">
            {contracts.map(contract => (
              <tr key={contract.id} className="hover:bg-slate-800/40">
                <td className="p-3 font-mono">
                  <div className="font-semibold text-white">{contract.contract_id}</div>
                  <div className="text-[11px] text-slate-400">{contract.voucher_code}</div>
                </td>
                <td className="p-3 font-semibold text-sky-400">{contract.contract_type}</td>
                <td className="p-3 font-medium text-white">{contract.vendor_name}</td>
                <td className="p-3 text-slate-300">{contract.representative_name}</td>
                <td className="p-3 font-mono text-slate-300">{contract.effective_date}</td>
                <td className="p-3 text-[11px] text-slate-400 truncate max-w-xs">
                  {contract.confirmation_comment || '法務標準取引基本規程・電子捺印条項整合確認済'}
                </td>
                <td className="p-3 text-center">
                  {contract.status === 'APPROVED' ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px] bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/60">
                      <CheckCircle2 className="w-3 h-3" />
                      承認済
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-400 font-semibold text-[11px] bg-amber-950/60 px-2 py-0.5 rounded-full border border-amber-800/60">
                      <Clock className="w-3 h-3" />
                      未処理
                    </span>
                  )}
                </td>
                <td className="p-3 text-right">
                  {contract.status !== 'APPROVED' && (
                    <button
                      onClick={() => onApproveSingle(contract.id)}
                      className="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-semibold text-[11px] transition-all"
                    >
                      承認
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
