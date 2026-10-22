import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  Upload, 
  Download, 
  Check, 
  AlertCircle, 
  Table, 
  Eye, 
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { readExcelFile, exportInvoicesToExcel, downloadSampleExcelTemplate, ParsedExcelResult } from '../services/excelService';
import { readWordDocument, exportAuditCertificateWord, ParsedWordResult } from '../services/wordService';
import { Invoice, VendorContract } from '../types';

interface DocumentsHubViewProps {
  invoices: Invoice[];
  vendors: VendorContract[];
  onImportInvoices: (imported: Partial<Invoice>[]) => void;
  onImportVendors: (imported: Partial<VendorContract>[]) => void;
}

export const DocumentsHubView: React.FC<DocumentsHubViewProps> = ({
  invoices,
  vendors,
  onImportInvoices,
  onImportVendors
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'EXCEL' | 'WORD'>('EXCEL');
  
  // Excel state
  const [excelResult, setExcelResult] = useState<ParsedExcelResult | null>(null);
  const [isExcelLoading, setIsExcelLoading] = useState<boolean>(false);

  // Word state
  const [wordResult, setWordResult] = useState<ParsedWordResult | null>(null);
  const [isWordLoading, setIsWordLoading] = useState<boolean>(false);

  // Handle Excel Upload
  const handleExcelDrop = async (e: React.DragEvent<HTMLDivElement> | React.ChangeEvent<HTMLInputElement>) => {
    let file: File | null = null;
    if ('dataTransfer' in e) {
      e.preventDefault();
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        file = e.dataTransfer.files[0];
      }
    } else if (e.target.files && e.target.files[0]) {
      file = e.target.files[0];
    }

    if (!file) return;

    setIsExcelLoading(true);
    try {
      const parsed = await readExcelFile(file);
      setExcelResult(parsed);
    } catch (err) {
      console.error('Failed to parse Excel:', err);
      alert('Excelファイルの読み込みに失敗しました。形式 (.xlsx, .xls, .csv) をご確認ください。');
    } finally {
      setIsExcelLoading(false);
    }
  };

  // Handle Word Upload
  const handleWordDrop = async (e: React.DragEvent<HTMLDivElement> | React.ChangeEvent<HTMLInputElement>) => {
    let file: File | null = null;
    if ('dataTransfer' in e) {
      e.preventDefault();
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        file = e.dataTransfer.files[0];
      }
    } else if (e.target.files && e.target.files[0]) {
      file = e.target.files[0];
    }

    if (!file) return;

    setIsWordLoading(true);
    try {
      const parsed = await readWordDocument(file);
      setWordResult(parsed);
    } catch (err) {
      console.error('Failed to parse Word:', err);
      alert('Wordドキュメントの読み込みに失敗しました。.docx 形式をご確認ください。');
    } finally {
      setIsWordLoading(false);
    }
  };

  const handleApplyExcelInvoices = () => {
    if (excelResult && excelResult.invoices.length > 0) {
      onImportInvoices(excelResult.invoices);
      alert(`${excelResult.invoices.length}件の請求書伝票をアクティブキューへ追加しました。`);
    }
  };

  const handleApplyWordVendors = () => {
    if (wordResult && wordResult.extractedVendors.length > 0) {
      onImportVendors(wordResult.extractedVendors);
      alert(`${wordResult.extractedVendors.length}件の契約取引先レコードをWordマスタへ反映しました。`);
    }
  };

  const handleExportWordCertificate = () => {
    const approvedInvoices = invoices.filter(i => i.status === 'APPROVED');
    const tableRowsHtml = approvedInvoices.map(i => `
      <tr>
        <td>${i.invoice_number}</td>
        <td>${i.voucher_code}</td>
        <td>${i.vendor_name}</td>
        <td style="text-align: right;">¥${i.subtotal_amount.toLocaleString()}</td>
        <td style="text-align: right;">¥${i.tax_amount.toLocaleString()}</td>
        <td style="text-align: right; font-weight: bold;">¥${i.total_amount.toLocaleString()}</td>
        <td><span class="badge-approved">承認済</span></td>
      </tr>
    `).join('');

    const contentHtml = `
      <h2>1. 照合承認済 請求書伝票台帳</h2>
      <table>
        <thead>
          <tr>
            <th>請求書番号</th>
            <th>伝票番号</th>
            <th>取引先名</th>
            <th>税抜金額</th>
            <th>消費税(10%)</th>
            <th>税込合計</th>
            <th>状態</th>
          </tr>
        </thead>
        <tbody>
          ${tableRowsHtml || '<tr><td colspan="7">承認済伝票はありません。</td></tr>'}
        </tbody>
      </table>

      <h2>2. 照合基準および監査証跡</h2>
      <p>対象文書: <strong>月次定額取引先一覧 (getsujitsu_teigaku_torihikisaki_ichiran)</strong></p>
      <p>全伝票において、月次定額契約単価との完全一致および法定消費税率10%の計算整合性を検算済。承認時確認コメント「月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済」を全自動注入の上、承認確定トランザクションをコミットしました。</p>
    `;

    exportAuditCertificateWord('請求書自動承認 監査証明書 (Audit Certification)', contentHtml);
  };

  return (
    <div className="space-y-6">

      {/* Header and Sub-Tab Switcher */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>Excel / Word スムーズ連携ワークスペース</span>
            <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
              Drag &amp; Drop Ingestion
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            実務で散在するWord契約書・Excel台帳をブラウザ上でシームレスに直接解析・抽出・相互エクスポート
          </p>
        </div>

        <div className="flex items-center gap-2 border border-slate-800 rounded-lg p-1 bg-slate-950">
          <button
            onClick={() => setActiveSubTab('EXCEL')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeSubTab === 'EXCEL'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-300" />
            <span>Excel スプレッドシート連携</span>
          </button>

          <button
            onClick={() => setActiveSubTab('WORD')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeSubTab === 'WORD'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-4 h-4 text-indigo-300" />
            <span>Word 契約文書連携</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: EXCEL WORKBENCH */}
      {activeSubTab === 'EXCEL' && (
        <div className="space-y-4">
          
          {/* Excel Dropzone & Quick Template Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            
            {/* Dropzone Card */}
            <div 
              onDragOver={e => e.preventDefault()}
              onDrop={handleExcelDrop}
              className="lg:col-span-2 p-6 rounded-xl border-2 border-dashed border-slate-700 hover:border-emerald-500 bg-slate-900/60 hover:bg-slate-900 transition-all text-center flex flex-col items-center justify-center gap-3 relative cursor-pointer"
            >
              <input 
                type="file" 
                accept=".xlsx,.xls,.csv" 
                onChange={handleExcelDrop}
                className="absolute inset-0 opacity-0 cursor-pointer" 
              />
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Excel スプレッドシートをドラッグ＆ドロップ</h3>
                <p className="text-xs text-slate-400 mt-1">
                  またはクリックしてファイルを選択 (.xlsx, .xls, .csv 対応)
                </p>
              </div>
              <div className="text-[11px] text-slate-500">
                請求書台帳、取引先レート表、振込一覧データを瞬時にパースします
              </div>
            </div>

            {/* Quick Templates & Export Card */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-3">
              <div>
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Excel エクスポート &amp; テンプレート
                </h4>
                <p className="text-xs text-slate-400">
                  監査用ブック出力またはインポート用標準雛形をダウンロードできます。
                </p>
              </div>

              <div className="space-y-2">
                <button
                  onClick={() => exportInvoicesToExcel(invoices)}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>承認台帳・監査KPI Excel出力</span>
                </button>

                <button
                  onClick={downloadSampleExcelTemplate}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>請求書インポート雛形 (.xlsx)</span>
                </button>
              </div>
            </div>

          </div>

          {/* Parsed Excel Preview Table */}
          {excelResult && (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white">
                    解析完了: {excelResult.fileName} ({excelResult.rawRows.length} 行)
                  </span>
                </div>

                <button
                  onClick={handleApplyExcelInvoices}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md"
                >
                  <span>請求書キューへ反映 ({excelResult.invoices.length}件)</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs text-slate-200">
                  <thead className="bg-slate-950 text-slate-400 text-[11px] sticky top-0">
                    <tr>
                      <th className="p-2 border-b border-slate-800">請求書番号</th>
                      <th className="p-2 border-b border-slate-800">伝票番号</th>
                      <th className="p-2 border-b border-slate-800">取引先名</th>
                      <th className="p-2 border-b border-slate-800 text-right">税抜金額</th>
                      <th className="p-2 border-b border-slate-800 text-right">消費税</th>
                      <th className="p-2 border-b border-slate-800 text-right">税込合計</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {excelResult.invoices.slice(0, 10).map((inv, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40">
                        <td className="p-2 text-white font-semibold">{inv.invoice_number}</td>
                        <td className="p-2 text-slate-400">{inv.voucher_code}</td>
                        <td className="p-2 font-sans">{inv.vendor_name}</td>
                        <td className="p-2 text-right">¥{inv.subtotal_amount?.toLocaleString()}</td>
                        <td className="p-2 text-right text-slate-400">¥{inv.tax_amount?.toLocaleString()}</td>
                        <td className="p-2 text-right text-emerald-400 font-bold">¥{inv.total_amount?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      )}

      {/* SECTION 2: WORD WORKBENCH */}
      {activeSubTab === 'WORD' && (
        <div className="space-y-4">
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            
            {/* Word Dropzone */}
            <div 
              onDragOver={e => e.preventDefault()}
              onDrop={handleWordDrop}
              className="lg:col-span-2 p-6 rounded-xl border-2 border-dashed border-slate-700 hover:border-indigo-500 bg-slate-900/60 hover:bg-slate-900 transition-all text-center flex flex-col items-center justify-center gap-3 relative cursor-pointer"
            >
              <input 
                type="file" 
                accept=".docx" 
                onChange={handleWordDrop}
                className="absolute inset-0 opacity-0 cursor-pointer" 
              />
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Word 契約文書 (.docx) をドラッグ＆ドロップ</h3>
                <p className="text-xs text-slate-400 mt-1">
                  例: getsujitsu_teigaku_torihikisaki_ichiran.docx (月次定額取引先一覧)
                </p>
              </div>
              <div className="text-[11px] text-slate-500">
                Mammoth エンジンにより文書内の契約条項・定額表を自動解析します
              </div>
            </div>

            {/* Word Export Card */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-3">
              <div>
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Word 監査証明書 生成
                </h4>
                <p className="text-xs text-slate-400">
                  承認された伝票群をまとめた公的監査用Word証明書（.doc）を発行します。
                </p>
              </div>

              <button
                onClick={handleExportWordCertificate}
                className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-xs font-semibold transition-all"
              >
                <Download className="w-3.5 h-3.5" />
                <span>監査証明書 Word (.doc) ダウンロード</span>
              </button>
            </div>

          </div>

          {/* Parsed Word Document Preview */}
          {wordResult ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white">
                    Word解析完了: {wordResult.fileName}
                  </span>
                </div>

                {wordResult.extractedVendors.length > 0 && (
                  <button
                    onClick={handleApplyWordVendors}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md"
                  >
                    <span>取引先マスタへ反映 ({wordResult.extractedVendors.length}件)</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Rendered HTML inside Word doc */}
              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 max-h-72 overflow-y-auto text-xs text-slate-300 prose prose-invert prose-sm max-w-none">
                <div dangerouslySetInnerHTML={{ __html: wordResult.html }} />
              </div>
            </div>
          ) : (
            /* Current In-Memory Word Master Table */
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  現在メモリにロードされているWord定額取引先マスタ ({vendors.length}社)
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  getsujitsu_teigaku_torihikisaki_ichiran
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-200">
                  <thead className="bg-slate-950 text-slate-400 text-[11px]">
                    <tr>
                      <th className="p-2 border-b border-slate-800">コード</th>
                      <th className="p-2 border-b border-slate-800">取引先名称</th>
                      <th className="p-2 border-b border-slate-800 text-right">月額契約金 (税抜)</th>
                      <th className="p-2 border-b border-slate-800 text-right">消費税 (10%)</th>
                      <th className="p-2 border-b border-slate-800 text-right">月額合計 (税込)</th>
                      <th className="p-2 border-b border-slate-800">委託業務範囲</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {vendors.map(v => (
                      <tr key={v.id} className="hover:bg-slate-800/30">
                        <td className="p-2 font-mono text-indigo-300 font-bold">{v.vendor_code}</td>
                        <td className="p-2 font-medium text-white">{v.vendor_name}</td>
                        <td className="p-2 text-right font-mono">¥{v.base_amount.toLocaleString()}</td>
                        <td className="p-2 text-right font-mono text-slate-400">¥{v.tax_amount.toLocaleString()}</td>
                        <td className="p-2 text-right font-mono text-emerald-400 font-bold">¥{v.total_amount.toLocaleString()}</td>
                        <td className="p-2 text-slate-400 text-[11px] truncate max-w-xs">{v.service_scope}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
};
