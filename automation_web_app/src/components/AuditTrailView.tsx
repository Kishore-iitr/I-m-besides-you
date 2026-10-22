import React from 'react';
import { ScrollText, Download, ShieldCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { AuditLogEntry } from '../types';
import * as XLSX from 'xlsx';

interface AuditTrailViewProps {
  logs: AuditLogEntry[];
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({ logs }) => {
  const handleExportAuditExcel = () => {
    const data = logs.map(l => ({
      'タイムスタンプ': l.timestamp,
      '対象伝票/契約ID': l.entity_id,
      '種別': l.entity_type,
      '自動化アクション': l.action_type,
      '注入コメント': l.comment_injected,
      '照合ソース': l.verification_source,
      'ステータス': l.status,
      'Puter推論ログ': l.puter_ai_thought || ''
    }));

    const ws = XLSX.utils.json_to_sheet(data.length > 0 ? data : [{ '備考': '監査ログなし' }]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, '監査証跡ログ');
    XLSX.writeFile(wb, `System_Audit_Trail_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  return (
    <div className="space-y-4">
      
      {/* Header */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ScrollText className="w-5 h-5 text-indigo-400" />
            <span>自動化監査証跡ログ (Audit Trail)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            電子帳簿保存法・内部統制基準に基づく全自動処理ログ、注入コメントおよびPuter推論思考の改ざん防止記録
          </p>
        </div>

        <button
          onClick={handleExportAuditExcel}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-medium transition-all"
        >
          <Download className="w-3.5 h-3.5 text-emerald-400" />
          <span>監査ログ Excel出力</span>
        </button>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-medium text-[11px]">
                <th className="p-3">日時 (JST)</th>
                <th className="p-3">対象伝票</th>
                <th className="p-3">実行アクション</th>
                <th className="p-3">照合検証元</th>
                <th className="p-3">注入コメント (41-43文字)</th>
                <th className="p-3 text-center">結果</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500 font-sans">
                    まだ自動化実行ログはありません。「一括自動承認」を実行するとここに記録されます。
                  </td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-800/40">
                    <td className="p-3 text-slate-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString('ja-JP')}
                    </td>
                    <td className="p-3 font-bold text-white whitespace-nowrap">
                      {log.entity_id}
                    </td>
                    <td className="p-3 text-indigo-300 font-semibold whitespace-nowrap">
                      {log.action_type}
                    </td>
                    <td className="p-3 text-slate-400 font-sans text-[11px]">
                      {log.verification_source}
                    </td>
                    <td className="p-3 text-emerald-300 font-sans text-[11px] max-w-xs truncate" title={log.comment_injected}>
                      {log.comment_injected}
                    </td>
                    <td className="p-3 text-center whitespace-nowrap">
                      {log.status === 'SUCCESS' ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold font-sans text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          合格
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold font-sans text-[11px]">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          保留
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
