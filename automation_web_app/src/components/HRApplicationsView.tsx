import React from 'react';
import { Users, CheckCircle2, Clock, Play, ShieldCheck } from 'lucide-react';
import { HRApplication } from '../types';

interface HRApplicationsViewProps {
  applications: HRApplication[];
  onApproveAll: () => void;
  onApproveSingle: (id: string) => void;
}

export const HRApplicationsView: React.FC<HRApplicationsViewProps> = ({
  applications,
  onApproveAll,
  onApproveSingle
}) => {
  const pendingCount = applications.filter(a => a.status === 'PENDING').length;

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-400" />
            <span>HR人事給与システム — 勤怠・休暇申請自動処理</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            フレックス変更、特別休暇（慶弔）、代休、年次有給休暇の就業規則適合性確認と承認確定
          </p>
        </div>

        <button
          onClick={onApproveAll}
          disabled={pendingCount === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer disabled:opacity-50"
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
              <th className="p-3">申請ID / 伝票コード</th>
              <th className="p-3">社員ID・氏名</th>
              <th className="p-3">所属部署</th>
              <th className="p-3">申請種別</th>
              <th className="p-3">対象日</th>
              <th className="p-3">確認コメント</th>
              <th className="p-3 text-center">状態</th>
              <th className="p-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200">
            {applications.map(app => (
              <tr key={app.id} className="hover:bg-slate-800/40">
                <td className="p-3 font-mono">
                  <div className="font-semibold text-white">{app.application_id}</div>
                  <div className="text-[11px] text-slate-400">{app.voucher_code}</div>
                </td>
                <td className="p-3">
                  <div className="font-medium text-white">{app.employee_name}</div>
                  <div className="text-[11px] text-slate-400 font-mono">{app.employee_id}</div>
                </td>
                <td className="p-3 text-slate-300">{app.department}</td>
                <td className="p-3 font-semibold text-emerald-400">{app.application_type}</td>
                <td className="p-3 font-mono text-slate-300">{app.target_date}</td>
                <td className="p-3 text-[11px] text-slate-400 truncate max-w-xs">
                  {app.confirmation_comment || '就業規則・休暇規程適合確認済'}
                </td>
                <td className="p-3 text-center">
                  {app.status === 'APPROVED' ? (
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
                  {app.status !== 'APPROVED' && (
                    <button
                      onClick={() => onApproveSingle(app.id)}
                      className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] transition-all"
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
