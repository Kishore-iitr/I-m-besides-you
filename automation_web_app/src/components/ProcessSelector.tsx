import React from 'react';
import { 
  FileText, 
  Users, 
  Briefcase, 
  PlayCircle, 
  FileSpreadsheet, 
  Sparkles, 
  ScrollText 
} from 'lucide-react';

export type MainTab = 
  | 'INVOICE_PROCESSING'
  | 'HR_APPLICATIONS'
  | 'PROCUREMENT_CONTRACTS'
  | 'STEP_SIMULATOR'
  | 'DOCUMENTS'
  | 'PUTER_CONSOLE'
  | 'AUDIT_TRAIL';

interface ProcessSelectorProps {
  activeTab: MainTab;
  setActiveTab: (tab: MainTab) => void;
  pendingInvoicesCount: number;
  pendingHrCount: number;
  pendingProcCount: number;
}

export const ProcessSelector: React.FC<ProcessSelectorProps> = ({
  activeTab,
  setActiveTab,
  pendingInvoicesCount,
  pendingHrCount,
  pendingProcCount
}) => {
  const tabs = [
    {
      id: 'INVOICE_PROCESSING' as MainTab,
      label: '請求書承認 (3者照合)',
      sublabel: '経理・財務会計',
      badge: pendingInvoicesCount > 0 ? `${pendingInvoicesCount}件` : undefined,
      badgeColor: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      icon: FileText
    },
    {
      id: 'HR_APPLICATIONS' as MainTab,
      label: '勤怠・休暇申請',
      sublabel: 'HR人事労務',
      badge: pendingHrCount > 0 ? `${pendingHrCount}件` : undefined,
      badgeColor: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      icon: Users
    },
    {
      id: 'PROCUREMENT_CONTRACTS' as MainTab,
      label: '取引基本契約管理',
      sublabel: '受発注・調達',
      badge: pendingProcCount > 0 ? `${pendingProcCount}件` : undefined,
      badgeColor: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
      icon: Briefcase
    },
    {
      id: 'STEP_SIMULATOR' as MainTab,
      label: '操作再現シミュレータ',
      sublabel: 'Edge × Word 照合',
      icon: PlayCircle
    },
    {
      id: 'DOCUMENTS' as MainTab,
      label: 'Excel / Word ハブ',
      sublabel: 'ファイル連携 & 変換',
      icon: FileSpreadsheet
    },
    {
      id: 'PUTER_CONSOLE' as MainTab,
      label: 'Puter AI 推論スタジオ',
      sublabel: 'LLM 思考ログ & Copilot',
      icon: Sparkles
    },
    {
      id: 'AUDIT_TRAIL' as MainTab,
      label: '監査ログ証跡',
      sublabel: '電子帳簿保存法準拠',
      icon: ScrollText
    }
  ];

  return (
    <div className="w-full mb-6 border-b border-slate-800 pb-1">
      <div className="flex items-center gap-2 overflow-x-auto py-1 scrollbar-thin scrollbar-thumb-slate-800">
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25 border border-indigo-500'
                  : 'bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
              <div className="text-left">
                <div className="font-semibold leading-tight">{tab.label}</div>
                <div className={`text-[10px] ${isActive ? 'text-indigo-200' : 'text-slate-400'}`}>
                  {tab.sublabel}
                </div>
              </div>
              {tab.badge && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md border ${
                  isActive ? 'bg-white/20 text-white border-white/30' : tab.badgeColor
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
