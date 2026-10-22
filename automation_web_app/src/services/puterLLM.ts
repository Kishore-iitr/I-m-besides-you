import { Invoice, VendorContract } from '../types';

declare global {
  interface Window {
    puter?: {
      ai?: {
        chat: (prompt: string | any[], options?: { model?: string }) => Promise<any>;
      };
      ui?: any;
    };
  }
}

export interface PuterReasoningResult {
  passed: boolean;
  thought: string;
  recommendedComment: string;
  auditFlag: string;
  sourceModel: string;
  latencyMs: number;
}

export function isPuterAvailable(): boolean {
  return typeof window !== 'undefined' && !!window.puter && !!window.puter.ai;
}

/**
 * Intelligent 3-way reconciliation and reasoning via Puter LLM
 */
export async function reasonInvoiceWithPuter(
  invoice: Invoice,
  contract?: VendorContract
): Promise<PuterReasoningResult> {
  const startTime = Date.now();

  // 1. Core Mathematical & Contractual Verification
  const expectedTax = Math.floor(invoice.subtotal_amount * invoice.tax_rate);
  const isTaxExact = Math.abs(invoice.tax_amount - expectedTax) <= 1;
  const isVendorListed = !!contract;
  const isAmountMatching = contract 
    ? Math.abs(invoice.subtotal_amount - contract.base_amount) < 1 
    : false;

  const passed = isVendorListed && isAmountMatching && isTaxExact;

  // 2. Prepare Prompt for Puter LLM
  const prompt = `
あなたは財務会計システムの自動化監査AIです。以下の請求書データとWord契約マスター（月次定額取引先一覧）を照合・推論してください。

【受領請求書】
- 請求書番号: ${invoice.invoice_number}
- 伝票番号: ${invoice.voucher_code}
- 取引先名: ${invoice.vendor_name}
- 請求税抜額: ¥${invoice.subtotal_amount.toLocaleString()}
- 消費税額: ¥${invoice.tax_amount.toLocaleString()} (税率: ${invoice.tax_rate * 100}%)
- 税込合計額: ¥${invoice.total_amount.toLocaleString()}

【Word定額取引先マスタ】
${contract ? `
- 取引先コード: ${contract.vendor_code}
- 契約社名: ${contract.vendor_name}
- 月額定額契約額: ¥${contract.base_amount.toLocaleString()}
- 契約税額: ¥${contract.tax_amount.toLocaleString()}
- 税込月額: ¥${contract.total_amount.toLocaleString()}
- 委託業務範囲: ${contract.service_scope}
- 参照元文書: ${contract.document_source}
` : '※ 該当する取引先が定額取引先マスタ（Word）に存在しません（未登録取引先）。'}

【指示】
1. 3者照合（取引先、金額、消費税10%）の推論結果を簡潔に要約してください。
2. 承認に合格した場合、社内規定の監査確認コメント（41〜43文字: "月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済"）を提示してください。
3. 不一致がある場合、差異の金額および原因（単価乖離、未契約請求、端数処理など）を明示してください。
`;

  let thought = '';
  let modelUsed = 'Heuristic Rules Engine';

  // Attempt calling Puter LLM if accessible
  if (isPuterAvailable()) {
    try {
      const response = await window.puter!.ai!.chat(prompt, { model: 'claude-3-5-sonnet' });
      thought = typeof response === 'string' 
        ? response 
        : response?.message?.content || JSON.stringify(response);
      modelUsed = 'Puter LLM (Claude-3.5-Sonnet)';
    } catch (puterErr) {
      console.warn('Puter.js API call fallback:', puterErr);
      thought = generateHeuristicThought(invoice, contract, passed, isAmountMatching, isTaxExact, isVendorListed);
      modelUsed = 'Puter Fallback (Deterministic Auditor)';
    }
  } else {
    thought = generateHeuristicThought(invoice, contract, passed, isAmountMatching, isTaxExact, isVendorListed);
  }

  const recommendedComment = passed
    ? '月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済'
    : isVendorListed
      ? `定額マスタ乖離検知: 差額¥${Math.abs(invoice.subtotal_amount - (contract?.base_amount || 0)).toLocaleString()}につき要管理者確認`
      : '定額取引先一覧未登録取引先: 個別発注請書または見積書要照合';

  const auditFlag = passed 
    ? 'OK' 
    : !isVendorListed 
      ? 'UNLISTED_VENDOR' 
      : !isTaxExact 
        ? 'TAX_MISMATCH' 
        : 'RATE_MISMATCH';

  return {
    passed,
    thought,
    recommendedComment,
    auditFlag,
    sourceModel: modelUsed,
    latencyMs: Date.now() - startTime
  };
}

function generateHeuristicThought(
  invoice: Invoice,
  contract: VendorContract | undefined,
  passed: boolean,
  isAmountMatching: boolean,
  isTaxExact: boolean,
  isVendorListed: boolean
): string {
  if (passed && contract) {
    return `【照合成功・整合性確認済】\n` +
      `取引先「${contract.vendor_name}（コード: ${contract.vendor_code}）」は月次定額取引先一覧（${contract.document_source}）と完全一致。\n` +
      `請求税抜額 ¥${invoice.subtotal_amount.toLocaleString()} は契約定額 ¥${contract.base_amount.toLocaleString()} と合致。\n` +
      `消費税計算 (10% = ¥${invoice.tax_amount.toLocaleString()}) は税法上の端数規定に基づき整合しています。承認トランザクションへの移行を推奨します。`;
  }

  if (!isVendorListed) {
    return `【警告: 取引先マスタ未登録】\n` +
      `請求社名「${invoice.vendor_name}」は、定額取引先マスタ（Word）に登録がありません。\n` +
      `定額保守ではなく都度発注（受発注在庫管理システム）の個別PO番号との紐付け照合が必要です。自動承認を保留し、経理マネージャー確認へ回送します。`;
  }

  if (!isAmountMatching && contract) {
    const diff = invoice.subtotal_amount - contract.base_amount;
    return `【警告: 契約金額不整合】\n` +
      `請求社名: ${contract.vendor_name}（${contract.vendor_code}）\n` +
      `契約額 ¥${contract.base_amount.toLocaleString()} に対し、請求金額 ¥${invoice.subtotal_amount.toLocaleString()} であり、差額 ¥${Math.abs(diff).toLocaleString()}（${diff > 0 ? '過大請求' : '過少請求'}）が発生しています。\n` +
      `超過作業時間または契約改定が反映されていない可能性があります。`;
  }

  return `【警告: 消費税計算不一致】\n` +
    `請求税抜 ¥${invoice.subtotal_amount.toLocaleString()} に対する法定消費税(10%) ¥${Math.floor(invoice.subtotal_amount * 0.1).toLocaleString()} と、記載税額 ¥${invoice.tax_amount.toLocaleString()} が乖離しています。`;
}

/**
 * Ask Puter Copilot a general business or audit question
 */
export async function askPuterCopilot(
  query: string,
  contextData: any
): Promise<string> {
  if (!isPuterAvailable()) {
    return `【オフライン応答】Puter.js SDK が未ロードまたはブラウザ制限されています。Puter LLM はクラウド経由でリアルタイム動作します。現在コンテキスト内の ${Array.isArray(contextData) ? contextData.length : '複数'} 件の伝票はルールエンジンによって安全に保護されています。`;
  }

  try {
    const prompt = `
あなたは企業の経理・人事・調達プロセスの自動化を支えるインテリジェントCopilotです。
以下の業務コンテキストを考慮し、ユーザーの質問に日本語で簡潔かつ論理的に回答してください。

【コンテキストデータ】
${JSON.stringify(contextData).slice(0, 3000)}

【質問】
${query}
`;
    const res = await window.puter!.ai!.chat(prompt, { model: 'claude-3-5-sonnet' });
    return typeof res === 'string' ? res : res?.message?.content || JSON.stringify(res);
  } catch (err: any) {
    return `Puter LLM 呼び出しエラー: ${err.message || err}`;
  }
}
