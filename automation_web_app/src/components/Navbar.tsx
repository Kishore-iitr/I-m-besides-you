import React from 'react';
import { 
  Building2, 
  Database, 
  Cpu, 
  FileSpreadsheet, 
  ShieldCheck, 
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { SupabaseConfig } from '../types';

interface NavbarProps {
  supabaseConfig: SupabaseConfig;
  onOpenSupabaseModal: () => void;
  onOpenDocsHub: () => void;
  onOpenPuterConsole: () => void;
  activeTab: string;
  setActiveTab: (tab: any) => void;
  isPuterOnline: boolean;
  onResetData: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  supabaseConfig,
  onOpenSupabaseModal,
  onOpenDocsHub,
  onOpenPuterConsole,
  activeTab,
  setActiveTab,
  isPuterOnline,
  onResetData
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Logo & App Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-sky-500 to-emerald-400 p-0.5 shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Building2 className="w-5 h-5 text-sky-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white tracking-tight">
                Enterprise Automation Hub
              </h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                SOP Level-3
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              財務会計・人事・契約 全自動処理 &amp; 3者照合推論プラットフォーム
            </p>
          </div>
        </div>

        {/* Global Action / Status Badges */}
        <div className="flex items-center gap-2 sm:gap-3">
          
          {/* Puter LLM Status Pill */}
          <button
            onClick={onOpenPuterConsole}
            title="Puter.js LLM 推論コンソールを開く"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/80 transition-all text-slate-300"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Puter LLM:</span>
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              {isPuterOnline ? 'Active' : 'Ready'}
            </span>
          </button>

          {/* Supabase Connection Status Pill */}
          <button
            onClick={onOpenSupabaseModal}
            title="Supabase PostgreSQL 接続設定を開く"
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              supabaseConfig.connected
                ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/40'
                : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800'
            }`}
          >
            <Database className={`w-3.5 h-3.5 ${supabaseConfig.connected ? 'text-emerald-400' : 'text-slate-400'}`} />
            <span className="hidden md:inline">Supabase DB:</span>
            <span className={supabaseConfig.connected ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
              {supabaseConfig.connected ? 'Connected' : 'Local Mode'}
            </span>
          </button>

          {/* Documents Workspace Shortcut */}
          <button
            onClick={onOpenDocsHub}
            title="Word / Excel ドキュメントハブを開く"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'DOCUMENTS'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
                : 'bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden sm:inline">Excel / Word</span>
          </button>

          {/* Reset Demo Data Button */}
          <button
            onClick={onResetData}
            title="Dataset B 初期データにリセット"
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

        </div>

      </div>
    </header>
  );
};
