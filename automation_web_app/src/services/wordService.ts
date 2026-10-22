import mammoth from 'mammoth';
import { VendorContract } from '../types';

export interface ParsedWordResult {
  html: string;
  rawText: string;
  fileName: string;
  extractedVendors: Partial<VendorContract>[];
}

/**
 * Smoothly read and parse Word documents (.docx) via Mammoth
 */
export async function readWordDocument(file: File): Promise<ParsedWordResult> {
  const arrayBuffer = await file.arrayBuffer();

  const [htmlResult, textResult] = await Promise.all([
    mammoth.convertToHtml({ arrayBuffer }),
    mammoth.extractRawText({ arrayBuffer })
  ]);

  const html = htmlResult.value;
  const rawText = textResult.value;

  // Extract structured vendor contract data from Word tables or text lines
  const extractedVendors = parseVendorContractsFromText(rawText);

  return {
    html,
    rawText,
    fileName: file.name,
    extractedVendors
  };
}

/**
 * Parse text or table lines in Word to identify vendor contracts (V3001, company name, amounts)
 */
export function parseVendorContractsFromText(text: string): Partial<VendorContract>[] {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const vendors: Partial<VendorContract>[] = [];

  // Match pattern: V300X or vendor name followed by currency
  const vendorRegex = /(V\d{4})?\s*([^\d\n\r]+(?:株式会社|合同会社|設計|サービス|センター))\s*([0-9,]+)/i;

  for (const line of lines) {
    const match = line.match(vendorRegex);
    if (match) {
      const code = match[1] || `V${3000 + vendors.length + 1}`;
      const name = match[2].trim();
      const amountStr = match[3].replace(/,/g, '');
      const baseAmount = parseInt(amountStr, 10);

      if (!isNaN(baseAmount) && baseAmount > 1000) {
        const taxAmount = Math.floor(baseAmount * 0.1);
        vendors.push({
          id: `doc-vc-${vendors.length + 1}`,
          vendor_code: code,
          vendor_name: name,
          base_amount: baseAmount,
          tax_rate: 0.10,
          tax_amount: taxAmount,
          total_amount: baseAmount + taxAmount,
          service_scope: 'Word契約書抽出条項に基づく定額委託業務',
          document_source: 'アップロードWord文書',
          status: 'ACTIVE'
        });
      }
    }
  }

  return vendors;
}

/**
 * Generate a downloadable Word-compatible HTML Document (.doc) with complete styling
 */
export function exportAuditCertificateWord(
  title: string,
  contentHtml: string,
  fileName: string = 'Invoice_Approval_Audit_Certificate.doc'
): void {
  const docHtml = `
<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
  <meta charset='utf-8'>
  <title>${title}</title>
  <style>
    body { font-family: 'MS Gothic', 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e293b; line-height: 1.6; }
    h1 { font-size: 18pt; color: #0f172a; border-bottom: 2pt solid #0284c7; padding-bottom: 6pt; }
    h2 { font-size: 14pt; color: #0369a1; margin-top: 14pt; }
    table { width: 100%; border-collapse: collapse; margin-top: 10pt; margin-bottom: 15pt; }
    th { background-color: #f1f5f9; color: #334155; font-weight: bold; border: 1pt solid #cbd5e1; padding: 6pt; text-align: left; }
    td { border: 1pt solid #cbd5e1; padding: 6pt; }
    .badge-approved { background-color: #dcfce7; color: #15803d; font-weight: bold; padding: 2pt 6pt; border-radius: 4pt; }
    .footer { margin-top: 30pt; font-size: 9pt; color: #64748b; border-top: 1pt solid #e2e8f0; padding-top: 8pt; }
  </style>
</head>
<body>
  <h1>${title}</h1>
  <p><strong>発行システム:</strong> 財務会計全自動処理エージェント (Enterprise Automation Hub)</p>
  <p><strong>発行日時:</strong> ${new Date().toLocaleString('ja-JP')} (JST)</p>
  <p><strong>準拠基準:</strong> 月次定額取引先一覧 3者照合内部統制基準 (Wordマスタ照合済)</p>
  <hr style="border: none; border-top: 1pt solid #e2e8f0; margin: 15pt 0;" />
  ${contentHtml}
  <div class="footer">
    本ドキュメントは内部統制監査・電子帳簿保存法要件に基づき自動生成された電子的処理証明書です。
  </div>
</body>
</html>
`;

  const blob = new Blob(['\ufeff' + docHtml], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
