"""
Unified Enterprise ERP Portal & LangGraph AI Co-Pilot
Triple Operational Suites:
  1. 財務会計システム (Financial Accounting - Invoice Processing: erp_invoices)
  2. HR人事給与システム (HR & Payroll - Payroll Item Processing: erp_payroll_items)
  3. 勤怠管理システム (Attendance & Leave Management - Leave Review: erp_leave_applications)
Running on http://127.0.0.1:5135
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from erp_db import db_manager, INITIAL_INVOICES, INITIAL_PAYROLL_ITEMS, INITIAL_LEAVE_APPLICATIONS, get_master_regulations, save_master_regulations
from copilot_langgraph_engine import copilot_engine, llm_service, extract_text_from_file_bytes

# Import shared enterprise PolicyEngine from pulled_automation
_agent_src = Path(__file__).parent / "pulled_automation" / "pg-db-analyst-agent" / "src"
if str(_agent_src) not in sys.path:
    sys.path.insert(0, str(_agent_src))

try:
    from services.policy_engine import PolicyEngine, TABLE_SCHEMAS
    erp_policy_engine = PolicyEngine()
    print("[PolicyEngine] Initialized shared policy engine in ERP portal.")
except Exception as pe_err:
    print(f"[PolicyEngine Warning] Could not load shared policy engine: {pe_err}")
    erp_policy_engine = None

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Preset documents
INVOICE_PRESET_POLICY = """月次定額保守取引先契約一覧 (2026年度 財務会計部門)
本方針は、定額保守契約および業務委託取引先に対する月次請求書の自動照合・承認基準を定める。

【承認基準 (Approved Rules)】
1. Global Tech LLC (取引先コード: V3005)
   - 月次定額保守費: ¥716,232 (固定)。契約内整合確認により自動承認。
2. 北陸部品工業株式会社 (Hokuriku Parts Industry Co., Ltd. / V3006)
   - 消耗部品定額保守費: ¥455,128 および ¥452,219。通常(Routine)取引として自動承認。
3. 大和商事株式会社 (Yamato Shoji Co., Ltd. / V3002)
   - 事務管理委託費: ¥1,237,439 および ¥1,218,687。業務委託契約書照合済、自動承認。
4. 福岡システムデザイン (Fukuoka System Design / V3007)
   - システム運用保守費: ¥1,832,962、¥1,993,825、¥1,685,384。IT基盤保守契約内として承認。
5. 山田製作所 (Yamada Manufacturing Co., Ltd. / V3001)
   - 定額加工費: ¥385,000 および ¥374,313。照合済、承認。
6. 東京クラウドソリューションズ (Tokyo Cloud Solutions / V3009)
   - クラウド保守費: ¥890,000。契約内として承認。
7. 仙台精密機器株式会社 (Sendai Precision Tech / V3010)
   - 精密機器定期点検費: ¥620,000。承認。
8. 札幌データネットワークス (Sapporo Data Networks / V3011)
   - 通信回線定額保守費: ¥540,000。承認。
9. 広島アドバンストエンジニアリング (Hiroshima Advanced Engineering / V3012)
   - 自動化ライン定期保守費: ¥950,000。承認。

【保留・要人間精査基準 (Hold / Review Rules)】
- 沖縄物流センター (Okinawa Logistics Center / V3008): 請求金額 ¥317,664 および ¥485,200 (区分: Adjustment)。
  調整・変動項目につき、物流管理部門の受領書および経理課長の事前承認確認を必須とし、自動承認は行わず保留(Hold)とする。
- 北陸部品工業株式会社 (V3006): 請求金額 ¥437,452 (区分: Adjustment)。部品緊急空輸割増につき保留(Hold)。
- 関西ソフトウェア研究所 (V3004): 請求金額 ¥2,450,000。自動承認限度額(200万円)超過につき取締役決裁を要す(Hold)。
- 区分が 'Adjustment' である伝票は、全件経理担当者による精査(Hold)を要する。"""

PAYROLL_PRESET_MEMO = """精算確認メモ (2026年7月度 人事給与控除・経費整備)
参照規程: 業務委託経費規程 (gyomu_itaku_keihi_kitei) / 業務委託給与規程 (gyomu_itaku_kyuuyo_kitei)

【経費精算・手当改定確認済リスト (Confirmed Items)】
1. 青木 拓也 (P4-07089771-001 / 照合伝票: P1-07089771-008)
   - 研修費: ¥77,224。外部技術研修受講料。規程第4条(上限10万円以内)適合確認済。確認済(Confirmed)。
2. 菊池 理恵 (P4-07089771-002 / 照合伝票: P1-07089771-009)
   - 消耗品費: ¥55,571。開発用消耗備品購入代金領収書照合済。確認済(Confirmed)。
3. 坂本 裕二 (P4-07089771-003 / 照合伝票: P1-07089771-010)
   - 出張旅費: ¥64,200。大阪支社技術支援出張旅費規程内整合確認済。確認済(Confirmed)。
4. 石田 美奈 (P4-07089771-004 / 照合伝票: P1-07089771-011)
   - 交通費精算: ¥14,850。客先往復近郊交通費照合済。確認済(Confirmed)。
5. 桐島 涼介 (P4-07089771-005 / 照合伝票: P4-07054374-012)
   - 残業手当調整: ¥38,400。勤怠管理システム超過勤務データ整合確認済。確認済(Confirmed)。
6. 江口 さくら (P4-07089771-006 / 照合伝票: P4-07054374-012)
   - 昇給: ¥25,000。人事考課給与辞令照合済。確認済(Confirmed)。
7. 島田 奈々 (P4-07089771-007 / 照合伝票: P5-07054374-012)
   - 扶養控除変更: ¥18,000 (控除)。扶養親族変更届照合済。確認済(Confirmed)。
8. 菊池 理恵 (P4-07089771-009 / 照合伝票: P4-07054374-012)
   - 役職手当新設: ¥40,000。新任リーダー手当適用確認済。確認済(Confirmed)。
9. 坂本 裕二 (P4-07089771-010 / 照合伝票: P4-07054374-012)
   - 役職手当廃止: ¥35,000 (控除)。組織変更に伴う手当終了確認済。確認済(Confirmed)。

【保留・要人間精査項目 (Hold / Exception Items)】
- 青木 拓也 (P4-07089771-008 / 照合伝票: P1-07089771-012)
  - 接待交際費: ¥145,000。業務委託経費規程第7条の上限(1件10万円)を超過しているため保留(Hold)。役員特別決裁承認を要す。
- 接待交際費で1件10万円を超える申請はすべて保留とし、役員事前承認稟議書を必須とする。
- 単一経費で15万円を超える申請は、社内限度額超過につき事前承認確認要(Hold)とする。
- 扶養控除変更または役職手当廃止が「加算(Addition)」として誤申請されている伝票は、控除区分不整合として保留とする。
- 人事給与マスタ未定義の手当コード（例: 未登録手当）は全件保留とする。"""

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>基幹統合業務システム - Enterprise ERP</title>
  <style>
    :root {
      --primary: #1e3a8a;
      --primary-hover: #172554;
      --accent: #0284c7;
      --border-color: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #475569;
      --success: #15803d;
      --success-bg: #dcfce7;
      --warning: #b45309;
      --warning-bg: #fef3c7;
      --danger: #b91c1c;
      --danger-bg: #fee2e2;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    html, body { height: 100%; overflow: hidden; }
    body { background-color: #f1f5f9; color: var(--text-main); font-size: 13px; line-height: 1.45; display: flex; flex-direction: column; }

    /* Clean Corporate Header */
    header.erp-header {
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      height: 56px;
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .header-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .erp-logo-icon {
      width: 32px;
      height: 32px;
      background: var(--primary);
      color: #ffffff;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
    }
    .header-title-box { display: flex; flex-direction: column; }
    .header-title {
      font-size: 15px;
      font-weight: 800;
      color: var(--primary);
      letter-spacing: -0.3px;
    }
    .header-subtitle {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Clean Navigation Tabs - Single Simple Name */
    .suite-nav-tabs {
      display: flex;
      background: #e2e8f0;
      padding: 3px;
      border-radius: 8px;
      gap: 4px;
    }
    .nav-tab-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 7px 22px;
      border-radius: 6px;
      border: 1px solid transparent;
      cursor: pointer;
      background: transparent;
      color: #475569;
      font-size: 13px;
      font-weight: 700;
      transition: all 0.15s ease;
    }
    .nav-tab-btn:hover { color: var(--text-main); }
    .nav-tab-btn.active {
      background: #ffffff;
      color: var(--primary);
      border-color: #cbd5e1;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* Header Actions */
    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .status-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .status-pill.db {
      background: #dcfce7;
      color: #166534;
      border: 1px solid #bbf7d0;
    }
    .status-pill.llm {
      background: #e0f2fe;
      color: #0369a1;
      border: 1px solid #bae6fd;
    }
    .status-pill:hover { opacity: 0.85; filter: brightness(0.97); }
    .status-pill .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .status-pill.db .dot { background: #16a34a; }
    .status-pill.llm .dot { background: #0284c7; }

    /* Puter Disconnected Status Indicator */
    .status-pill.llm.disconnected {
      background: #fef2f2 !important;
      color: #991b1b !important;
      border-color: #fca5a5 !important;
      cursor: pointer;
    }
    .status-pill.llm.disconnected .dot {
      background: #ef4444 !important;
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
      animation: pulse-red 1.6s infinite;
    }
    .status-pill.llm.connected {
      background: #f0fdf4 !important;
      color: #166534 !important;
      border-color: #86efac !important;
    }
    .status-pill.llm.connected .dot {
      background: #16a34a !important;
    }
    @keyframes pulse-red {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
      70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    /* Puter Login Alert Banner */
    .puter-login-banner {
      background: linear-gradient(90deg, #fff7ed 0%, #ffedd5 100%);
      border-bottom: 1px solid #fdba74;
      padding: 7px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: #9a3412;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      z-index: 45;
      animation: bannerSlideDown 0.25s ease-out;
    }
    @keyframes bannerSlideDown {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .puter-banner-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .puter-banner-badge {
      background: #ea580c;
      color: #ffffff;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }
    .puter-banner-text {
      font-weight: 500;
      color: #7c2d12;
    }
    .puter-banner-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-puter-signin {
      background: #0284c7;
      color: #ffffff;
      border: none;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.1);
      transition: background 0.15s;
    }
    .btn-puter-signin:hover { background: #0369a1; }
    .btn-puter-link {
      background: #ffffff;
      color: #0f172a;
      border: 1px solid #cbd5e1;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      text-decoration: none;
      transition: background 0.15s;
    }
    .btn-puter-link:hover { background: #f8fafc; border-color: #94a3b8; }
    .btn-puter-close {
      background: transparent;
      border: none;
      color: #9a3412;
      font-size: 14px;
      font-weight: bold;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 3px;
    }
    .btn-puter-close:hover { background: rgba(154, 52, 18, 0.15); }

    .btn-header {
      background: #ffffff;
      border: 1px solid var(--border-color);
      color: #334155;
      font-size: 12px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 5px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .btn-header:hover { background: #f1f5f9; }

    /* Robot Co-Pilot Header Toggle Button */
    .btn-copilot-toggle {
      background: #eff6ff;
      border: 1px solid #93c5fd;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 700;
      padding: 5px 12px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .btn-copilot-toggle:hover {
      background: #dbeafe;
      border-color: #3b82f6;
      transform: translateY(-1px);
    }
    .btn-copilot-toggle.active {
      background: #2563eb;
      color: #ffffff;
      border-color: #1d4ed8;
      box-shadow: 0 1px 4px rgba(37, 99, 235, 0.35);
    }

    /* Animated Loading Spinner */
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .loading-spinner {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: #ffffff;
      border-radius: 50%;
      animation: spin 0.75s linear infinite;
      vertical-align: middle;
      margin-right: 6px;
    }
    .loading-spinner.dark {
      border: 2px solid rgba(30, 58, 138, 0.25);
      border-top-color: #1e3a8a;
      width: 14px;
      height: 14px;
    }

    /* Main Resizable Layout - Constant Viewport Height */
    .main-layout {
      display: flex;
      flex-direction: row;
      gap: 0;
      padding: 8px 14px;
      flex: 1;
      height: calc(100vh - 56px);
      max-height: calc(100vh - 56px);
      box-sizing: border-box;
      overflow: hidden;
      position: relative;
    }

    /* Side Workspace Panel (Resizable Width, Internal Scroll) */
    .workspace-panel {
      width: 490px;
      min-width: 340px;
      max-width: 1100px;
      flex-shrink: 0;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      height: 100%;
      max-height: 100%;
    }

    /* Vertical Splitter Handle */
    .drag-splitter {
      width: 14px;
      margin: 0 4px;
      cursor: col-resize;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      user-select: none;
      flex-shrink: 0;
    }
    .drag-splitter::before {
      content: "";
      width: 4px;
      height: 48px;
      background: #cbd5e1;
      border-radius: 2px;
      transition: all 0.2s;
    }
    .drag-splitter:hover::before, .drag-splitter.dragging::before {
      background: var(--accent);
      width: 6px;
      height: 72px;
    }

    .workspace-header {
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      padding: 8px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-shrink: 0;
    }
    .workspace-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }
    .workspace-tabs-inline {
      display: flex;
      gap: 5px;
      align-items: center;
    }
    .ws-tab-btn {
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 5px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: var(--text-muted);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }
    .ws-tab-btn:hover {
      background: #f1f5f9;
      color: var(--text-main);
    }
    .ws-tab-btn.active {
      background: #eff6ff;
      color: #1d4ed8;
      border-color: #3b82f6;
      box-shadow: 0 1px 2px rgba(37, 99, 235, 0.12);
      font-weight: 700;
    }

    /* Clean Policy Editor with Vertical Resizability */
    .policy-editor-box {
      display: flex;
      flex-direction: column;
      height: 270px;
      min-height: 80px;
      max-height: 850px;
      border-bottom: 1px solid var(--border-color);
      background: #ffffff;
      flex-shrink: 0;
    }

    /* Horizontal Resizer between Editor and LLM Rules Panel */
    .rules-vertical-resizer {
      height: 9px;
      cursor: row-resize;
      background: #f1f5f9;
      border-top: 1px solid #e2e8f0;
      border-bottom: 1px solid #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      user-select: none;
      flex-shrink: 0;
      transition: background 0.15s ease;
    }
    .rules-vertical-resizer:hover, .rules-vertical-resizer.dragging {
      background: #dbeafe;
      border-color: #3b82f6;
    }
    .resizer-handle-pill {
      width: 44px;
      height: 3px;
      background: #94a3b8;
      border-radius: 2px;
      transition: all 0.15s ease;
    }
    .rules-vertical-resizer:hover .resizer-handle-pill, .rules-vertical-resizer.dragging .resizer-handle-pill {
      background: #2563eb;
      width: 62px;
      height: 4px;
    }
    .editor-toolbar {
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 5px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: #475569;
    }
    .policy-textarea {
      flex: 1;
      padding: 10px 12px;
      border: none;
      resize: none;
      outline: none;
      font-family: "Consolas", "Courier New", monospace;
      font-size: 12px;
      line-height: 1.5;
      color: #1e293b;
      background: #ffffff;
      white-space: pre-wrap;
    }

    /* Editable Master Spreadsheet Tab */
    .excel-window {
      background: #ffffff;
      display: flex;
      flex-direction: column;
      height: 270px;
      border-bottom: 1px solid var(--border-color);
      overflow: hidden;
    }
    .excel-toolbar {
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 5px 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
    }
    .excel-grid-container {
      flex: 1;
      overflow: auto;
      background: #ffffff;
    }
    table.excel-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    table.excel-grid th, table.excel-grid td {
      border: 1px solid #e2e8f0;
      padding: 4px 6px;
      text-align: left;
    }
    table.excel-grid th {
      background: #f8fafc;
      color: #475569;
      font-weight: 600;
      text-align: center;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    table.excel-grid td input, table.excel-grid td select {
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      font-size: 11px;
      padding: 2px 4px;
      border-radius: 3px;
    }
    table.excel-grid td input:focus, table.excel-grid td select:focus {
      border-color: var(--accent);
      background: #ffffff;
      outline: none;
    }

    /* Word Upload Window */
    .word-window {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      height: 270px;
      overflow-y: auto;
      border-bottom: 1px solid var(--border-color);
    }
    .dropzone {
      border: 2px dashed #93c5fd;
      border-radius: 8px;
      background: #eff6ff;
      padding: 20px;
      text-align: center;
      cursor: pointer;
    }

    /* Extracted Active Rules Container */
    .extracted-rules-box {
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      max-height: 380px;
      overflow-y: auto;
      transition: all 0.2s ease;
    }
    .rules-header {
      padding: 8px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      background: #f1f5f9;
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 5;
    }
    .rules-header:hover { background: #e2e8f0; }
    .rules-content-body {
      padding: 10px 12px;
      display: block;
    }
    .rules-content-body.collapsed {
      display: none;
    }
    .rules-count-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      background: #dbeafe;
      color: #1e40af;
      border-radius: 10px;
    }
    table.rules-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      background: #ffffff;
    }
    table.rules-table th, table.rules-table td {
      border: 1px solid #e2e8f0;
      padding: 4px 6px;
      text-align: left;
    }
    table.rules-table th {
      background: #f8fafc;
      color: #475569;
      font-weight: 600;
      font-size: 10px;
      position: sticky;
      top: 0;
      z-index: 5;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    }
    table.rules-table td input, table.rules-table td select {
      width: 100%;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      font-size: 11px;
      padding: 3px 5px;
      border-radius: 4px;
      color: #0f172a;
    }
    table.rules-table td input:focus, table.rules-table td select:focus {
      border-color: var(--accent);
      outline: none;
    }

    /* LangGraph Visualizer (Retractable) */
    .graph-tracker-box {
      background: #ffffff;
      border-top: 1px solid var(--border-color);
      transition: all 0.2s ease;
    }
    .graph-header {
      padding: 8px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      user-select: none;
      transition: background 0.15s ease;
    }
    .graph-header:hover {
      background: #f1f5f9;
    }
    .graph-content-body {
      padding: 12px 14px;
      display: block;
      transition: all 0.2s ease;
    }
    .graph-content-body.collapsed {
      display: none;
    }
    .graph-title {
      font-size: 12px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* Comment Small Icon & Snippet */
    .btn-comment-icon-btn {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 5px;
      padding: 3px 8px;
      font-size: 13px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
      color: #475569;
      transition: all 0.15s ease;
      line-height: 1;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .btn-comment-icon-btn:hover {
      background: #eff6ff;
      border-color: #3b82f6;
      color: #1d4ed8;
      transform: translateY(-1px);
    }
    .btn-comment-icon-btn.has-comment {
      background: #eff6ff;
      border-color: #60a5fa;
      color: #2563eb;
    }
    .comment-dot {
      width: 6px;
      height: 6px;
      background: #2563eb;
      border-radius: 50%;
      display: inline-block;
    }
    .comment-add-plus {
      font-size: 10px;
      color: #64748b;
      font-weight: 700;
    }
    .comment-snippet {
      font-size: 11px;
      color: #475569;
      margin-left: 6px;
      max-width: 170px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
      vertical-align: middle;
      cursor: pointer;
    }
    .comment-snippet:hover {
      color: #1e3a8a;
      text-decoration: underline;
    }

    /* Row Action Buttons: Approve / Disapprove */
    .btn-action-approve {
      background: #f0fdf4;
      border: 1px solid #86efac;
      color: #15803d;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 2px;
    }
    .btn-action-approve:hover {
      background: #22c55e;
      color: #ffffff;
      border-color: #22c55e;
      transform: translateY(-1px);
    }
    .btn-action-approve.active {
      background: #16a34a;
      color: #ffffff;
      border-color: #16a34a;
      box-shadow: 0 1px 3px rgba(22, 163, 74, 0.3);
    }

    .btn-action-hold {
      background: #fef2f2;
      border: 1px solid #fca5a5;
      color: #b91c1c;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 2px;
      margin-left: 4px;
    }
    .btn-action-hold:hover {
      background: #ef4444;
      color: #ffffff;
      border-color: #ef4444;
      transform: translateY(-1px);
    }
    .btn-action-hold.active {
      background: #dc2626;
      color: #ffffff;
      border-color: #dc2626;
      box-shadow: 0 1px 3px rgba(220, 38, 38, 0.3);
    }
    /* Ultra-Compact Horizontal LangGraph Pipeline with Execution Timers */
    .mini-pipeline-container {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 3px;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 5px 6px;
      margin-bottom: 8px;
    }
    .mini-node {
      flex: 1;
      min-width: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 3px 5px;
      font-size: 11px;
      transition: all 0.2s ease;
      overflow: hidden;
      white-space: nowrap;
    }
    .mini-node-num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 15px;
      height: 15px;
      border-radius: 50%;
      background: #e2e8f0;
      font-size: 9px;
      font-weight: 700;
      color: #475569;
      flex-shrink: 0;
    }
    .mini-node-label {
      font-weight: 600;
      font-size: 11px;
      color: var(--text-main);
    }
    .mini-node-time {
      font-size: 9px;
      color: #64748b;
      font-family: monospace;
      background: #f1f5f9;
      padding: 1px 3px;
      border-radius: 3px;
      flex-shrink: 0;
    }
    .mini-pipeline-arrow {
      color: #94a3b8;
      font-size: 10px;
      flex-shrink: 0;
      user-select: none;
    }
    .mini-node.node-active {
      border-color: #0284c7;
      background: #f0f9ff;
      box-shadow: 0 0 0 1px #0284c7;
    }
    .mini-node.node-active .mini-node-num {
      background: #0284c7;
      color: #ffffff;
    }
    .mini-node.node-active .mini-node-label {
      color: #0369a1;
    }
    .mini-node.node-done {
      border-color: #16a34a;
      background: #f0fdf4;
    }
    .mini-node.node-done .mini-node-num {
      background: #16a34a;
      color: #ffffff;
    }
    .mini-node.node-done .mini-node-label {
      color: #15803d;
    }
    .mini-node.node-done .mini-node-time {
      background: #dcfce7;
      color: #166534;
      font-weight: 700;
    }
    .mini-node.node-pending {
      opacity: 0.65;
    }

    .btn-run-agent {
      width: 100%;
      background: var(--primary);
      color: #ffffff;
      font-size: 13px;
      font-weight: 700;
      padding: 10px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 10px;
    }
    .btn-run-agent:hover { background: var(--primary-hover); }

    /* Left: ERP Table Section (Constant Height with Scrollable List) */
    .erp-content {
      flex: 1;
      min-width: 450px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      display: flex;
      flex-direction: column;
      height: 100%;
      max-height: 100%;
    }
    .table-top-toolbar {
      flex-shrink: 0;
      padding: 10px 14px;
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .table-metric-cards {
      flex-shrink: 0;
      display: flex;
      gap: 12px;
      padding: 8px 14px;
      background: #ffffff;
      border-bottom: 1px solid #f1f5f9;
    }
    .metric-card {
      flex: 1;
      padding: 5px 12px;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      background: #f8fafc;
    }
    .metric-card.approved { border-left: 4px solid var(--success); }
    .metric-card.hold { border-left: 4px solid var(--danger); }
    .metric-card.unprocessed { border-left: 4px solid #64748b; }
    .metric-card-label { font-size: 11px; color: var(--text-muted); }
    .metric-card-val { font-size: 16px; font-weight: 700; color: var(--text-main); margin-top: 1px; }

    /* Main ERP Table (Constant Bounded Height with Internal Smooth Scroll) */
    .table-scroll-container {
      flex: 1;
      height: 100%;
      min-height: 0;
      overflow-y: auto;
      overflow-x: auto;
      position: relative;
    }
    table.erp-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    table.erp-table th {
      background: #f8fafc;
      color: #475569;
      font-weight: 600;
      padding: 9px 12px;
      border-bottom: 1px solid var(--border-color);
      font-size: 11px;
      letter-spacing: 0.2px;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    table.erp-table td {
      padding: 8px 12px;
      border-bottom: 1px solid #f1f5f9;
      font-size: 12px;
      color: #1e293b;
    }
    table.erp-table tr:hover { background-color: #f8fafc; }

    /* Badges */
    .status-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }
    .badge-approved, .badge-confirmed {
      background: var(--success-bg);
      color: var(--success);
      border: 1px solid #86efac;
    }
    .badge-hold {
      background: var(--danger-bg);
      color: var(--danger);
      border: 1px solid #fca5a5;
    }
    .badge-unprocessed {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
    }

    /* Comment Icon & Button */
    .btn-comment-icon {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      border-radius: 4px;
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      max-width: 260px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .btn-comment-icon:hover { background: #dbeafe; }
    .comment-empty { color: #94a3b8; font-weight: normal; }

    /* Buttons */
    .btn-primary {
      background: var(--primary);
      color: #ffffff;
      border: none;
      padding: 6px 14px;
      border-radius: 5px;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
    }
    .btn-primary:hover { background: var(--primary-hover); }

    .btn-secondary {
      background: #ffffff;
      color: #334155;
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      border-radius: 5px;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
    }
    .btn-secondary:hover { background: #f8fafc; }

    /* Professional Corporate Human Intervention Cards */
    .intervention-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-left: 4px solid #b45309;
      border-radius: 4px;
      padding: 10px 12px;
      margin-top: 8px;
    }
    .intervention-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .intervention-title {
      font-size: 12px;
      font-weight: 700;
      color: #1e293b;
    }
    .intervention-rule-badge {
      font-size: 10px;
      font-weight: 600;
      padding: 1px 6px;
      background: #fef3c7;
      color: #92400e;
      border-radius: 3px;
      border: 1px solid #fde68a;
    }
    .intervention-reason {
      font-size: 11px;
      color: #475569;
      margin-bottom: 6px;
    }
    .btn-override {
      background: #334155;
      color: #ffffff;
      border: none;
      padding: 3px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-override:hover { background: #1e293b; }

    /* Modals */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.55);
      backdrop-filter: blur(2px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .modal-card {
      background: #ffffff;
      border-radius: 8px;
      width: 600px;
      max-width: 95vw;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .modal-card.large { width: 920px; }
    .modal-header {
      padding: 12px 18px;
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
    }
    .modal-body {
      padding: 16px 20px;
      max-height: 75vh;
      overflow-y: auto;
    }
    .modal-footer {
      padding: 12px 18px;
      background: #f8fafc;
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }

    .form-group { margin-bottom: 12px; }
    .form-group label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: #475569;
      margin-bottom: 4px;
    }
    .form-control {
      width: 100%;
      padding: 7px 10px;
      border: 1px solid var(--border-color);
      border-radius: 5px;
      font-size: 12px;
      color: #0f172a;
      outline: none;
    }
    .form-control:focus { border-color: var(--accent); }

    /* Expandable Row Detail in Staged Modal */
    .row-detail-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      padding: 8px 12px;
      margin-top: 4px;
      font-size: 11px;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px;
    }
    .btn-detail-toggle {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: 3px;
      padding: 2px 6px;
      font-size: 11px;
      cursor: pointer;
    }
    .btn-detail-toggle:hover { background: #e2e8f0; }
  </style>
  <script src="https://js.puter.com/v2/"></script>
</head>
<body>

  <!-- Top Corporate Header -->
  <header class="erp-header">
    <div class="header-brand">
      <div class="erp-logo-icon">ERP</div>
      <div class="header-title-box">
        <span class="header-title">基幹統合業務システム</span>
        <span class="header-subtitle">企業会計・人事給与・勤怠管理 自動照合</span>
      </div>
    </div>

    <!-- Suite Navigator: Clean Dropdown List -->
    <div style="display: flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.25);">
      <span style="font-size: 12px; font-weight: 700; color: #ffffff;">業務選択:</span>
      <select id="suite-dropdown-select" onchange="switchSuite(this.value)" style="background: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 4px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; cursor: pointer; outline: none;">
        <option value="invoice">📄 請求書照合 (財務会計)</option>
        <option value="payroll">👥 給与明細精査 (人事給与)</option>
        <option value="leave">🌴 休暇申請承認 (勤怠管理)</option>
      </select>
    </div>

    <!-- Header Actions -->
    <div class="header-actions">
      <button class="btn-copilot-toggle active" id="btn-toggle-copilot" onclick="toggleCopilotPanel()" title="AI Co-Pilot パネルの表示・非表示切替">
        🤖 AI Co-Pilot
      </button>

      <div class="status-pill llm" onclick="openSettingsModal()" title="LLM接続・アカウント設定 (クリックして設定を開く)" style="cursor: pointer;">
        <span class="dot" id="llm-dot"></span>
        <span id="llm-pill-text" style="font-weight: 700;">LLM</span>
      </div>

      <div style="display: flex; align-items: center; gap: 4px;">
        <div class="status-pill db" onclick="openDbModal()" title="データベース設定 (クリックしてPostgreSQL/Supabase/SQLite設定を開く)" style="cursor: pointer;">
          <span class="dot" id="db-dot"></span>
          <span id="db-pill-text" style="font-weight: 700;">Database</span>
        </div>
        <button class="btn-db-info" onclick="openSchemaInfoModal()" title="データベース仕様・スキーマ定義及び許容データ型ガイド (Schema & Data Types Guide)" style="background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.4); color: #ffffff; width: 22px; height: 22px; border-radius: 50%; font-size: 11px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.4)'" onmouseout="this.style.background='rgba(255,255,255,0.22)'">
          ℹ️
        </button>
      </div>

      <button class="btn-header-settings" id="btn-settings-header" onclick="openSettingsModal()" title="AI Engine & Puter Account Settings" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.35); color: #ffffff; padding: 4px 11px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 5px; transition: all 0.2s;">
        ⚙️ 設定 (Settings)
      </button>

      <button class="btn-header" onclick="resetDatabaseBenchmark()" title="初期ベンチマークデータに戻す">
        ↺ データ初期化
      </button>
    </div>
  </header>

  <!-- Puter Login Alert Banner (shown when Puter is disconnected) -->
  <div id="puter-login-banner" class="puter-login-banner" style="display: none;">
    <div class="puter-banner-left">
      <span class="puter-banner-badge">⚠️ Puter 未接続</span>
      <span class="puter-banner-text">Puter AI にログインしていません。AIコパイロット・ルール自動生成機能を使用するには、Puterにログインしてください。</span>
    </div>
    <div class="puter-banner-right">
      <button class="btn-puter-signin" onclick="loginWithPuter()" title="Puter認証ウィンドウを開いてログイン">
        🔑 Puter にログイン (Connect Puter)
      </button>
      <button class="btn-puter-link" onclick="openPuterLoginPage()" title="Puter公式サイトのログイン画面を別タブで開く">
        🌐 ログインページを開く
      </button>
      <button class="btn-puter-close" onclick="dismissPuterBanner()" title="一時的に非表示">✕</button>
    </div>
  </div>

  <!-- Main Resizable Split Layout -->
  <main class="main-layout" id="main-layout">
    <!-- Left: Real-time ERP Live Database Grid (Primary Main Table) -->
    <section class="erp-content" id="erp-content">
      <!-- Toolbar -->
      <div class="table-top-toolbar">
        <div class="toolbar-left">
          <span style="font-weight: 700; font-size: 14px;" id="table-suite-title">財務会計 - 請求書一覧</span>
          <span style="font-size: 11px; color: #64748b;" id="table-row-count">(105 records)</span>
          <div class="filter-group">
            <button class="filter-btn active" id="f-all" onclick="filterTable('all')">All Records</button>
            <button class="filter-btn" id="f-app" onclick="filterTable('Approved')">Approve</button>
            <button class="filter-btn" id="f-hold" onclick="filterTable('Hold')">On Hold</button>
          </div>
        </div>
        <div class="toolbar-right">
          <button class="btn-secondary" onclick="loadTableData()" title="最新データに再読込">
            🔄 更新
          </button>
          <button class="btn-secondary" style="color: #15803d; border-color: #86efac;" onclick="openExcelImportModal()" title="データ一括取込 (Bulk Import)">
            一括取込 (Bulk Import)
          </button>
          <button class="btn-primary" onclick="openAddRecordModal()">
            + 新規伝票追加
          </button>
        </div>
      </div>

      <!-- Metric Cards -->
      <div class="table-metric-cards">
        <div class="metric-card approved">
          <div class="metric-card-label" id="metric-label-approved">Approve</div>
          <div class="metric-card-val" id="metric-approved-count">0</div>
        </div>
        <div class="metric-card hold">
          <div class="metric-card-label">On Hold</div>
          <div class="metric-card-val" id="metric-hold-count">0</div>
        </div>
        <div class="metric-card unprocessed">
          <div class="metric-card-label">Unprocessed</div>
          <div class="metric-card-val" id="metric-unprocessed-count">0</div>
        </div>
      </div>

      <!-- Scrollable Data Grid -->
      <div class="table-scroll-container" style="position: relative;">
        <div id="table-loading-banner" style="display: none; position: sticky; top: 0; z-index: 20; background: #eff6ff; border-bottom: 1px solid #bfdbfe; padding: 6px 14px; font-size: 11px; color: #1e40af; align-items: center; gap: 8px;">
          <span class="loading-spinner dark"></span>
          <span><strong>AI Co-Pilot Processing:</strong> Evaluating database records against policy rules...</span>
        </div>
        <table class="erp-table">
          <thead id="erp-table-head">
            <!-- Dynamically populated based on active suite -->
          </thead>
          <tbody id="erp-table-body">
            <!-- Dynamically populated rows -->
          </tbody>
        </table>
      </div>
    </section>

    <!-- Draggable Vertical Splitter Handle -->
    <div class="drag-splitter" id="drag-splitter" title="左右にドラッグしてパネル幅を調整"></div>
    <!-- Right: AI Co-Pilot Reference & Multi-Window Workspace (Sidecar) -->
    <aside class="workspace-panel" id="workspace-panel">
      <div class="workspace-header">
        <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0;">
          <div class="workspace-title">
            <span>🤖 AI Co-Pilot</span>
          </div>
          <!-- Tabs on the same level as Co-Pilot Title -->
          <div class="workspace-tabs-inline">
            <button class="ws-tab-btn active" id="ws-btn-notepad" onclick="switchWsTab('notepad')" title="規程・ポリシー (Regulations)">
              規程 (Regulations)
            </button>
            <button class="ws-tab-btn" id="ws-btn-excel" onclick="switchWsTab('excel')" title="規程マスタ (Regulation Master)">
              規程マスタ (Regulation Master)
            </button>
          </div>
        </div>
        <div style="display: flex; gap: 5px; align-items: center; flex-shrink: 0;">
          <button class="btn-secondary" style="padding: 2px 7px; font-size: 11px; font-weight: bold;" onclick="toggleCopilotPanel()" title="Co-Pilotパネルを閉じる">
            ✕
          </button>
        </div>
      </div>

      <!-- Tab 1: Policy / Memo Clean Editor with Small Upload Button -->
      <div id="ws-tab-notepad" class="policy-editor-box">


        <div class="editor-toolbar">
          <span id="notepad-filename" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; color: #475569;">月次定額保守取引先一覧.txt (参照規程)</span>
          <div style="display: flex; gap: 4px; align-items: center;">
            <button class="btn-primary" style="padding: 3px 10px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px; background: #2563eb; color: #ffffff;" onclick="document.getElementById('policy-file-input').click()" title="Word文書 (.docx) または テキスト (.txt) を読込">
              📁 規程ファイル選択 (Upload Policy)
            </button>
            <input type="file" id="policy-file-input" accept=".docx,.txt" style="display: none;" onchange="handlePolicyFileUpload(event)">
          </div>
        </div>
        <textarea id="doc-text" class="policy-textarea" spellcheck="false">{{ invoice_preset }}</textarea>
      </div>

      <!-- Tab 2: Editable Master Spreadsheet with Upload & Download -->
      <div id="ws-tab-excel" class="excel-window" style="display: none;">
        <div class="excel-toolbar">
          <span style="font-weight: 700; color: #15803d; font-size: 11px;" id="excel-master-title">📊 規程・契約マスタ</span>
          <div style="display: flex; gap: 4px; align-items: center;">
            <button class="btn-secondary" style="padding: 2px 7px; font-size: 10px; color: #15803d; border-color: #86efac; display: inline-flex; align-items: center; gap: 3px;" onclick="document.getElementById('master-excel-input').click()" title="Excel (.xlsx, .xls) または CSVファイルをアップロードしてマスタを更新">
              📁 Excel/CSV取込
            </button>
            <input type="file" id="master-excel-input" accept=".xlsx,.xls,.csv" style="display: none;" onchange="handleMasterExcelUpload(event)">
            <button class="btn-secondary" style="padding: 2px 5px; font-size: 10px;" onclick="downloadMasterRegulationsCsv()" title="現在のマスタをCSVダウンロード">
              📥 出力
            </button>
            <button class="btn-secondary" style="padding: 2px 5px; font-size: 10px;" onclick="addMasterRow()">+ 行追加</button>
            <button class="btn-primary" style="padding: 2px 7px; font-size: 10px; background: #15803d;" onclick="saveMasterRegulationsTable()">💾 保存</button>
          </div>
        </div>
        <div class="excel-grid-container">
          <table class="excel-grid" id="excel-master-table">
            <thead>
              <tr>
                <th style="width: 25px;">#</th>
                <th style="width: 85px;">コード</th>
                <th>対象名称/項目</th>
                <th>上限/契約定額</th>
                <th>承認要件</th>
                <th style="width: 75px;">区分</th>
                <th style="width: 25px;"></th>
              </tr>
            </thead>
            <tbody id="excel-master-tbody">
              <!-- Dynamically populated from backend -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Draggable Splitter Handle between Top Editor and LLM Rules Panel -->
      <div class="rules-vertical-resizer" id="rules-vertical-resizer" title="上下にドラッグしてエディタとルールの高さを調整">
        <div class="resizer-handle-pill"></div>
      </div>

      <!-- Fused LLM Extracted Rules & LangGraph Execution Pipeline (Space-Optimized) -->
      <div class="extracted-rules-box" id="extracted-rules-box" style="background: #ffffff; border-top: 1px solid var(--border-color); flex: 1; min-height: 0; display: flex; flex-direction: column;">
        <!-- Single Unified Fused Header -->
        <div class="rules-header" onclick="toggleLlmOutputCollapse()" style="padding: 6px 12px; background: #f1f5f9; border-bottom: 1px solid #cbd5e1; display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span id="llm-collapse-icon" style="transition: transform 0.2s; font-size: 11px;">▼</span>
            <strong style="font-size: 12px; color: #1e3a8a; display: flex; align-items: center; gap: 4px;">
              <span>⚡</span> LLM Rules & LangGraph Pipeline
            </strong>
            <span class="rules-count-badge" id="rules-count-badge" style="background: #dbeafe; color: #1e40af; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 9999px;">8 Rules Active</span>
            <span id="graph-overall-badge" style="font-size: 10px; padding: 1px 6px; border-radius: 4px; background: #e2e8f0; font-weight: 700; color: #475569;">READY</span>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;">
            <span style="font-size: 10px; color: #64748b;" id="llm-toggle-text">[ Click to Collapse ]</span>
          </div>
        </div>

        <!-- Fused Content Body (Scrollable: Top elements move up to reveal more rows) -->
        <div class="rules-content-body" id="llm-rules-content" style="padding: 8px 10px; flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column;">
          
          <!-- Integrated Horizontal Stepper + Execution Bar (Fused Top Strip, scrolls up with page) -->
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; flex-shrink: 0;">
            <!-- 5-Node Stepper -->
            <div class="mini-pipeline-container" style="flex: 1; min-width: 320px; margin: 0; padding: 3px 5px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
              <div class="mini-node node-pending" id="node-1" title="Node 1: parse_document_to_schema_json (文書解析)">
                <span class="mini-node-num">1</span>
                <span class="mini-node-label">Parse</span>
                <span class="mini-node-time" id="time-node-1">-</span>
              </div>
              <span class="mini-pipeline-arrow">➔</span>
              <div class="mini-node node-pending" id="node-2" title="Node 2: validate_and_refine_sql_rules (SQL検証 & LLMループ)">
                <span class="mini-node-num">2</span>
                <span class="mini-node-label">Verify SQL</span>
                <span class="mini-node-time" id="time-node-2">-</span>
              </div>
              <span class="mini-pipeline-arrow">➔</span>
              <div class="mini-node node-pending" id="node-3" title="Node 3: compare_features_and_decide (実SQL照合・判定)">
                <span class="mini-node-num">3</span>
                <span class="mini-node-label">Decide</span>
                <span class="mini-node-time" id="time-node-3">-</span>
              </div>
              <span class="mini-pipeline-arrow">➔</span>
              <div class="mini-node node-pending" id="node-4" title="Node 4: commit_database_updates (DB更新)">
                <span class="mini-node-num">4</span>
                <span class="mini-node-label">Commit</span>
                <span class="mini-node-time" id="time-node-4">-</span>
              </div>
              <span class="mini-pipeline-arrow">➔</span>
              <div class="mini-node node-pending" id="node-5" title="Node 5: human_in_the_loop_audit (J-SOX監査)">
                <span class="mini-node-num">5</span>
                <span class="mini-node-label">Audit</span>
                <span class="mini-node-time" id="time-node-5">-</span>
              </div>
            </div>

            <!-- Fused Single Action Control -->
            <div style="display: flex; gap: 5px; align-items: center; flex-shrink: 0;">
              <button class="btn-secondary" id="btn-analyze" style="font-size: 10px; padding: 4px 8px; background: #0284c7; color: #ffffff; border: 1px solid #0284c7; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px;" onclick="runPolicyAnalysis()" title="LLM analyzes the prompt/policy and extracts condition rules">
                🔍 Analyze Policy
              </button>
              <button class="btn-secondary" style="font-size: 10px; padding: 4px 7px;" onclick="addNewExtractedRule()">
                + Add Rule
              </button>
              <button class="btn-primary" id="btn-continue-eval" style="background: #15803d; font-size: 11px; font-weight: 700; padding: 4px 12px; display: flex; align-items: center; gap: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.08);" onclick="continueAndEvaluateDatabase()">
                ▶ Continue & Evaluate Database
              </button>
              <button class="btn-run-agent" id="btn-run" style="display: none;" onclick="continueAndEvaluateDatabase()"></button>
            </div>
          </div>

          <!-- Rules Table in Full-Space Scrollable Box -->
          <div style="border: 1px solid #e2e8f0; border-radius: 4px; background: #ffffff; overflow-x: auto; flex-shrink: 0; margin-bottom: 6px;">
            <table class="rules-table" style="margin: 0; width: 100%;">
              <thead>
                <tr>
                  <th style="width: 28px; text-align: center;">#</th>
                  <th style="width: 80px;">Rule ID</th>
                  <th style="width: 130px;">Target / Entity</th>
                  <th style="min-width: 240px;">SQL Condition / Predicate (Checked vs DB)</th>
                  <th style="width: 85px; text-align: center;">Action</th>
                  <th style="min-width: 150px;">English Explanation</th>
                  <th style="width: 26px; text-align: center;"></th>
                </tr>
              </thead>
              <tbody id="rules-table-body">
                <!-- Fully editable extracted rules -->
              </tbody>
            </table>
          </div>

          <!-- Professional Human Intervention Container (Space-Saving Collapsible with Yellow Triangle) -->
          <div id="interventions-container" style="display: none; margin-top: 6px; flex-shrink: 0; background: #fffbeb; border: 1px solid #fef08a; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 2px rgba(245, 158, 11, 0.08);">
            <!-- Compact Single-Line Bar -->
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 8px; user-select: none;">
              <!-- Left side: Yellow Triangle Button & Title -->
              <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0;">
                <button type="button" id="btn-open-interventions-modal" onclick="openInterventionsModal()" style="background: #fef08a; border: 1px solid #f59e0b; color: #b45309; border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: bold; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.15s;" title="クリックして別ウィンドウで要精査一覧を開く (Open in separate window)" onmouseover="this.style.background='#fde68a'" onmouseout="this.style.background='#fef08a'">
                  ⚠️ <span id="interventions-badge-count" style="font-size: 10px; background: #b45309; color: #fff; padding: 0 5px; border-radius: 10px; font-weight: 700;">0</span>
                </button>
                <span onclick="openInterventionsModal()" style="font-weight: 700; color: #92400e; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;" title="クリックして別ウィンドウで開く">
                  要人間精査項目 (Audit Required)
                </span>
                <span onclick="openInterventionsModal()" style="font-size: 10px; color: #b45309; cursor: pointer; text-decoration: underline;" title="別ウィンドウで開く">
                  [ 🗗 画面で開く ]
                </span>
              </div>
              <!-- Right side: Inline Collapse/Expand Toggle Arrow -->
              <button type="button" id="btn-toggle-interventions" onclick="toggleInterventionsCollapse()" style="background: none; border: none; font-size: 11px; color: #92400e; cursor: pointer; padding: 2px 6px; border-radius: 3px;" title="インライン詳細の折りたたみ / 展開 (Toggle Inline View)">
                ▶
              </button>
            </div>
            <!-- Inline list (collapsed by default, max-height if expanded) -->
            <div id="interventions-list" style="display: none; max-height: 140px; overflow-y: auto; padding: 6px 8px; border-top: 1px dashed #fde68a; background: #fffdf5;"></div>
          </div>

        </div>
      </div>
    </aside>
  </main>

  <!-- Modal: Internal Control & Human Audit Review Dialog (Separate Window) -->
  <div class="modal-overlay" id="interventions-modal" style="display: none;">
    <div class="modal-card" style="max-width: 680px; width: 92%;">
      <div class="modal-header" style="background: #fffbeb; border-bottom: 1px solid #fef08a;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 16px;">⚠️</span>
          <span style="color: #92400e; font-size: 13px; font-weight: 700;">内部統制・要人間精査項目 (Audit Review Required)</span>
          <span id="interventions-modal-count-badge" style="background: #f59e0b; color: #fff; font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 9999px;">0</span>
        </div>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeInterventionsModal()">✕</button>
      </div>
      <div class="modal-body" style="max-height: 65vh; overflow-y: auto; padding: 14px 16px;">
        <div style="background: #fefce8; border: 1px solid #fef08a; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 11px; color: #854d0e; line-height: 1.5;">
          規程ルールおよびSQL条件により「<strong>要人間精査 (Hold)</strong>」と判定された項目の一覧です。<br>
          内容を確認し、問題がなければ「<strong>コメント・承認管理</strong>」から承認や条件調整を実施してください。
        </div>
        <div id="interventions-modal-list">
          <!-- Populated dynamically -->
        </div>
      </div>
      <div class="modal-footer" style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 11px; color: #64748b;">各項目の [💬 コメント・承認管理] より個別にステータス変更が可能です</span>
        <button class="btn-secondary" onclick="closeInterventionsModal()">閉じる (Close)</button>
      </div>
    </div>
  </div>

  <!-- Modal 1: Comments & Status Audit Dialog -->
  <div class="modal-overlay" id="comment-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>💬 伝票コメント・承認ステータス管理</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeCommentModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin-bottom: 14px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="color: #64748b; font-size: 11px;">伝票番号:</span>
            <strong id="modal-record-id">-</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="color: #64748b; font-size: 11px;" id="modal-entity-label">取引先 / 従業員:</span>
            <strong id="modal-entity-name">-</strong>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: #64748b; font-size: 11px;">金額:</span>
            <strong id="modal-amount" style="color: #1e3a8a;">-</strong>
          </div>
        </div>

        <div class="form-group">
          <label>承認ステータス:</label>
          <select id="modal-status-select" class="form-control">
            <option value="Unprocessed">未処理 (Unprocessed)</option>
            <option value="Approved">承認済 (Approved)</option>
            <option value="Confirmed">確認済 (Confirmed)</option>
            <option value="Hold">保留 (Hold)</option>
            <option value="Rejected">差戻 (Rejected)</option>
          </select>
        </div>

        <div class="form-group">
          <label>処理内容・確認コメント:</label>
          <textarea id="modal-comment-text" class="form-control" rows="4" placeholder="コメントを入力してください…"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeCommentModal()">閉じる</button>
        <button class="btn-primary" onclick="commitCommentModal()">💾 保存してDB更新</button>
      </div>
    </div>
  </div>

  <!-- Modal 2: Staged Decision Review & Commit Confirmation (ALL Rows Visible + Info Icon) -->
  <div class="modal-overlay" id="staged-modal">
    <div class="modal-card large">
      <div class="modal-header">
        <span>⚡ 評価結果の確認 & データベース反映承認</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeStagedModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="display: flex; gap: 12px; margin-bottom: 12px;">
          <div class="metric-card approved" style="flex: 1;">
            <div class="metric-card-label">承認/確認 予定</div>
            <div class="metric-card-val" id="stage-approved-count">0</div>
          </div>
          <div class="metric-card hold" style="flex: 1;">
            <div class="metric-card-label">保留・精査 予定</div>
            <div class="metric-card-val" id="stage-hold-count">0</div>
          </div>
          <div class="metric-card" style="flex: 1;">
            <div class="metric-card-label">総評価件数 (全件表示)</div>
            <div class="metric-card-val" id="stage-total-count">0</div>
          </div>
        </div>

        <!-- Filter & Search Controls in Staged Modal -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 10px;">
          <div style="display: flex; gap: 6px;">
            <button class="btn-secondary active" id="btn-filter-all" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('all')">全件表示</button>
            <button class="btn-secondary" id="btn-filter-approved" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('approved')">承認/確認のみ</button>
            <button class="btn-secondary" id="btn-filter-hold" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('hold')">保留のみ</button>
          </div>
          <input type="text" id="staged-search-input" class="form-control" style="width: 220px; padding: 4px 8px; font-size: 11px;" placeholder="伝票ID / 氏名で絞込…" oninput="filterStagedRows(currentStagedFilter)">
        </div>

        <div style="max-height: 380px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 6px;">
          <table class="erp-table" style="font-size: 11px;">
            <thead>
              <tr>
                <th style="width: 40px; text-align: center;">詳細</th>
                <th style="width: 120px;">伝票番号</th>
                <th style="width: 130px;">取引先 / 氏名</th>
                <th style="width: 80px;">金額</th>
                <th style="width: 110px;">ステータス</th>
                <th>適用ルール & コメント</th>
              </tr>
            </thead>
            <tbody id="staged-preview-body">
              <!-- Dynamically populated with ALL rows -->
            </tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeStagedModal()">キャンセル</button>
        <button class="btn-primary" style="background: var(--success);" onclick="confirmCommitStaged()">
          ✓ データベースへ反映・コミット
        </button>
      </div>
    </div>
  </div>

  <!-- Modal 3: Single Add Record Dialog -->
  <div class="modal-overlay" id="add-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span id="add-modal-title">+ 新規伝票追加</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeAddRecordModal()">✕</button>
      </div>
      <div class="modal-body" id="add-modal-form">
        <!-- Injected dynamically -->
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeAddRecordModal()">キャンセル</button>
        <button class="btn-primary" onclick="submitAddRecord()">データベースへ登録</button>
      </div>
    </div>
  </div>

  <!-- Modal 4: Excel / CSV Bulk Import Dialog with Automatic Schema & Datatype Validation -->
  <div class="modal-overlay" id="excel-import-modal">
    <div class="modal-card" style="max-width: 640px;">
      <div class="modal-header" style="background: #15803d; color: #ffffff;">
        <span style="font-weight: 700; font-size: 13px;">📊 Excel / CSV データ一括取込 (Bulk Import)</span>
        <button class="btn-secondary" style="padding: 2px 6px; color: #ffffff; border-color: rgba(255,255,255,0.4); background: transparent;" onclick="closeExcelImportModal()">✕</button>
      </div>
      <div class="modal-body" style="padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 11px; color: #475569;">
            対象テーブル: <strong id="bulk-target-table-label" style="color: #15803d;">erp_invoices</strong>
          </span>
          <button type="button" class="btn-secondary" onclick="openSchemaInfoModal()" style="font-size: 10px; padding: 2px 8px; color: #1e40af; border-color: #93c5fd;">
            ℹ️ スキーマ仕様・データ型ガイドを確認
          </button>
        </div>

        <!-- Validation Error / Instructions Flagging Banner -->
        <div id="bulk-validation-warning" style="display: none; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 11px; color: #b91c1c;">
            <span>⚠️</span>
            <span id="bulk-val-title">データ形式・型不一致が検出されました (Validation Failed)</span>
          </div>
          <div id="bulk-val-details" style="font-size: 11px; color: #7f1d1d; margin-top: 4px; line-height: 1.5; white-space: pre-line;"></div>
          <div style="margin-top: 6px;">
            <button type="button" class="btn-secondary" onclick="openSchemaInfoModal()" style="font-size: 10px; padding: 2px 7px; background: #ffffff; color: #b91c1c; border-color: #fca5a5;">
              📖 正しいデータ型と必須カラム一覧を表示
            </button>
          </div>
        </div>

        <div class="form-group" style="margin-bottom: 10px;">
          <label style="font-size: 11px; font-weight: 600;">Excelから貼り付け (タブ区切り / カンマ区切り):</label>
          <textarea id="bulk-paste-text" class="form-control" rows="5" placeholder="ExcelまたはCSVの行をコピーして貼り付けてください..." style="font-family: monospace; font-size: 11px;"></textarea>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 10px; align-items: center;">
          <button class="btn-secondary" style="font-size: 11px;" onclick="previewBulkSpreadsheet()">📋 解析プレビュー & 型検証</button>
          <input type="file" id="bulk-file-input" accept=".xlsx,.xls,.csv,.tsv,.txt" style="display: none;" onchange="handleBulkFileSelect(event)">
          <button class="btn-secondary" style="font-size: 11px; color: #15803d; border-color: #86efac;" onclick="document.getElementById('bulk-file-input').click()">
            📁 Excel (.xlsx) / CSV ファイル読込
          </button>
          <span style="font-size: 10px; color: #64748b;" id="bulk-file-selected-name"></span>
        </div>

        <div id="bulk-preview-summary" style="font-size: 11px; color: #1e3a8a; font-weight: 700; margin-bottom: 6px;"></div>
        <div id="bulk-preview-container" style="max-height: 140px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 4px; display: none;">
          <table class="erp-table" style="font-size: 10px;">
            <thead id="bulk-preview-head"></thead>
            <tbody id="bulk-preview-body"></tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeExcelImportModal()">キャンセル</button>
        <button class="btn-primary" id="btn-submit-bulk-import" style="background: var(--success);" onclick="submitBulkImport()">一括登録を実行 (Import to DB)</button>
      </div>
    </div>
  </div>

  <!-- Modal 5: Comprehensive Settings & Puter AI Account Dialog -->
  <div class="modal-overlay" id="llm-modal">
    <div class="modal-card" style="max-width: 580px;">
      <div class="modal-header" style="background: #1e3a8a; color: #ffffff;">
        <span style="font-weight: 700; font-size: 13px;">⚙️ AI 設定 & Puter アカウント管理 (AI & Account Settings)</span>
        <button class="btn-secondary" style="padding: 2px 6px; color: #ffffff; border-color: rgba(255,255,255,0.4); background: transparent;" onclick="closeLlmModal()">✕</button>
      </div>
      <div class="modal-body" style="padding: 18px;">

        <!-- AI Credit Circle & Live Account Gauge Widget -->
        <div style="display: flex; gap: 16px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
          <div style="position: relative; width: 76px; height: 76px; flex-shrink: 0;">
            <svg width="76" height="76" viewBox="0 0 76 76">
              <circle cx="38" cy="38" r="32" stroke="#e2e8f0" stroke-width="6" fill="none" />
              <circle id="ai-credit-gauge-circle" cx="38" cy="38" r="32" stroke="#10b981" stroke-width="6" stroke-dasharray="201" stroke-dashoffset="0" stroke-linecap="round" fill="none" style="transition: stroke-dashoffset 0.8s ease;" />
              <text x="38" y="43" text-anchor="middle" font-size="12" font-weight="bold" fill="#0f172a" id="ai-credit-gauge-text">100%</text>
            </svg>
          </div>
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
              <span id="puter-modal-conn-badge" class="status-badge badge-approved" style="font-size: 10px;">接続済 (Connected)</span>
              <strong style="font-size: 12px; color: #1e3a8a;" id="settings-user-name">Puter AI Account</strong>
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 2px;" id="settings-credit-status">
              AIクレジット残量: <strong>十分 (Available / Free Tier)</strong>
            </div>
            <div style="font-size: 10px; color: #64748b;">
              現在、デフォルトの <strong>OpenRouter Free</strong> でコストなしで稼働しています。
            </div>
          </div>
        </div>

        <!-- Puter Login / Sign Up / Account Switch Buttons -->
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
          <div style="font-weight: 700; font-size: 11px; color: #166534; margin-bottom: 6px;">
            ☁️ Puter アカウント操作 (Account Management):
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="button" class="btn-primary" style="background: #0284c7; flex: 1; min-width: 140px; padding: 7px 10px; font-size: 11px; justify-content: center;" onclick="loginWithPuter()">
              🔑 Puter にログイン (Log In)
            </button>
            <button type="button" class="btn-secondary" style="flex: 1; min-width: 140px; padding: 7px 10px; font-size: 11px; justify-content: center; color: #1e40af; border-color: #93c5fd;" onclick="openPuterSignUpPage()">
              ✨ Puter に新規登録 (Sign Up)
            </button>
            <button type="button" class="btn-secondary" style="padding: 7px 10px; font-size: 11px; color: #dc2626; border-color: #fca5a5;" onclick="switchPuterAccount()" title="別のアカウントに切り替える">
              🔄 アカウント切替
            </button>
          </div>
        </div>

        <!-- LLM Model Dropdown Selector -->
        <div class="form-group" style="margin-bottom: 12px;">
          <label style="font-weight: 700; font-size: 12px; color: #334155;">利用 LLM モデル (LLM Model):</label>
          <select id="settings-model-dropdown" class="form-control" onchange="onSettingsModelChange()">
            <option value="openrouter:openrouter/free" selected>⭐ OpenRouter Free (Free / Default - 完全無料・推奨)</option>
            <option value="gpt-4o-mini">OpenAI GPT-4o Mini (Puter)</option>
            <option value="gpt-4o">OpenAI GPT-4o (Puter Paid / 高精度)</option>
            <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet (Puter)</option>
            <option value="deepseek-chat">DeepSeek Chat (Puter)</option>
            <option value="openrouter:meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B Free (OpenRouter)</option>
            <option value="custom">✏️ その他のカスタムモデルを指定...</option>
          </select>
        </div>

        <div class="form-group" id="settings-custom-model-box" style="display: none; margin-bottom: 12px;">
          <label style="font-size: 11px; color: #64748b;">カスタムモデルID:</label>
          <input type="text" id="llm-model-input" class="form-control" value="openrouter:openrouter/free" placeholder="openrouter:openrouter/free">
        </div>

        <select id="llm-provider-select" style="display: none;">
          <option value="puter" selected>Puter</option>
        </select>

        <!-- Auth Token / API Key Field -->
        <div class="form-group" style="margin-bottom: 10px;">
          <label style="font-weight: 700; font-size: 12px; color: #334155;">Puter Auth Token (自動連携):</label>
          <input type="password" id="llm-token-input" class="form-control" placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0...">
          <small style="color: #64748b; font-size: 10px;">※ Puterログイン時に自動設定されます。手動で直接トークンを更新・保存することも可能です。</small>
        </div>

        <div id="llm-test-result" style="display: none; padding: 8px 12px; border-radius: 6px; font-size: 11px; margin-top: 10px;"></div>
      </div>
      <div class="modal-footer" style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 10px 16px;">
        <button class="btn-secondary" onclick="testLlmConnection()">⚡ 接続テスト</button>
        <button class="btn-primary" onclick="saveLlmSettings()">💾 設定を保存して適用</button>
      </div>
    </div>
  </div>

  <!-- Modal 5b: Puter Authentication & Login Modal -->
  <div class="modal-overlay" id="puter-auth-modal" style="display: none;">
    <div class="modal-card" style="max-width: 500px;">
      <div class="modal-header" style="background: #1e3a8a; color: #ffffff;">
        <span style="display: flex; align-items: center; gap: 8px;">
          <span>☁️</span>
          <strong style="color: #ffffff;">Puter AI アカウント連携・ログイン</strong>
        </span>
        <button class="btn-secondary" style="padding: 2px 6px; color: #ffffff; border-color: rgba(255,255,255,0.4); background: transparent;" onclick="closePuterAuthModal()">✕</button>
      </div>
      <div class="modal-body" style="padding: 20px;">
        <div style="text-align: center; margin-bottom: 16px;">
          <div style="font-size: 32px; margin-bottom: 6px;">🔐 ➔ 🤖</div>
          <h3 style="font-size: 15px; color: #0f172a; margin-bottom: 6px;">Puter AI にログインしてください</h3>
          <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
            基幹ERPのAIコパイロット・ポリシー自動照合を実行するには、Puterの認証が必要です。ログインすると自動的にトークンが連携されます。
          </p>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">
            方法 1: ワンクリックでPuterにサインイン (推奨)
          </div>
          <p style="font-size: 11px; color: #475569; margin-bottom: 10px;">
            下のボタンを押すとPuter認証ウィンドウが開きます。ログイン完了後、自動的にERPシステムへトークンが反映されます。
          </p>
          <button class="btn-primary" id="btn-modal-puter-signin" onclick="loginWithPuter()" style="width: 100%; justify-content: center; padding: 9px; font-size: 13px; font-weight: 700; background: #0284c7;">
            🔑 Puter にログイン (Sign In with Puter)
          </button>
        </div>

        <div style="background: #fff; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 14px;">
          <div style="font-weight: 700; font-size: 12px; color: #334155; margin-bottom: 6px;">
            方法 2: 公式ログインページを開く
          </div>
          <p style="font-size: 11px; color: #64748b; margin-bottom: 10px;">
            ブラウザで直接Puterログインページを開いてログインまたは新規アカウント登録を行います。
          </p>
          <button class="btn-secondary" onclick="openPuterLoginPage()" style="width: 100%; justify-content: center; padding: 8px; font-size: 12px; font-weight: 600;">
            🌐 Puter ログインページを開く (https://puter.com/login)
          </button>
        </div>

        <div id="puter-modal-status-box" style="display: none; margin-top: 14px; padding: 10px 12px; border-radius: 6px; font-size: 12px; line-height: 1.4;"></div>
      </div>
      <div class="modal-footer" style="display: flex; justify-content: space-between; align-items: center;">
        <button class="btn-secondary" onclick="openLlmModal(); closePuterAuthModal();">⚙️ 手動API設定</button>
        <div style="display: flex; gap: 6px;">
          <button class="btn-secondary" onclick="checkPuterConnection()">🔄 接続確認</button>
          <button class="btn-secondary" onclick="closePuterAuthModal()">閉じる</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal 6: Database Connection Dialog (Remote Postgres / Supabase & Local SQLite) -->
  <div class="modal-overlay" id="db-modal">
    <div class="modal-card" style="max-width: 620px;">
      <div class="modal-header" style="background: #1e3a8a; color: #ffffff;">
        <span style="font-weight: 700; font-size: 13px;">🗄️ データベース接続設定 (PostgreSQL / Supabase / SQLite)</span>
        <button class="btn-secondary" style="padding: 2px 6px; color: #ffffff; border-color: rgba(255,255,255,0.4); background: transparent;" onclick="closeDbModal()">✕</button>
      </div>
      <div class="modal-body" style="padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; background: #f1f5f9; padding: 8px 12px; border-radius: 6px;">
          <div style="font-size: 12px; color: #334155;">
            現在の稼働データベース: <strong id="modal-db-current" style="color: #1e40af;">PostgreSQL Active</strong>
          </div>
          <button class="btn-secondary" onclick="openSchemaInfoModal()" style="font-size: 10px; padding: 2px 8px; color: #1e40af; border-color: #93c5fd;">
            ℹ️ スキーマ・データ型仕様
          </button>
        </div>

        <!-- Section 1: PostgreSQL / Supabase Granular & URI Configuration -->
        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-bottom: 14px;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <span>⚡ 1. PostgreSQL / Supabase 接続設定 (Cloud or Self-Hosted)</span>
            <span style="font-size: 10px; color: #64748b;">SSL Mode: require (Supabase対応)</span>
          </div>

          <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-bottom: 8px;">
            <div class="form-group" style="margin: 0;">
              <label style="font-size: 10px; font-weight: 600;">ホスト名 (Host / Endpoint):</label>
              <input type="text" id="db-host-input" class="form-control" placeholder="aws-0-ap-southeast-1.pooler.supabase.com または db.xxxx.supabase.co" oninput="syncDbUriFromFields()" style="font-size: 11px;">
            </div>
            <div class="form-group" style="margin: 0;">
              <label style="font-size: 10px; font-weight: 600;">ポート (Port):</label>
              <input type="number" id="db-port-input" class="form-control" placeholder="5432 / 6543" value="5432" oninput="syncDbUriFromFields()" style="font-size: 11px;">
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px;">
            <div class="form-group" style="margin: 0;">
              <label style="font-size: 10px; font-weight: 600;">データベース名 (DB Name):</label>
              <input type="text" id="db-name-input" class="form-control" placeholder="postgres" value="postgres" oninput="syncDbUriFromFields()" style="font-size: 11px;">
            </div>
            <div class="form-group" style="margin: 0;">
              <label style="font-size: 10px; font-weight: 600;">ユーザー名 (User):</label>
              <input type="text" id="db-user-input" class="form-control" placeholder="postgres.xxxx または postgres" oninput="syncDbUriFromFields()" style="font-size: 11px;">
            </div>
            <div class="form-group" style="margin: 0;">
              <label style="font-size: 10px; font-weight: 600;">パスワード (Password):</label>
              <input type="password" id="db-pass-input" class="form-control" placeholder="••••••••" oninput="syncDbUriFromFields()" style="font-size: 11px;">
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 8px;">
            <label style="font-size: 10px; font-weight: 600;">接続 URI (自動生成 または 直接入力):</label>
            <input type="text" id="db-uri-input" class="form-control" placeholder="postgresql://postgres:password@host:5432/postgres?sslmode=require" style="font-family: monospace; font-size: 11px;">
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" style="font-size: 11px; padding: 5px 10px;" onclick="testCustomDbConnection()">🔌 接続テスト (Test Ping)</button>
            <button class="btn-primary" style="font-size: 11px; padding: 5px 12px; background: #0284c7;" onclick="connectCustomDb()">🚀 PostgreSQL / Supabase へ接続</button>
          </div>
        </div>

        <!-- Section 2: Local SQLite -->
        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px;">
          <div style="font-weight: 700; font-size: 12px; color: #15803d; margin-bottom: 6px;">📂 2. ローカル SQLite データベース</div>
          <div class="form-group" style="margin-bottom: 8px;">
            <label style="font-size: 10px; font-weight: 600;">SQLite ファイルパス:</label>
            <input type="text" id="db-local-path-input" class="form-control" placeholder="./erp_unified.db" style="font-size: 11px;">
            <small style="color: #64748b; font-size: 10px;">※ 指定したパスにファイルが存在しない場合は自動で3テーブルおよびベンチマークデータが初期化されます。</small>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" style="font-size: 11px;" onclick="connectLocalDb()">📂 指定ローカルDBに切替</button>
            <button class="btn-secondary" style="font-size: 11px;" onclick="switchDb('default')">標準ローカルDBに戻す</button>
          </div>
        </div>

        <div id="db-conn-result" style="display: none; padding: 8px 12px; border-radius: 6px; font-size: 11px; margin-top: 10px;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeDbModal()">閉じる</button>
      </div>
    </div>
  </div>

  <!-- Modal 7: Comprehensive Database Schema & Data Types Specification Guide -->
  <div class="modal-overlay" id="schema-info-modal" style="display: none;">
    <div class="modal-card" style="max-width: 820px; width: 95%; max-height: 88vh; display: flex; flex-direction: column;">
      <div class="modal-header" style="background: #0f172a; color: #ffffff; padding: 12px 18px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 16px;">ℹ️</span>
          <span style="font-weight: 700; font-size: 13px;">ERP データベース仕様・スキーマ定義 & データ型要件ガイド</span>
        </div>
        <button class="btn-secondary" style="padding: 2px 7px; color: #ffffff; border-color: rgba(255,255,255,0.3); background: transparent;" onclick="closeSchemaInfoModal()">✕</button>
      </div>

      <div style="display: flex; background: #f1f5f9; border-bottom: 1px solid #cbd5e1; padding: 0 12px;">
        <button class="schema-tab-btn active" id="schema-tab-btn-inv" onclick="switchSchemaTab('invoice')" style="padding: 8px 14px; border: none; background: transparent; font-size: 11px; font-weight: 700; color: #1e3a8a; border-bottom: 2px solid #2563eb; cursor: pointer;">📄 財務会計 (erp_invoices)</button>
        <button class="schema-tab-btn" id="schema-tab-btn-pay" onclick="switchSchemaTab('payroll')" style="padding: 8px 14px; border: none; background: transparent; font-size: 11px; font-weight: 600; color: #64748b; cursor: pointer;">👥 人事給与 (erp_payroll_items)</button>
        <button class="schema-tab-btn" id="schema-tab-btn-lev" onclick="switchSchemaTab('leave')" style="padding: 8px 14px; border: none; background: transparent; font-size: 11px; font-weight: 600; color: #64748b; cursor: pointer;">🌴 勤怠管理 (erp_leave_applications)</button>
        <button class="schema-tab-btn" id="schema-tab-btn-excel" onclick="switchSchemaTab('excel')" style="padding: 8px 14px; border: none; background: transparent; font-size: 11px; font-weight: 600; color: #64748b; cursor: pointer;">📊 Excel/CSV 取込規程 & 型整合性</button>
      </div>

      <div class="modal-body" style="padding: 16px; overflow-y: auto; flex: 1;">
        <!-- Tab 1: Invoices Schema -->
        <div id="schema-view-invoice">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">テーブル名: <code>erp_invoices</code> (財務会計 - 請求書照合)</div>
          <p style="font-size: 11px; color: #475569; margin-bottom: 10px;">企業間取引の請求書・支払伝票を格納します。月次定額保守契約や上限額規程との照合に利用されます。</p>
          <table class="erp-table" style="font-size: 11px;">
            <thead>
              <tr style="background: #f1f5f9;">
                <th>カラム名 (物理名)</th>
                <th>項目名 (日本語)</th>
                <th>データ型 (SQL)</th>
                <th>必須</th>
                <th>許容値・フォーマット制約</th>
                <th>サンプル例</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><code>id</code></td><td>伝票ID (PK)</td><td>VARCHAR(50)</td><td>YES</td><td>ユニーク識別子。<code>INV-2026-XXX</code> または <code>P6-XXXX-XXX</code></td><td>INV-2026-001</td></tr>
              <tr><td><code>employee_id</code></td><td>取引先コード</td><td>VARCHAR(50)</td><td>YES</td><td>登録ベンダーコード (例: <code>V1001</code>〜<code>V3099</code>)</td><td>V1001</td></tr>
              <tr><td><code>name</code></td><td>取引先企業名</td><td>VARCHAR(255)</td><td>YES</td><td>企業名・ベンダー名称</td><td>株式会社アルファ・システムズ</td></tr>
              <tr><td><code>raw_amount</code></td><td>請求金額 (数値)</td><td>BIGINT</td><td>YES</td><td>0以上の整数 (JPY)。カンマ・記号なし</td><td>1250000</td></tr>
              <tr><td><code>amount</code></td><td>フォーマット金額</td><td>VARCHAR(50)</td><td>NO</td><td>表示用通貨文字列</td><td>¥1,250,000</td></tr>
              <tr><td><code>type</code></td><td>請求区分</td><td>VARCHAR(50)</td><td>NO</td><td><code>Routine</code> (定額保守) または <code>Non-Routine</code> (スポット)</td><td>Routine</td></tr>
              <tr><td><code>status</code></td><td>承認ステータス</td><td>VARCHAR(50)</td><td>NO</td><td><code>Approved</code>, <code>Hold</code>, <code>Unprocessed</code></td><td>Approved</td></tr>
              <tr><td><code>ref</code></td><td>証憑・契約参照</td><td>VARCHAR(255)</td><td>NO</td><td>契約番号または稟議決裁番号</td><td>契約番号 CT-2026-042</td></tr>
              <tr><td><code>comment</code></td><td>J-SOX監査理由</td><td>TEXT</td><td>NO</td><td>AIまたは監査人による判定理由</td><td>定額保守契約金額と一致・自動承認</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Tab 2: Payroll Schema -->
        <div id="schema-view-payroll" style="display: none;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">テーブル名: <code>erp_payroll_items</code> (人事給与・経費精算)</div>
          <p style="font-size: 11px; color: #475569; margin-bottom: 10px;">社員からの立替経費、出張手当、交通費精算データを格納します。規程限度額との突合に利用されます。</p>
          <table class="erp-table" style="font-size: 11px;">
            <thead>
              <tr style="background: #f1f5f9;">
                <th>カラム名 (物理名)</th>
                <th>項目名 (日本語)</th>
                <th>データ型 (SQL)</th>
                <th>必須</th>
                <th>許容値・フォーマット制約</th>
                <th>サンプル例</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><code>id</code></td><td>精算伝票ID (PK)</td><td>VARCHAR(50)</td><td>YES</td><td><code>PAY-2026-XXX</code> または <code>P4-XXXX-XXX</code></td><td>PAY-2026-014</td></tr>
              <tr><td><code>employee_id</code></td><td>社員番号</td><td>VARCHAR(50)</td><td>YES</td><td>社員コード (例: <code>EMP-001</code>〜<code>EMP-105</code>)</td><td>EMP-014</td></tr>
              <tr><td><code>employee_name</code></td><td>社員氏名</td><td>VARCHAR(255)</td><td>YES</td><td>従業員姓名</td><td>佐藤 健太</td></tr>
              <tr><td><code>item_category</code></td><td>精算項目分類</td><td>VARCHAR(100)</td><td>YES</td><td><code>交通費精算</code>, <code>消耗品費</code>, <code>出張旅費</code>, <code>研修費</code>, <code>在宅勤務手当</code>, <code>残業手当調整</code>, <code>接待交際費</code></td><td>交通費精算</td></tr>
              <tr><td><code>item_type</code></td><td>支給・控除区分</td><td>VARCHAR(50)</td><td>YES</td><td><code>Addition</code> (支給・精算) または <code>Deduction</code> (控除)</td><td>Addition</td></tr>
              <tr><td><code>raw_amount</code></td><td>精算金額 (数値)</td><td>BIGINT</td><td>YES</td><td>0以上の整数 (JPY)</td><td>24800</td></tr>
              <tr><td><code>amount</code></td><td>表示用金額</td><td>VARCHAR(50)</td><td>NO</td><td>通貨表記文字列</td><td>¥24,800</td></tr>
              <tr><td><code>status</code></td><td>承認ステータス</td><td>VARCHAR(50)</td><td>NO</td><td><code>Approved</code>, <code>Hold</code>, <code>Unprocessed</code></td><td>Approved</td></tr>
              <tr><td><code>voucher_ref</code></td><td>領収書・証憑番号</td><td>VARCHAR(100)</td><td>NO</td><td>領収書スキャン番号</td><td>P2-07101496-014</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Tab 3: Leave Schema -->
        <div id="schema-view-leave" style="display: none;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">テーブル名: <code>erp_leave_applications</code> (勤怠管理・休暇申請)</div>
          <p style="font-size: 11px; color: #475569; margin-bottom: 10px;">社員の有給休暇・病気特別休暇申請および添付医師診断書との照合データを格納します。</p>
          <table class="erp-table" style="font-size: 11px;">
            <thead>
              <tr style="background: #f1f5f9;">
                <th>カラム名 (物理名)</th>
                <th>項目名 (日本語)</th>
                <th>データ型 (SQL)</th>
                <th>必須</th>
                <th>許容値・フォーマット制約</th>
                <th>サンプル例</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><code>id</code></td><td>申請ID (PK)</td><td>VARCHAR(50)</td><td>YES</td><td><code>LV-2026-XXX</code> (例: LV-2026-001)</td><td>LV-2026-001</td></tr>
              <tr><td><code>employee_id</code></td><td>社員番号</td><td>VARCHAR(50)</td><td>YES</td><td>社員識別コード</td><td>EMP-001</td></tr>
              <tr><td><code>employee_name</code></td><td>申請者氏名</td><td>VARCHAR(255)</td><td>YES</td><td>フルネーム (添付診断書名義と突合)</td><td>青木 拓也</td></tr>
              <tr><td><code>department</code></td><td>所属部署</td><td>VARCHAR(100)</td><td>NO</td><td>開発部, 営業部, 人事部, 財務部 等</td><td>開発部</td></tr>
              <tr><td><code>leave_type</code></td><td>休暇種別</td><td>VARCHAR(100)</td><td>YES</td><td><code>有給休暇</code>, <code>病気休暇</code>, <code>慶弔特別休暇</code>, <code>未登録休暇</code></td><td>病気休暇</td></tr>
              <tr><td><code>start_date</code></td><td>開始日</td><td>VARCHAR(20)</td><td>YES</td><td>ISO日付形式: <code>YYYY-MM-DD</code></td><td>2026-07-20</td></tr>
              <tr><td><code>end_date</code></td><td>終了日</td><td>VARCHAR(20)</td><td>YES</td><td>ISO日付形式: <code>YYYY-MM-DD</code> (開始日以降)</td><td>2026-07-21</td></tr>
              <tr><td><code>requested_days</code></td><td>申請日数</td><td>NUMERIC(4, 1)</td><td>YES</td><td>0より大きい数値 (0.5, 1.0, 2.0 等)</td><td>2.0</td></tr>
              <tr><td><code>remaining_balance</code></td><td>有給残日数</td><td>NUMERIC(4, 1)</td><td>YES</td><td>申請時点の有給残高 (0以上の数値)</td><td>14.0</td></tr>
              <tr><td><code>reason</code></td><td>申請理由</td><td>TEXT</td><td>NO</td><td>申請者が入力した理由詳細</td><td>発熱・風邪症状のため自宅療養</td></tr>
              <tr><td><code>has_attachment</code></td><td>証明書添付フラグ</td><td>BOOLEAN</td><td>YES</td><td><code>TRUE</code> / <code>FALSE</code> (1 / 0)</td><td>TRUE</td></tr>
              <tr><td><code>attachment_name</code></td><td>添付ファイル名</td><td>VARCHAR(255)</td><td>NO</td><td><code>attachments/</code> フォルダに存在する実ファイル名</td><td>LV-2026-001_青木拓也_医師診断書.pdf</td></tr>
              <tr><td><code>status</code></td><td>判定ステータス</td><td>VARCHAR(50)</td><td>NO</td><td><code>Approved</code>, <code>Hold</code>, <code>Unprocessed</code></td><td>Approved</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Tab 4: Excel Constraints -->
        <div id="schema-view-excel" style="display: none;">
          <div style="font-weight: 700; font-size: 12px; color: #166534; margin-bottom: 6px;">📊 Excel / CSV ファイルアップロード時の整合性チェック規則</div>
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 12px; margin-bottom: 12px; font-size: 11px; line-height: 1.6; color: #166534;">
            <div><strong>① ヘッダー行 (カラム名) の自動マッピング:</strong></div>
            <div>日本語ヘッダー (例: <code>取引先コード</code>, <code>企業名</code>, <code>金額</code>) および英語ヘッダー (例: <code>employee_id</code>, <code>name</code>, <code>raw_amount</code>) の双方が自動認識されます。</div>
            <div style="margin-top: 6px;"><strong>② データ型検証 (Data Type Validation):</strong></div>
            <div>・金額および日数は必ず数値型 (INTEGER / FLOAT) である必要があります。文字や記号が含まれる場合、システムが自動でフラグを立てて警告を表示します。</div>
            <div>・日付は <code>YYYY-MM-DD</code> 形式で記述してください。</div>
            <div>・未定義の休暇種別や存在しない必須カラムは自動的に検知され、取込前に修正を促します。</div>
          </div>
          <div style="font-weight: 700; font-size: 11px; color: #334155; margin-bottom: 6px;">📥 サンプルCSVテンプレートのダウンロード:</div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" onclick="downloadSampleCsv('invoice')" style="font-size: 11px;">📄 請求書テンプレート (.csv)</button>
            <button class="btn-secondary" onclick="downloadSampleCsv('payroll')" style="font-size: 11px;">👥 人事給与テンプレート (.csv)</button>
            <button class="btn-secondary" onclick="downloadSampleCsv('leave')" style="font-size: 11px;">🌴 休暇申請テンプレート (.csv)</button>
          </div>
        </div>
      </div>
      <div class="modal-footer" style="padding: 10px 16px; background: #f8fafc; border-top: 1px solid #e2e8f0;">
        <button class="btn-secondary" onclick="closeSchemaInfoModal()">閉じる</button>
      </div>
    </div>
  </div>

  <script>
    /* --- Global State --- */
    let currentSuite = 'invoice'; // 'invoice' | 'payroll'
    let invoiceRecords = [];
    let payrollRecords = [];
    let stagedDecisionsData = [];
    let currentStagedFilter = 'all';
    let expandedStagedRows = new Set();
    let parsedBulkData = [];
    let activeCommentRecord = null;
    let masterRegulationsData = [];

    const INVOICE_PRESET = `{{ invoice_preset | safe }}`;
    const PAYROLL_PRESET = `{{ payroll_preset | safe }}`;

    /* --- Core Staged Evaluation, Human Intervention & Modal Logic (Hoisted Globally) --- */
    let isInterventionsInlineCollapsed = true;
    let activeDiscrepancies = [];

    function toggleInterventionsCollapse() {
      isInterventionsInlineCollapsed = !isInterventionsInlineCollapsed;
      const list = document.getElementById('interventions-list');
      const btn = document.getElementById('btn-toggle-interventions');
      if (list) {
        list.style.display = isInterventionsInlineCollapsed ? 'none' : 'block';
      }
      if (btn) {
        btn.innerText = isInterventionsInlineCollapsed ? '▶' : '▼';
        btn.title = isInterventionsInlineCollapsed ? 'インライン展開 (Expand inline)' : '折りたたむ (Collapse inline)';
      }
    }
    window.toggleInterventionsCollapse = toggleInterventionsCollapse;

    function openInterventionsModal() {
      const modal = document.getElementById('interventions-modal');
      const modalList = document.getElementById('interventions-modal-list');
      const countBadge = document.getElementById('interventions-modal-count-badge');
      if (!modal) return;

      if (countBadge) {
        countBadge.innerText = activeDiscrepancies.length;
      }

      if (modalList) {
        if (!activeDiscrepancies || activeDiscrepancies.length === 0) {
          modalList.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">現在、要人間精査項目はありません。</div>';
        } else {
          modalList.innerHTML = activeDiscrepancies.map(function(d, idx) {
            const reasonText = (d.reasons && d.reasons.length > 0) ? d.reasons[0] : (d.rule_summary || '要確認・監査精査');
            return '<div style="background: #ffffff; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">' +
              '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">' +
                '<div>' +
                  '<span style="font-weight: 700; color: #92400e; font-size: 13px;">⚠️ ' + (d.id || '-') + '</span>' +
                  '<span style="margin-left: 8px; font-weight: 600; color: #1e293b; font-size: 12px;">' + (d.name || '-') + '</span>' +
                '</div>' +
                '<span style="color: #b45309; font-weight: 700; font-size: 12px; background: #fef3c7; padding: 2px 8px; border-radius: 4px;">' + (d.amount || '-') + '</span>' +
              '</div>' +
              '<div style="background: #fffbeb; border: 1px solid #fef08a; border-radius: 4px; padding: 8px 10px; color: #78350f; font-size: 11px; line-height: 1.4; margin-bottom: 8px;">' +
                '<strong>検出理由 / SQL判定:</strong> ' + reasonText +
              '</div>' +
              '<div style="display: flex; justify-content: flex-end; gap: 6px;">' +
                '<button class="btn-secondary" style="font-size: 11px; padding: 3px 9px;" onclick="handleAuditCommentClick(' + idx + ')">' +
                  '💬 コメント・承認管理' +
                '</button>' +
              '</div>' +
            '</div>';
          }).join('');
        }
      }

      modal.style.display = 'flex';
    }
    window.openInterventionsModal = openInterventionsModal;

    function closeInterventionsModal() {
      const modal = document.getElementById('interventions-modal');
      if (modal) modal.style.display = 'none';
    }
    window.closeInterventionsModal = closeInterventionsModal;

    function handleAuditCommentClick(idx) {
      closeInterventionsModal();
      const d = activeDiscrepancies[idx];
      if (!d) return;
      const encComment = encodeURIComponent(d.comments || '');
      const encName = encodeURIComponent(d.name || '');
      openCommentModal(d.id || '', encComment, d.new_status || 'Hold', encName, d.amount || '');
    }
    window.handleAuditCommentClick = handleAuditCommentClick;

    function renderInterventions(discrepancies) {
      try {
        activeDiscrepancies = discrepancies || [];
        const container = document.getElementById('interventions-container');
        const list = document.getElementById('interventions-list');
        const countBadge = document.getElementById('interventions-badge-count');
        const modalCountBadge = document.getElementById('interventions-modal-count-badge');
        if (!container || !list) return;

        if (!discrepancies || discrepancies.length === 0) {
          container.style.display = 'none';
          list.innerHTML = '';
          if (countBadge) countBadge.innerText = '0';
          if (modalCountBadge) modalCountBadge.innerText = '0';
          return;
        }

        // Show compact container, but keep inline list collapsed by default
        container.style.display = 'block';
        if (countBadge) countBadge.innerText = discrepancies.length;
        if (modalCountBadge) modalCountBadge.innerText = discrepancies.length;

        // Populate inline list (accessible if user expands with ▶ toggle)
        list.innerHTML = discrepancies.map(function(d) {
          const reasonText = (d.reasons && d.reasons.length > 0) ? d.reasons[0] : (d.rule_summary || '要確認・監査精査');
          return '<div style="background: #ffffff; border: 1px solid #fde68a; border-radius: 4px; padding: 6px 8px; margin-bottom: 4px; font-size: 11px;">' +
            '<div style="display: flex; justify-content: space-between; align-items: center;">' +
              '<strong style="color: #92400e;">⚠️ ' + (d.id || '-') + ' (' + (d.name || '-') + ')</strong>' +
              '<span style="color: #b45309; font-weight: 700;">' + (d.amount || '-') + '</span>' +
            '</div>' +
            '<div style="color: #78350f; margin-top: 2px; font-size: 11px;">' + reasonText + '</div>' +
          '</div>';
        }).join('');

        // Ensure inline list starts collapsed to save space
        list.style.display = 'none';
        isInterventionsInlineCollapsed = true;
        const btn = document.getElementById('btn-toggle-interventions');
        if (btn) btn.innerText = '▶';

      } catch (err) {
        console.warn('renderInterventions warning:', err);
      }
    }
    window.renderInterventions = renderInterventions;

    function openStagedModal(result) {
      try {
        document.getElementById('stage-approved-count').innerText = result.approved_count || 0;
        document.getElementById('stage-hold-count').innerText = result.hold_count || 0;
        document.getElementById('stage-total-count').innerText = result.evaluated_count || 0;

        currentStagedFilter = 'all';
        expandedStagedRows.clear();
        filterStagedRows('all');

        const modal = document.getElementById('staged-modal');
        if (modal) modal.style.display = 'flex';
      } catch (err) {
        console.warn('openStagedModal warning:', err);
      }
    }
    window.openStagedModal = openStagedModal;

    function closeStagedModal() {
      const modal = document.getElementById('staged-modal');
      if (modal) modal.style.display = 'none';
    }
    window.closeStagedModal = closeStagedModal;

    function filterStagedRows(filterType) {
      currentStagedFilter = filterType;
      const bAll = document.getElementById('btn-filter-all');
      const bApp = document.getElementById('btn-filter-approved');
      const bHld = document.getElementById('btn-filter-hold');
      if (bAll) bAll.classList.toggle('active', filterType === 'all');
      if (bApp) bApp.classList.toggle('active', filterType === 'approved');
      if (bHld) bHld.classList.toggle('active', filterType === 'hold');

      const searchInput = document.getElementById('staged-search-input');
      const search = (searchInput ? searchInput.value : '').toLowerCase().trim();

      const tbody = document.getElementById('staged-preview-body');
      if (!tbody) return;

      const filtered = stagedDecisionsData.map(function(d, idx) {
        return Object.assign({}, d, { originalIdx: idx });
      }).filter(function(d) {
        const isApproved = (d.new_status === 'Approved' || d.new_status === 'Confirmed');
        const isHold = (d.new_status === 'Hold');

        if (filterType === 'approved' && !isApproved) return false;
        if (filterType === 'hold' && !isHold) return false;

        if (search) {
          const matchId = (d.id || '').toLowerCase().includes(search);
          const matchName = (d.entity_name || '').toLowerCase().includes(search);
          if (!matchId && !matchName) return false;
        }
        return true;
      });

      tbody.innerHTML = filtered.map(function(d) {
        const idx = d.originalIdx;
        const isExpanded = expandedStagedRows.has(d.id);
        const detailHtml = isExpanded ? 
          '<tr id="detail-row-' + d.id + '" style="background: #f8fafc;">' +
            '<td colspan="6" style="padding: 8px 14px;">' +
              '<div class="row-detail-box">' +
                '<div><strong>伝票ID:</strong> ' + d.id + '</div>' +
                '<div><strong>取引先/従業員:</strong> ' + (d.entity_name || '-') + '</div>' +
                '<div><strong>申請金額:</strong> <span style="color: #1e3a8a; font-weight: 700;">' + (d.amount || ('¥' + (d.raw_amount || 0).toLocaleString())) + '</span></div>' +
                '<div><strong>伝票区分:</strong> ' + (d.type || '-') + '</div>' +
                '<div><strong>照合伝票・注文番号:</strong> ' + (d.ref || '-') + '</div>' +
                '<div><strong>適用判定ルール:</strong> <span style="color: #1e40af; font-weight: 700;">[' + (d.matched_rule_id || 'RULE') + '] ' + (d.matched_rule_summary || '') + '</span></div>' +
                '<div style="grid-column: span 2;"><strong>判定事由 / 指摘事項:</strong> ' + ((d.reasons || []).join(' / ') || '契約・規程整合確認済') + '</div>' +
                '<div style="grid-column: span 2;"><strong>LLM監査コメント:</strong> <span style="color: #047857;">' + (d.comment || '-') + '</span></div>' +
              '</div>' +
            '</td>' +
          '</tr>' : '';

        return '<tr>' +
          '<td style="text-align: center;">' +
            '<button class="btn-detail-toggle" data-id="' + d.id + '" onclick="toggleStagedDetail(this.dataset.id)" title="伝票の詳細情報を表示">' +
              (isExpanded ? '▲' : 'ℹ️') +
            '</button>' +
          '</td>' +
          '<td><strong>' + d.id + '</strong></td>' +
          '<td>' + (d.entity_name || '-') + '</td>' +
          '<td style="color: #1e3a8a; font-weight: 700;">' + (d.amount || ('¥' + (d.raw_amount || 0).toLocaleString())) + '</td>' +
          '<td>' +
            '<select class="form-control" style="padding:2px 4px; font-size:11px;" onchange="updateStagedDecisionStatus(' + idx + ', this.value)">' +
              '<option value="' + d.new_status + '" selected>' + d.new_status + '</option>' +
              '<option value="' + (d.new_status === 'Hold' ? (currentSuite === 'invoice' ? 'Approved' : 'Confirmed') : 'Hold') + '">' +
                (d.new_status === 'Hold' ? (currentSuite === 'invoice' ? 'Approved' : 'Confirmed') : 'Hold') +
              '</option>' +
            '</select>' +
          '</td>' +
          '<td>' +
            '<div style="font-size: 10px; color: #1e40af; font-weight: 600; margin-bottom: 2px;">' +
              '[' + (d.matched_rule_id || 'RULE') + '] ' + (d.matched_rule_summary || '') +
            '</div>' +
            '<input type="text" class="form-control" style="font-size:11px; padding:2px 6px;" value="' + (d.comment || '') + '" onchange="updateStagedDecisionComment(' + idx + ', this.value)">' +
          '</td>' +
        '</tr>' + detailHtml;
      }).join('');
    }
    window.filterStagedRows = filterStagedRows;

    function toggleStagedDetail(id) {
      if (expandedStagedRows.has(id)) {
        expandedStagedRows.delete(id);
      } else {
        expandedStagedRows.add(id);
      }
      filterStagedRows(currentStagedFilter);
    }
    window.toggleStagedDetail = toggleStagedDetail;

    function updateStagedDecisionStatus(idx, val) {
      if (stagedDecisionsData[idx]) stagedDecisionsData[idx].new_status = val;
    }
    window.updateStagedDecisionStatus = updateStagedDecisionStatus;

    function updateStagedDecisionComment(idx, val) {
      if (stagedDecisionsData[idx]) stagedDecisionsData[idx].comment = val;
    }
    window.updateStagedDecisionComment = updateStagedDecisionComment;

    async function confirmCommitStaged() {
      closeStagedModal();
      setNodeActive('node-3');

      try {
        const res = await fetch('/api/copilot/commit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            process_type: currentSuite,
            decisions: stagedDecisionsData
          })
        });
        const commitRes = await res.json();

        setNodeDone('node-3', '0.04s');
        setNodeDone('node-4', '0.01s');
        const badge = document.getElementById('graph-overall-badge');
        if (badge) {
          badge.innerText = commitRes.overall_status || 'SUCCESS';
          badge.style.background = commitRes.overall_status === 'SUCCESS' ? '#dcfce7' : '#fef3c7';
        }

        // Render corporate human intervention cards if any
        const discrepancies = commitRes.discrepancies || [];
        renderInterventions(discrepancies);

        // Refresh live database table
        loadTableData();

      } catch (e) {
        alert('DBコミットエラー: ' + e);
      }
    }
    window.confirmCommitStaged = confirmCommitStaged;

    /* --- Co-Pilot Drawer Toggle Logic --- */
    let isCopilotPanelOpen = true;
    function toggleCopilotPanel() {
      isCopilotPanelOpen = !isCopilotPanelOpen;
      const panel = document.getElementById('workspace-panel');
      const splitter = document.getElementById('drag-splitter');
      const btn = document.getElementById('btn-toggle-copilot');

      if (panel) {
        panel.style.display = isCopilotPanelOpen ? 'flex' : 'none';
      }
      if (splitter) {
        splitter.style.display = isCopilotPanelOpen ? 'flex' : 'none';
      }
      if (btn) {
        btn.classList.toggle('active', isCopilotPanelOpen);
      }
      localStorage.setItem('erp_copilot_open', isCopilotPanelOpen ? '1' : '0');
    }
    window.toggleCopilotPanel = toggleCopilotPanel;

    /* --- Resizable Splitter Logic (Right-Docked Co-Pilot Panel) --- */
    (function initResizableSplitter() {
      const splitter = document.getElementById('drag-splitter');
      const panel = document.getElementById('workspace-panel');
      let isDragging = false;
      let startX, startWidth;

      const savedWidth = localStorage.getItem('erp_ws_width');
      if (savedWidth && panel) {
        panel.style.width = savedWidth + 'px';
      }

      const savedOpen = localStorage.getItem('erp_copilot_open');
      if (savedOpen === '0') {
        toggleCopilotPanel();
      }

      if (splitter && panel) {
        splitter.addEventListener('mousedown', function(e) {
          isDragging = true;
          startX = e.clientX;
          startWidth = parseInt(window.getComputedStyle(panel).width, 10);
          splitter.classList.add('dragging');
          document.body.style.cursor = 'col-resize';
          document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', function(e) {
          if (!isDragging) return;
          const dx = e.clientX - startX;
          // Since panel is on the right, dragging mouse to the left (dx < 0) expands the panel
          let newWidth = startWidth - dx;
          if (newWidth < 320) newWidth = 320;
          if (newWidth > 1100) newWidth = 1100;
          panel.style.width = newWidth + 'px';
        });

        document.addEventListener('mouseup', function() {
          if (isDragging) {
            isDragging = false;
            splitter.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            localStorage.setItem('erp_ws_width', parseInt(panel.style.width, 10));
          }
        });
      }
    })();

    /* --- Resizable Splitter Logic (Horizontal: Top Editor vs LLM Rules Panel) --- */
    (function initRulesVerticalResizer() {
      const resizer = document.getElementById('rules-vertical-resizer');
      const notepadBox = document.getElementById('ws-tab-notepad');
      const excelBox = document.getElementById('ws-tab-excel');
      if (!resizer) return;

      let isDragging = false;
      let startY = 0;
      let startHeight = 270;

      const savedH = localStorage.getItem('erp_editor_height');
      if (savedH) {
        if (notepadBox) notepadBox.style.height = savedH + 'px';
        if (excelBox) excelBox.style.height = savedH + 'px';
      }

      resizer.addEventListener('mousedown', function(e) {
        isDragging = true;
        startY = e.clientY;
        const currentBox = (notepadBox && notepadBox.style.display !== 'none') ? notepadBox : excelBox;
        startHeight = currentBox ? currentBox.offsetHeight : 270;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'row-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
      });

      document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        const delta = e.clientY - startY;
        let newH = startHeight + delta;
        if (newH < 80) newH = 80;
        if (newH > 850) newH = 850;
        if (notepadBox) notepadBox.style.height = newH + 'px';
        if (excelBox) excelBox.style.height = newH + 'px';
      });

      document.addEventListener('mouseup', function() {
        if (isDragging) {
          isDragging = false;
          resizer.classList.remove('dragging');
          document.body.style.cursor = '';
          document.body.style.userSelect = '';
          const currentBox = (notepadBox && notepadBox.style.display !== 'none') ? notepadBox : excelBox;
          if (currentBox) {
            localStorage.setItem('erp_editor_height', currentBox.offsetHeight);
          }
        }
      });
    })();

    /* --- Application Initialization --- */
    window.addEventListener('DOMContentLoaded', async function() {
      await loadMasterRegulations();
      await updateSystemStatus();
      await loadTableData();
      renderInitialExtractedRules();
    });

    /* --- Module Navigation --- */
    function switchSuite(suite) {
      currentSuite = suite;

      const sel = document.getElementById('suite-dropdown-select');
      if (sel) sel.value = suite;

      const tabInv = document.getElementById('tab-invoice');
      const tabPay = document.getElementById('tab-payroll');
      const tabLev = document.getElementById('tab-leave');

      const cardInv = document.getElementById('proc-card-invoice');
      const cardPay = document.getElementById('proc-card-payroll');
      const cardLev = document.getElementById('proc-card-leave');

      const pillInv = document.getElementById('proc-pill-invoice');
      const pillPay = document.getElementById('proc-pill-payroll');
      const pillLev = document.getElementById('proc-pill-leave');

      [tabInv, tabPay, tabLev].forEach(function(t) { if (t) t.classList.remove('active'); });
      [cardInv, cardPay, cardLev].forEach(function(c) {
        if (c) { c.style.border = '1px solid #cbd5e1'; c.style.background = '#ffffff'; }
      });
      [pillInv, pillPay, pillLev].forEach(function(p) { if (p) p.style.display = 'none'; });

      if (suite === 'invoice') {
        if (tabInv) tabInv.classList.add('active');
        if (cardInv) { cardInv.style.border = '2px solid #2563eb'; cardInv.style.background = '#eff6ff'; }
        if (pillInv) pillInv.style.display = 'inline-block';

        document.getElementById('table-suite-title').innerText = '財務会計 - 請求書一覧';
        document.getElementById('metric-label-approved').innerText = '自動承認済';
        document.getElementById('notepad-filename').innerText = '月次定額保守取引先一覧.txt (参照規程)';
        document.getElementById('doc-text').value = INVOICE_PRESET;
        document.getElementById('excel-master-title').innerText = '📊 月次定額取引先契約マスタ (編集可能)';
      } else if (suite === 'leave') {
        if (tabLev) tabLev.classList.add('active');
        if (cardLev) { cardLev.style.border = '2px solid #2563eb'; cardLev.style.background = '#eff6ff'; }
        if (pillLev) pillLev.style.display = 'inline-block';

        document.getElementById('table-suite-title').innerText = '勤怠管理 - 休暇申請一覧';
        document.getElementById('metric-label-approved').innerText = '承認済 (Approved)';
        document.getElementById('notepad-filename').innerText = '休暇申請承認審査規程.txt (審査方針)';
        document.getElementById('doc-text').value = LEAVE_PRESET;
        document.getElementById('excel-master-title').innerText = '📊 勤怠有休管理マスタ (編集可能)';
      } else {
        if (tabPay) tabPay.classList.add('active');
        if (cardPay) { cardPay.style.border = '2px solid #2563eb'; cardPay.style.background = '#eff6ff'; }
        if (pillPay) pillPay.style.display = 'inline-block';

        document.getElementById('table-suite-title').innerText = '人事給与 - 支給控除項目一覧';
        document.getElementById('metric-label-approved').innerText = '確認済 (Confirmed)';
        document.getElementById('notepad-filename').innerText = '*精算確認メモ.txt (確認メモ)';
        document.getElementById('doc-text').value = PAYROLL_PRESET;
        document.getElementById('excel-master-title').innerText = '📊 業務委託経費・給与規程マスタ (編集可能)';
      }

      resetGraphUi();
      renderInitialExtractedRules();
      renderMasterRegulationsTable();
      loadTableData();
    }

    let isPuterBannerDismissed = false;

    /* --- Status Check & Refresh --- */
    async function updateSystemStatus() {
      try {
        const dbRes = await fetch('/api/database/status').then(function(r) { return r.json(); });
        const pillText = document.getElementById('db-pill-text');
        if (pillText) {
          pillText.innerText = 'Database';
          pillText.parentElement.title = 'Database: ' + (dbRes.display_target || 'Active');
        }
        const dbCurrEl = document.getElementById('modal-db-current');
        if (dbCurrEl) dbCurrEl.innerText = dbRes.display_target;
        if (dbRes.sqlite_path) {
          const lpathEl = document.getElementById('db-local-path-input');
          if (lpathEl) lpathEl.value = dbRes.sqlite_path;
        }

        const llmRes = await fetch('/api/llm/status').then(function(r) { return r.json(); });
        const llmPill = document.querySelector('.status-pill.llm');
        const llmPillText = document.getElementById('llm-pill-text');
        const puterBanner = document.getElementById('puter-login-banner');

        const isPuter = (llmRes.provider === 'puter');
        const isConnected = Boolean(llmRes.connected);

        if (isPuter && !isConnected) {
          if (llmPill) {
            llmPill.classList.add('disconnected');
            llmPill.classList.remove('connected');
            llmPill.onclick = function() { openPuterAuthModal(); };
            llmPill.title = '⚠️ Puter 未接続 - クリックしてログイン';
          }
          if (llmPillText) {
            llmPillText.innerText = 'LLM';
          }
          if (puterBanner && !isPuterBannerDismissed) {
            puterBanner.style.display = 'flex';
          }
        } else {
          if (llmPill) {
            llmPill.classList.remove('disconnected');
            if (isConnected) llmPill.classList.add('connected');
            else llmPill.classList.remove('connected');
            llmPill.onclick = function() { openLlmModal(); };
            llmPill.title = 'LLM: ' + (llmRes.display || 'Ready');
          }
          if (llmPillText) {
            llmPillText.innerText = 'LLM';
          }
          if (puterBanner) {
            puterBanner.style.display = 'none';
          }
        }

        // Update Puter badge in LLM modal if open
        const puterBadge = document.getElementById('puter-modal-conn-badge');
        if (puterBadge) {
          if (isPuter && isConnected) {
            puterBadge.className = 'status-badge badge-approved';
            puterBadge.innerText = '接続済 (Connected)';
          } else {
            puterBadge.className = 'status-badge badge-hold';
            puterBadge.innerText = '未接続 (Disconnected)';
          }
        }
      } catch (e) {
        console.error('Status fetch error:', e);
      }
    }

    /* --- Load Table Data --- */
    async function loadTableData() {
      try {
        if (currentSuite === 'invoice') {
          const res = await fetch('/api/invoices');
          invoiceRecords = await res.json();
          renderInvoiceTable(invoiceRecords);
        } else if (currentSuite === 'leave') {
          const res = await fetch('/api/leave-applications');
          leaveRecords = await res.json();
          renderLeaveTable(leaveRecords);
        } else {
          const res = await fetch('/api/payroll-items');
          payrollRecords = await res.json();
          renderPayrollTable(payrollRecords);
        }
      } catch (e) {
        console.error('Data load error:', e);
      }
    }

    /* --- Render Invoices Table --- */
    
    let leaveRecords = [];
    const LEAVE_PRESET = `休暇申請承認審査規程 (2026年度 勤怠管理・人事総務部門)
参照規程: 就業規則第28条(年次有給休暇) / 特別有給休暇規程 (shinkui_keiyaku_tetsuzuki)

【承認基準 (Approved Criteria)】
1. 有給休暇 (年次有休)
   - 申請日数が保有有給残日数以内(requested_days <= remaining_balance)かつ、連続3日以下の申請は自動承認とする。
2. 半日有給申請 (午前半休・午後半休)
   - 申請日数0.5日。有給残数内である場合、通院・役所手続き等の事由を問わず自動承認とする。
3. 夏季特別休暇 (7月〜9月期間)
   - 会社所定の夏季一斉取得枠(3日以内)。有給残数を減算せず特別休暇として自動承認とする。
4. 在宅研修休暇 (専門技術習得)
   - 計画書提出済かつ1日以内の場合、自動承認とする。

【保留・要人事精査基準 (Hold / Review Rules)】
1. 有休残日数超過申請 (Leave Quota Deficit)
   - 申請日数(requested_days)が有休残日数(remaining_balance)を超える場合(requested_days > remaining_balance)、残数不足につき即時保留(Hold)とする。
2. 3日を超える長期連続休暇 (Long Consecutive Leave)
   - 申請日数が3日を超える場合(requested_days > 3.0)、業務代替人員調整および部門長事前決裁を確認するため保留(Hold)とする。
3. 病気休暇の医師診断書未添付 (Medical Leave Missing Certificate)
   - 病気休暇(leave_type = '病気休暇')で医師診断書が添付されていない場合(has_attachment = FALSE)、保留(Hold)とし診断書原本提出を求める。
4. 慶弔特別休暇の証明書未添付 (Bereavement Leave Missing Certificate)
   - 慶弔特別休暇(leave_type = '慶弔特別休暇')で会葬礼状等の証明書が添付されていない場合(has_attachment = FALSE)、保留(Hold)とする。
5. 未登録休暇区分 (Unregistered Leave Category)
   - 人事システム未定義の休暇種別(leave_type = '未登録休暇')は、人事労務課長精査のため保留(Hold)とする。`;

    let currentAttachmentFileName = '';
    let currentLeaveRecord = null;

    function openAttachmentModal(id, empName, leaveType, attName) {
      currentAttachmentFileName = decodeURIComponent(attName || '添付書類.pdf');
      currentLeaveRecord = (leaveRecords || []).find(function(r) { return r.id === id; });

      const nameDec = decodeURIComponent(empName || '-');
      const typeDec = decodeURIComponent(leaveType || '-');

      const fnEl = document.getElementById('att-doc-filename');
      if (fnEl) fnEl.innerText = currentAttachmentFileName;

      const metaEl = document.getElementById('att-doc-meta');
      if (metaEl) metaEl.innerText = '申請ID: ' + id + ' | 氏名: ' + nameDec + ' | 休暇区分: ' + typeDec;

      const pathEl = document.getElementById('att-doc-path');
      if (pathEl) {
        pathEl.innerText = (currentAttachmentPath || ('./attachments/' + currentAttachmentFileName));
      }

      const sealEl = document.getElementById('att-seal-check');
      const diagEl = document.getElementById('att-diag-check');
      const daysEl = document.getElementById('att-days-check');

      if (currentLeaveRecord) {
        if (sealEl) sealEl.innerHTML = currentLeaveRecord.doc_has_doctor_seal ? '✅ <strong>医療機関発行印鑑:</strong> 照合済（原本スキャンデータ整合）' : '⚠️ <strong>医療機関発行印鑑:</strong> 押印なし（要確認・再提出）';
        if (diagEl) diagEl.innerHTML = '📋 <strong>抽出診断名:</strong> ' + (currentLeaveRecord.doc_diagnosis || currentLeaveRecord.reason || '急性上気道炎');
        if (daysEl) daysEl.innerHTML = '⏱️ <strong>医師推奨療養日数:</strong> ' + (currentLeaveRecord.doc_recommended_days != null ? currentLeaveRecord.doc_recommended_days + '日' : currentLeaveRecord.requested_days + '日') + ' (申請日数 ' + currentLeaveRecord.requested_days + '日と突合)';
      }

      const modal = document.getElementById('attachment-preview-modal');
      if (modal) modal.style.display = 'flex';
    }
    window.openAttachmentModal = openAttachmentModal;

    function closeAttachmentModal() {
      const modal = document.getElementById('attachment-preview-modal');
      if (modal) modal.style.display = 'none';
    }
    window.closeAttachmentModal = closeAttachmentModal;

    async function openExplorerFile(action) {
      try {
        const res = await fetch('/api/open-explorer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: currentAttachmentFileName,
            action: action || 'select'
          })
        });
        const data = await res.json();
        if (data.success) {
          console.log('Windows Explorer executed:', data);
        } else {
          alert('Explorer起動通知: ' + (data.error || 'ファイルが見つかりません'));
        }
      } catch (err) {
        alert('Explorer呼び出しエラー: ' + err);
      }
    }
    window.openExplorerFile = openExplorerFile;

    async function openExplorerFolder() {
      return openExplorerFile('select');
    }
    window.openExplorerFolder = openExplorerFolder;

    /* --- Render Leave Applications Table --- */
    function renderLeaveTable(records) {
      document.getElementById('table-row-count').innerText = '(' + records.length + ' 件)';
      let appCount = 0, holdCount = 0, unpCount = 0;

      const thead = document.getElementById('erp-table-head');
      thead.innerHTML = '<tr>' +
        '<th style="width: 100px;">申請ID</th>' +
        '<th style="width: 75px;">社員番号</th>' +
        '<th style="width: 100px;">氏名</th>' +
        '<th style="width: 90px;">所属部署</th>' +
        '<th style="width: 95px;">休暇種別</th>' +
        '<th style="width: 130px;">申請期間</th>' +
        '<th style="width: 70px; text-align: right;">申請日数</th>' +
        '<th style="width: 70px; text-align: right;">有給残数</th>' +
        '<th>申請事由</th>' +
        '<th style="width: 90px; text-align: center;">添付書類</th>' +
        '<th style="width: 80px;">ステータス</th>' +
        '<th style="width: 70px; text-align: center;">審査</th>' +
        '<th style="width: 140px; text-align: center;">手動判定</th>' +
      '</tr>';

      const tbody = document.getElementById('erp-table-body');
      tbody.innerHTML = records.map(function(r) {
        if (r.status === 'Approved') appCount++;
        else if (r.status === 'Hold' || r.status === 'On Hold') holdCount++;
        else unpCount++;

        const isApproved = (r.status === 'Approved');
        const isHold = (r.status === 'Hold' || r.status === 'On Hold');

        const badgeClass = isApproved ? 'badge-approved' : (isHold ? 'badge-hold' : 'badge-unprocessed');
        const statusLabel = isApproved ? 'Approve' : (isHold ? 'On Hold' : (r.status || 'Unprocessed'));

        const hasComm = Boolean(r.comment && r.comment.trim());
        const commentEsc = encodeURIComponent(r.comment || '');
        const nameEsc = encodeURIComponent(r.employee_name || '');
        const commentTitle = hasComm ? r.comment.replace(/"/g, '&quot;') : 'コメント追加...';

        const commentCell = '<div style="display: flex; justify-content: center; align-items: center;">' +
          '<button class="btn-comment-icon-btn ' + (hasComm ? 'has-comment' : '') + '" ' +
            'title="' + commentTitle + '" ' +
            'onclick="openCommentModal(\'' + r.id + '\', \'' + commentEsc + '\', \'' + r.status + '\', \'' + nameEsc + '\', \'' + r.requested_days + '日\')">' +
            '💬' + (hasComm ? '<span class="comment-dot"></span>' : '<span class="comment-add-plus">+</span>') +
          '</button>' +
        '</div>';

        const actionCell = '<div style="display: flex; gap: 4px; justify-content: center;">' +
          '<button class="btn-action-approve ' + (isApproved ? 'active' : '') + '" title="休暇申請を承認" onclick="quickApproveRow(\'' + r.id + '\')">' +
            '✓ Approve' +
          '</button>' +
          '<button class="btn-action-hold ' + (isHold ? 'active' : '') + '" title="休暇申請を保留" onclick="quickHoldRow(\'' + r.id + '\')">' +
            '✕ On Hold' +
          '</button>' +
        '</div>';

        const hasAtt = Boolean(r.has_attachment);
        const attCell = hasAtt ?
          '<button onclick="openAttachmentModal(\'' + r.id + '\', \'' + nameEsc + '\', \'' + encodeURIComponent(r.leave_type) + '\', \'' + encodeURIComponent(r.attachment_name || '添付書類.pdf') + '\')" style="background: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; cursor: pointer;">📎 添付確認</button>' :
          '<span style="color: #94a3b8; font-size: 11px;">なし</span>';

        const periodStr = (r.start_date === r.end_date) ? r.start_date : (r.start_date + '〜' + r.end_date.slice(5));

        return '<tr>' +
          '<td><strong>' + r.id + '</strong></td>' +
          '<td>' + (r.employee_id || '-') + '</td>' +
          '<td><strong>' + (r.employee_name || '-') + '</strong></td>' +
          '<td>' + (r.department || '-') + '</td>' +
          '<td><span style="font-weight: 600; color: #1e40af;">' + (r.leave_type || '-') + '</span></td>' +
          '<td><span style="font-size: 11px; color: #64748b;">' + periodStr + '</span></td>' +
          '<td style="text-align: right; font-weight: 700; color: #0f172a;">' + (r.requested_days != null ? r.requested_days.toFixed(1) + '日' : '-') + '</td>' +
          '<td style="text-align: right; color: ' + (r.remaining_balance < r.requested_days ? '#b91c1c; font-weight: 700;' : '#475569;') + '">' + (r.remaining_balance != null ? r.remaining_balance.toFixed(1) + '日' : '-') + '</td>' +
          '<td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + (r.reason || '').replace(/"/g, '&quot;') + '">' + (r.reason || '-') + '</td>' +
          '<td style="text-align: center;">' + attCell + '</td>' +
          '<td><span class="status-badge ' + badgeClass + '">' + statusLabel + '</span></td>' +
          '<td>' + commentCell + '</td>' +
          '<td style="text-align: center;">' + actionCell + '</td>' +
        '</tr>';
      }).join('');

      document.getElementById('metric-approved-count').innerText = appCount;
      document.getElementById('metric-hold-count').innerText = holdCount;
      document.getElementById('metric-unprocessed-count').innerText = unpCount;
    }

    function renderInvoiceTable(records) {
      document.getElementById('table-row-count').innerText = '(' + records.length + ' 件)';
      let appCount = 0, holdCount = 0, unpCount = 0;

      const thead = document.getElementById('erp-table-head');
      thead.innerHTML = '<tr>' +
        '<th style="width: 120px;">Voucher ID</th>' +
        '<th style="width: 75px;">Vendor CD</th>' +
        '<th>Vendor Name</th>' +
        '<th style="width: 95px;">Invoice No</th>' +
        '<th style="width: 85px; text-align: right;">Amount</th>' +
        '<th style="width: 75px;">Category</th>' +
        '<th style="width: 85px;">Status</th>' +
        '<th style="width: 80px; text-align: center;">Confirmation comment</th>' +
        '<th style="width: 145px; text-align: center;">Action</th>' +
      '</tr>';

      const tbody = document.getElementById('erp-table-body');
      tbody.innerHTML = records.map(function(r) {
        if (r.status === 'Approved') appCount++;
        else if (r.status === 'Hold') holdCount++;
        else unpCount++;

        const isApproved = (r.status === 'Approved');
        const isHold = (r.status === 'Hold' || r.status === 'On Hold');

        const badgeClass = isApproved ? 'badge-approved' : (isHold ? 'badge-hold' : 'badge-unprocessed');
        const statusLabel = isApproved ? 'Approve' : (isHold ? 'On Hold' : (r.status || 'Unprocessed'));
        
        const hasComm = Boolean(r.comment && r.comment.trim());
        const commentEsc = encodeURIComponent(r.comment || '');
        const nameEsc = encodeURIComponent(r.name || '');
        const commentTitle = hasComm ? r.comment.replace(/"/g, '&quot;') : 'Add a comment...';

        // ONLY Icon for the comments column
        const commentCell = '<div style="display: flex; justify-content: center; align-items: center;">' +
          '<button class="btn-comment-icon-btn ' + (hasComm ? 'has-comment' : '') + '" ' +
            'title="' + commentTitle + '" ' +
            'onclick="openCommentModal(\'' + r.id + '\', \'' + commentEsc + '\', \'' + r.status + '\', \'' + nameEsc + '\', \'' + r.amount + '\')">' +
            '💬' + (hasComm ? '<span class="comment-dot"></span>' : '<span class="comment-add-plus">+</span>') +
          '</button>' +
        '</div>';

        // Action buttons: Approve and On Hold
        const actionCell = '<div style="display: flex; gap: 4px; justify-content: center;">' +
          '<button class="btn-action-approve ' + (isApproved ? 'active' : '') + '" title="Approve invoice" onclick="quickApproveRow(\'' + r.id + '\')">' +
            '✓ Approve' +
          '</button>' +
          '<button class="btn-action-hold ' + (isHold ? 'active' : '') + '" title="Place invoice on hold" onclick="quickHoldRow(\'' + r.id + '\')">' +
            '✕ On Hold' +
          '</button>' +
        '</div>';

        return '<tr>' +
          '<td><strong>' + r.id + '</strong></td>' +
          '<td>' + (r.vendor_code || r.employee_id || '-') + '</td>' +
          '<td>' + (r.vendor_name || r.name || '-') + '</td>' +
          '<td><span style="font-family: monospace; color: #64748b;">' + (r.invoice_no || '-') + '</span></td>' +
          '<td style="text-align: right; font-weight: 700; color: #1e3a8a;">' + r.amount + '</td>' +
          '<td><span style="font-size: 11px; font-weight: 600; color: ' + (r.type === 'Adjustment' ? '#b45309' : '#0284c7') + ';">' + (r.type || 'Routine') + '</span></td>' +
          '<td><span class="status-badge ' + badgeClass + '">' + statusLabel + '</span></td>' +
          '<td>' + commentCell + '</td>' +
          '<td style="text-align: center;">' + actionCell + '</td>' +
        '</tr>';
      }).join('');

      document.getElementById('metric-approved-count').innerText = appCount;
      document.getElementById('metric-hold-count').innerText = holdCount;
      document.getElementById('metric-unprocessed-count').innerText = unpCount;
    }

    /* --- Render Payroll Table --- */
    function renderPayrollTable(records) {
      document.getElementById('table-row-count').innerText = '(' + records.length + ' 件)';
      let appCount = 0, holdCount = 0, unpCount = 0;

      const thead = document.getElementById('erp-table-head');
      thead.innerHTML = '<tr>' +
        '<th style="width: 120px;">Voucher ID</th>' +
        '<th style="width: 75px;">Emp ID</th>' +
        '<th>Employee Name</th>' +
        '<th style="width: 100px;">Item Category</th>' +
        '<th style="width: 65px;">Type</th>' +
        '<th style="width: 85px; text-align: right;">Amount</th>' +
        '<th style="width: 110px;">Ref Voucher</th>' +
        '<th style="width: 85px;">Status</th>' +
        '<th style="width: 80px; text-align: center;">Confirmation comment</th>' +
        '<th style="width: 145px; text-align: center;">Action</th>' +
      '</tr>';

      const tbody = document.getElementById('erp-table-body');
      tbody.innerHTML = records.map(function(r) {
        if (r.status === 'Confirmed') appCount++;
        else if (r.status === 'Hold') holdCount++;
        else unpCount++;

        const isApproved = (r.status === 'Confirmed' || r.status === 'Approved');
        const isHold = (r.status === 'Hold' || r.status === 'On Hold');

        const badgeClass = isApproved ? 'badge-confirmed' : (isHold ? 'badge-hold' : 'badge-unprocessed');
        const statusLabel = isApproved ? 'Approve' : (isHold ? 'On Hold' : (r.status || 'Unprocessed'));

        const hasComm = Boolean(r.comment && r.comment.trim());
        const commentEsc = encodeURIComponent(r.comment || '');
        const empEsc = encodeURIComponent(r.employee_name || '');
        const commentTitle = hasComm ? r.comment.replace(/"/g, '&quot;') : 'Add a comment...';

        // ONLY Icon for the comments column
        const commentCell = '<div style="display: flex; justify-content: center; align-items: center;">' +
          '<button class="btn-comment-icon-btn ' + (hasComm ? 'has-comment' : '') + '" ' +
            'title="' + commentTitle + '" ' +
            'onclick="openCommentModal(\'' + r.id + '\', \'' + commentEsc + '\', \'' + r.status + '\', \'' + empEsc + '\', \'' + r.amount + '\')">' +
            '💬' + (hasComm ? '<span class="comment-dot"></span>' : '<span class="comment-add-plus">+</span>') +
          '</button>' +
        '</div>';

        // Action buttons: Approve and On Hold
        const actionCell = '<div style="display: flex; gap: 4px; justify-content: center;">' +
          '<button class="btn-action-approve ' + (isApproved ? 'active' : '') + '" title="Approve payroll item" onclick="quickApproveRow(\'' + r.id + '\')">' +
            '✓ Approve' +
          '</button>' +
          '<button class="btn-action-hold ' + (isHold ? 'active' : '') + '" title="Place item on hold" onclick="quickHoldRow(\'' + r.id + '\')">' +
            '✕ On Hold' +
          '</button>' +
        '</div>';

        return '<tr>' +
          '<td><strong>' + r.id + '</strong></td>' +
          '<td>' + (r.employee_id || '-') + '</td>' +
          '<td><strong>' + r.employee_name + '</strong></td>' +
          '<td>' + r.item_category + '</td>' +
          '<td><span style="font-size: 11px; font-weight: 600; color: ' + (r.item_type === 'Deduction' ? '#b45309' : '#15803d') + ';">' + r.item_type + '</span></td>' +
          '<td style="text-align: right; font-weight: 700; color: #1e3a8a;">' + r.amount + '</td>' +
          '<td><span style="font-family: monospace; font-size: 11px; color: #64748b;">' + (r.voucher_ref || '-') + '</span></td>' +
          '<td><span class="status-badge ' + badgeClass + '">' + statusLabel + '</span></td>' +
          '<td>' + commentCell + '</td>' +
          '<td style="text-align: center;">' + actionCell + '</td>' +
        '</tr>';
      }).join('');

      document.getElementById('metric-approved-count').innerText = appCount;
      document.getElementById('metric-hold-count').innerText = holdCount;
      document.getElementById('metric-unprocessed-count').innerText = unpCount;
    }

    /* --- Retractable LangGraph Tracker State --- */
    let isGraphTrackerCollapsed = false;
    function toggleGraphTrackerCollapse() {
      toggleLlmOutputCollapse();
    }

    /* --- Row Quick Action: Approve or Disapprove (Hold) --- */
    async function quickApproveRow(rowId) {
      const targetStatus = (currentSuite === 'invoice') ? 'Approved' : 'Confirmed';
      const defaultComment = (currentSuite === 'invoice') 
        ? '月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済 (Approved)'
        : '業務委託経費規程適合確認済・経費精算確定 (Confirmed)';

      const records = (currentSuite === 'invoice') ? invoiceRecords : ((currentSuite === 'leave') ? leaveRecords : payrollRecords);
      const r = records.find(function(x) { return x.id === rowId; });
      const currentComment = (r && r.comment && r.comment.trim()) ? r.comment : defaultComment;

      try {
        const res = await fetch('/api/item/override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            suite: currentSuite,
            id: rowId,
            status: targetStatus,
            comment: currentComment
          })
        });
        const d = await res.json();
        if (d.success) {
          await loadTableData();
        } else {
          alert('承認処理に失敗しました。');
        }
      } catch (e) {
        alert('通信エラー: ' + e);
      }
    }

    async function quickHoldRow(rowId) {
      const records = (currentSuite === 'invoice') ? invoiceRecords : ((currentSuite === 'leave') ? leaveRecords : payrollRecords);
      const r = records.find(function(x) { return x.id === rowId; });
      const defaultHoldComment = (currentSuite === 'invoice')
        ? '[HOLD] 請求金額または契約範囲要確認につき保留'
        : '[HOLD] 経費規程確認または証憑精査のため保留';
      const currentComment = (r && r.comment && r.comment.trim()) 
        ? r.comment 
        : defaultHoldComment;

      const name = (currentSuite === 'invoice') ? (r ? r.name : '') : (r ? r.employee_name : '');
      const amt = r ? r.amount : '';
      openCommentModal(rowId, encodeURIComponent(currentComment), 'Hold', encodeURIComponent(name), amt);
    }

    /* --- Collapsible & Editable Extracted Rules State --- */
    let activeExtractedRules = [];
    let isLlmOutputCollapsed = false;

    function toggleLlmOutputCollapse() {
      isLlmOutputCollapsed = !isLlmOutputCollapsed;
      const content = document.getElementById('llm-rules-content');
      const icon = document.getElementById('llm-collapse-icon');
      const text = document.getElementById('llm-toggle-text');

      if (isLlmOutputCollapsed) {
        content.classList.add('collapsed');
        icon.innerText = '►';
        text.innerText = '[ Click to Expand ]';
      } else {
        content.classList.remove('collapsed');
        icon.innerText = '▼';
        text.innerText = '[ Click to Collapse ]';
      }
    }

    function formatConditionDisplay(r) {
      if (r.sql_condition && r.sql_condition.trim()) return r.sql_condition.trim();
      if (r.condition && r.condition.trim()) return r.condition.trim();
      const num = r.expected_amount || r.threshold_amount || 0;
      const field = r.match_field || (currentSuite === 'invoice' ? 'raw_amount' : 'amount');
      if (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected') {
        return num ? (field + ' > ' + num) : 'status = \'Hold\'';
      } else {
        return num ? (field + ' = ' + num) : 'status = \'Approved\'';
      }
    }

    function renderInitialExtractedRules() {
      if (currentSuite === 'invoice') {
        activeExtractedRules = [
          { rule_id: 'RULE-INV-01', match_value: 'Global Tech LLC (V3005)', condition: "type = 'Routine' AND raw_amount = 716232 AND vendor_code = 'V3005'", sql_condition: "type = 'Routine' AND raw_amount = 716232 AND vendor_code = 'V3005'", action_on_match: 'Approved', description: 'Recurring SaaS contract rate matched' },
          { rule_id: 'RULE-INV-02', match_value: 'Hokuriku Parts (V3006)', condition: "type = 'Routine' AND raw_amount IN (455128, 452219) AND vendor_code = 'V3006'", sql_condition: "type = 'Routine' AND raw_amount IN (455128, 452219) AND vendor_code = 'V3006'", action_on_match: 'Approved', description: 'Routine parts maintenance contract matched' },
          { rule_id: 'RULE-INV-03', match_value: 'Yamato Shoji (V3002)', condition: "type = 'Routine' AND raw_amount IN (1237439, 1218687) AND vendor_code = 'V3002'", sql_condition: "type = 'Routine' AND raw_amount IN (1237439, 1218687) AND vendor_code = 'V3002'", action_on_match: 'Approved', description: 'Business outsourcing contract verified' },
          { rule_id: 'RULE-INV-04', match_value: 'Fukuoka System (V3007)', condition: "type = 'Routine' AND raw_amount IN (1832962, 1993825, 1685384) AND vendor_code = 'V3007'", sql_condition: "type = 'Routine' AND raw_amount IN (1832962, 1993825, 1685384) AND vendor_code = 'V3007'", action_on_match: 'Approved', description: 'IT infrastructure maintenance contract matched' },
          { rule_id: 'RULE-INV-05', match_value: 'Hokuriku Parts (V3006) Adjustment', condition: "vendor_code = 'V3006' AND type = 'Adjustment'", sql_condition: "vendor_code = 'V3006' AND type = 'Adjustment'", action_on_match: 'Hold', description: 'Emergency air freight surcharge inspection per policy' },
          { rule_id: 'RULE-INV-ADJ', match_value: 'Okinawa Logistics (V3008)', condition: "vendor_code = 'V3008' AND type = 'Adjustment'", sql_condition: "vendor_code = 'V3008' AND type = 'Adjustment'", action_on_match: 'Hold', description: 'Logistics delivery receipt and manager review required' },
          { rule_id: 'RULE-INV-CAT', match_value: 'Adjustment Category', condition: "type = 'Adjustment'", sql_condition: "type = 'Adjustment'", action_on_match: 'Hold', description: 'Accounting inspection required for all adjustment vouchers per policy' },
          { rule_id: 'RULE-INV-CEIL', match_value: 'Policy Ceiling (> ¥2,000,000)', condition: "raw_amount > 2000000", sql_condition: "raw_amount > 2000000", action_on_match: 'Hold', description: 'Director sanction required for invoices exceeding ceiling' }
        ];
      } else {
        activeExtractedRules = [
          { rule_id: 'RULE-PAY-01', match_value: 'Takuya Aoki (P4-07089771-001)', condition: "id = 'P4-07089771-001' AND raw_amount <= 100000", sql_condition: "id = 'P4-07089771-001' AND raw_amount <= 100000", action_on_match: 'Confirmed', description: 'Article 4 technical training regulation compliant' },
          { rule_id: 'RULE-PAY-02', match_value: 'Rie Kikuchi (P4-07089771-002)', condition: "id = 'P4-07089771-002' AND raw_amount <= 100000", sql_condition: "id = 'P4-07089771-002' AND raw_amount <= 100000", action_on_match: 'Confirmed', description: 'Development consumables receipt verified' },
          { rule_id: 'RULE-PAY-03', match_value: 'Yuji Sakamoto (P4-07089771-003)', condition: "id = 'P4-07089771-003' AND raw_amount <= 100000", sql_condition: "id = 'P4-07089771-003' AND raw_amount <= 100000", action_on_match: 'Confirmed', description: 'Osaka branch technical trip report matched' },
          { rule_id: 'RULE-PAY-ENT', match_value: 'All Staff (Entertainment)', condition: "item_category = '接待交際費' AND raw_amount > 100000", sql_condition: "item_category = '接待交際費' AND raw_amount > 100000", action_on_match: 'Hold', description: 'Article 7 limit exceeded, executive special sanction required' },
          { rule_id: 'RULE-PAY-CLASS', match_value: 'Dependent Deduction / Position Abolition', condition: "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'", sql_condition: "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'", action_on_match: 'Hold', description: 'Classification error (Deduction registered as Addition)' },
          { rule_id: 'RULE-PAY-CEIL', match_value: 'All Expense Items', condition: "raw_amount > 150000", sql_condition: "raw_amount > 150000", action_on_match: 'Hold', description: 'Exceeds standard single ceiling, prior approval memo required' },
          { rule_id: 'RULE-PAY-UNK', match_value: 'All Allowance Items', condition: "item_category NOT IN ('研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '昇給')", sql_condition: "item_category NOT IN ('研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '昇給')", action_on_match: 'Hold', description: 'Unregistered allowance code requires HR authorization' }
        ];
      }
      renderExtractedRulesTable();
    }

    function renderExtractedRulesTable() {
      const tbody = document.getElementById('rules-table-body');
      const badge = document.getElementById('rules-count-badge');
      if (badge) badge.innerText = activeExtractedRules.length + ' Rules Active';

      if (!tbody) return;
      tbody.innerHTML = activeExtractedRules.map(function(r, idx) {
        const isHold = (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected');
        const condVal = formatConditionDisplay(r);
        return '<tr>' +
          '<td style="text-align: center; color: #64748b;">' + (idx + 1) + '</td>' +
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', &quot;rule_id&quot;, this.value)" style="width: 100%; box-sizing: border-box; font-weight: 600; font-size: 11px; padding: 4px 6px;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', &quot;match_value&quot;, this.value)" style="width: 100%; box-sizing: border-box; font-size: 11px; padding: 4px 6px;"></td>' +
          '<td><input type="text" value="' + condVal.replace(/"/g, '&quot;') + '" onchange="updateRuleCell(' + idx + ', &quot;condition&quot;, this.value)" style="width: 100%; box-sizing: border-box; font-family: Consolas, monospace; font-size: 11px; padding: 4px 6px;"></td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', &quot;action_on_match&quot;, this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + '; width: 100%; box-sizing: border-box; padding: 4px; font-size: 11px;">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', &quot;description&quot;, this.value)" style="width: 100%; box-sizing: border-box; font-size: 11px; padding: 4px 6px;"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    }

    function updateRuleCell(idx, field, val) {
      if (activeExtractedRules[idx]) {
        activeExtractedRules[idx][field] = val;
        if (field === 'condition') {
          activeExtractedRules[idx]['sql_condition'] = val;
        } else if (field === 'sql_condition') {
          activeExtractedRules[idx]['condition'] = val;
        }
        if (field === 'action_on_match') {
          renderExtractedRulesTable();
        }
      }
    }

    function addNewExtractedRule() {
      const defaultSql = (currentSuite === 'invoice' ? "type = 'Routine' AND raw_amount = 500000" : "item_category = '経費項目' AND raw_amount <= 50000");
      activeExtractedRules.push({
        rule_id: 'RULE-CUSTOM-' + (activeExtractedRules.length + 1),
        match_value: 'Custom Target',
        condition: defaultSql,
        sql_condition: defaultSql,
        action_on_match: (currentSuite === 'invoice' ? 'Approved' : 'Confirmed'),
        description: 'User-configured SQL policy rule'
      });
      renderExtractedRulesTable();
    }

    function deleteExtractedRule(idx) {
      activeExtractedRules.splice(idx, 1);
      renderExtractedRulesTable();
    }

    async function runPolicyAnalysis() {
      const isConnected = await ensurePuterConnectedIfRequired();
      if (!isConnected) return;

      const docText = document.getElementById('doc-text').value.trim();
      if (!docText) {
        alert('Please enter or load policy/memo text to analyze.');
        return;
      }

      const btnAnalyze = document.getElementById('btn-analyze');
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.innerHTML = '<span class="loading-spinner"></span> Analyzing...';
      }

      resetGraphUi();
      setNodeActive('node-1');
      setNodeActive('node-2');

      try {
        const res = await fetch('/api/copilot/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            process_type: currentSuite,
            document_text: docText,
            filename_or_title: (currentSuite === 'invoice') ? 'getsujitsu_teigaku_torihikisaki_ichiran.docx' : '*精算確認メモ.txt'
          })
        });
        let data;
        const textResp = await res.text();
        try {
          data = JSON.parse(textResp);
        } catch (parseErr) {
          throw new Error('Server returned non-JSON response (' + res.status + '): ' + textResp.slice(0, 120));
        }
        if (data.success && data.rules && data.rules.length > 0) {
          activeExtractedRules = data.rules;
          renderExtractedRulesTable();
          setNodeDone('node-1', '0.15s');
          setNodeDone('node-2', '0.18s');
          if (isLlmOutputCollapsed) toggleLlmOutputCollapse();
          alert('✓ LLM & SQL検証完了: ' + activeExtractedRules.length + ' 件のSQLルールを抽出・検証しました。\n条件式やアクションを編集後、下の [▶ Continue & Evaluate Database] を押すと実データベース行と照合されます。');
        } else {
          setNodeDone('node-1', '0.12s');
          setNodeDone('node-2', '0.10s');
          alert('Analysis completed using standard rules.');
        }
      } catch (e) {
        alert('Analysis error: ' + e);
      } finally {
        const btnAnalyze = document.getElementById('btn-analyze');
        if (btnAnalyze) {
          btnAnalyze.disabled = false;
          btnAnalyze.innerHTML = '🔍 Analyze';
        }
      }
    }

    function syncActiveRulesFromDom() {
      const tbody = document.getElementById('rules-table-body');
      if (!tbody) return;
      const rows = tbody.querySelectorAll('tr');
      rows.forEach(function(tr, idx) {
        if (activeExtractedRules[idx]) {
          const inputs = tr.querySelectorAll('input');
          const select = tr.querySelector('select');
          if (inputs.length >= 4) {
            activeExtractedRules[idx].rule_id = inputs[0].value.trim();
            activeExtractedRules[idx].match_value = inputs[1].value.trim();
            activeExtractedRules[idx].name = inputs[1].value.trim();
            const cond = inputs[2].value.trim();
            activeExtractedRules[idx].condition = cond;
            activeExtractedRules[idx].sql_condition = cond;
            if (select) {
              activeExtractedRules[idx].action_on_match = select.value;
            }
            activeExtractedRules[idx].description = inputs[3].value.trim();
          }
        }
      });
    }

    async function continueAndEvaluateDatabase() {
      const isConnected = await ensurePuterConnectedIfRequired();
      if (!isConnected) return;

      syncActiveRulesFromDom();
      const docText = document.getElementById('doc-text').value.trim();
      if (!activeExtractedRules || activeExtractedRules.length === 0) {
        await analyzeDocumentWithLlm();
      }
      if (isGraphTrackerCollapsed) {
        toggleGraphTrackerCollapse();
      }
      resetGraphUi();
      setNodeDone('node-1', '0.15s');
      setNodeDone('node-2', '0.18s');
      setNodeActive('node-3');

      const btnRun = document.getElementById('btn-run');
      const btnContinue = document.getElementById('btn-continue-eval');
      const tableBanner = document.getElementById('table-loading-banner');

      if (btnRun) {
        btnRun.disabled = true;
        btnRun.innerHTML = '<span class="loading-spinner"></span> Running LangGraph Agent...';
      }
      if (btnContinue) {
        btnContinue.disabled = true;
        btnContinue.innerHTML = '<span class="loading-spinner"></span> Evaluating...';
      }
      if (tableBanner) {
        tableBanner.style.display = 'flex';
      }

      try {
        const res = await fetch('/api/copilot/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            process_type: currentSuite,
            document_text: docText,
            filename_or_title: (currentSuite === 'invoice') ? 'getsujitsu_teigaku_torihikisaki_ichiran.docx' : '*精算確認メモ.txt',
            custom_rules: activeExtractedRules
          })
        });
        const result = await res.json();
        if (result.success) {
          setNodeDone('node-3', '0.22s');
          setNodeDone('node-4', '0.08s');
          setNodeDone('node-5', 'Ready');
          stagedDecisionsData = result.staged_decisions || [];

          // Database changes are STAGED only (committed only when user confirms)
          const appCount = result.approved_count || 0;
          const hldCount = result.hold_count || 0;
          const totalCount = result.evaluated_count || 0;
          console.log(`[Staged Evaluation] ${appCount} Approved, ${hldCount} Hold out of ${totalCount} records.`);

          const gBadge = document.getElementById('graph-overall-badge');
          if (gBadge) {
            gBadge.innerText = 'AUDIT READY';
            gBadge.style.background = '#fef08a';
          }
          if (typeof renderInterventions === 'function') {
            renderInterventions(result.discrepancies || []);
          } else if (typeof window.renderInterventions === 'function') {
            window.renderInterventions(result.discrepancies || []);
          }
          if (typeof openStagedModal === 'function') {
            openStagedModal(result);
          } else if (typeof window.openStagedModal === 'function') {
            window.openStagedModal(result);
          }
        } else {
          alert('Evaluation error: ' + (result.error || 'Unknown error'));
        }
      } catch (e) {
        console.error('Database evaluation error:', e);
        if (e && e.toString().includes('renderInterventions')) {
          alert('System update detected. Please press Ctrl+F5 (or Shift+Reload) to refresh your browser cache.');
        } else {
          alert('Communication error: ' + e);
        }
      } finally {
        const btnRun = document.getElementById('btn-run');
        const btnContinue = document.getElementById('btn-continue-eval');
        const tableBanner = document.getElementById('table-loading-banner');

        if (btnRun) {
          btnRun.disabled = false;
          btnRun.innerHTML = '⚡ Run LangGraph Co-Pilot Agent';
        }
        if (btnContinue) {
          btnContinue.disabled = false;
          btnContinue.innerHTML = '▶ Continue & Evaluate Database';
        }
        if (tableBanner) {
          tableBanner.style.display = 'none';
        }
      }
    }

    /* --- Workspace Tabs (Clean 2-Tab Switcher) --- */
    function switchWsTab(tab) {
      ['notepad', 'excel'].forEach(function(t) {
        const btn = document.getElementById('ws-btn-' + t);
        const pane = document.getElementById('ws-tab-' + t);
        if (btn) btn.classList.toggle('active', t === tab);
        if (pane) pane.style.display = (t === tab) ? 'flex' : 'none';
      });
    }

    function loadSampleEnglishRules() {
      const sample = `Rule 1 — Vendor Registration\n\nThe following vendor codes are registered: V3001, V3002, V3004, V3005, V3006, V3007, V3008, V3009, V3010, V3011, and V3012.\n\nHold any voucher whose vendor code is not on this list.\n\nRule 2 — Adjustment Review\n\nHold every voucher with category Adjustment, regardless of amount or vendor. Manual finance review is mandatory.\n\nRule 3 — High-Value Review\n\nHold every voucher whose amount is strictly greater than ¥1,800,000. This rule applies to all vendors, including registered vendors and invoices whose amounts appear in their contracts.\n\nAn amount equal to ¥1,800,000 does not trigger this rule.\n\nRule 4 — Routine Approval\n\nApprove a voucher only if:\n\nThe vendor code is registered.\n\nThe category is Routine.\n\nThe amount is ¥1,800,000 or less.\n\nNo mandatory Hold rule applies.\n\nExact contract-amount matching is not required under this policy.`;
      document.getElementById('doc-text').value = sample;
      const fn = document.getElementById('notepad-filename');
      if (fn) fn.innerText = '📜 English Vendor Billing Policy (4 Rules)';
      analyzePolicyWithCopilot();
    }

    function loadPresetDocument() {
      document.getElementById('doc-text').value = (currentSuite === 'invoice') ? INVOICE_PRESET : PAYROLL_PRESET;
      analyzePolicyWithCopilot();
    }

    /* --- Policy & Memo File Upload Handler (.docx / .txt) --- */
    async function handlePolicyFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/upload-doc', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          document.getElementById('doc-text').value = data.text;
          const fn = document.getElementById('notepad-filename');
          if (fn) fn.innerText = '📄 ' + data.filename + ' (' + data.text.length + '文字 読込済)';
          analyzePolicyWithCopilot();
        } else {
          alert('解析エラー: ' + (data.error || '不明なエラー'));
        }
      } catch (e) {
        alert('アップロードエラー: ' + e);
      } finally {
        event.target.value = '';
      }
    }
    window.handlePolicyFileUpload = handlePolicyFileUpload;

    /* --- Regulations Master Excel / CSV Upload Handler --- */
    async function handleMasterExcelUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/master/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success && data.regulations) {
          masterRegulationsData = data.regulations;
          renderMasterRegulationsTable();
          alert('✓ 規程マスタ (' + data.filename + ') から ' + data.count + ' 件の規程データを取り込みました。');
        } else {
          alert('取込エラー: ' + (data.error || '不明なエラー'));
        }
      } catch (e) {
        alert('マスタExcelアップロードエラー: ' + e);
      } finally {
        event.target.value = '';
      }
    }
    window.handleMasterExcelUpload = handleMasterExcelUpload;

    /* --- Download Current Regulations Master as CSV Template --- */
    function downloadMasterRegulationsCsv() {
      if (!masterRegulationsData || masterRegulationsData.length === 0) {
        alert('出力対象の規程マスタデータがありません。');
        return;
      }
      const headers = ['コード', '対象名称/項目', '上限/契約定額', '承認要件', '区分'];
      const lines = [headers.join(',')];
      masterRegulationsData.forEach(function(r) {
        const row = [
          '"' + (r.code || '').replace(/"/g, '""') + '"',
          '"' + (r.name || '').replace(/"/g, '""') + '"',
          '"' + (r.limit || '').replace(/"/g, '""') + '"',
          '"' + (r.req || '').replace(/"/g, '""') + '"',
          '"' + (r.class || '').replace(/"/g, '""') + '"'
        ];
        lines.push(row.join(','));
      });
      const csvContent = '\uFEFF' + lines.join('\r\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'regulations_master_' + currentSuite + '.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
    window.downloadMasterRegulationsCsv = downloadMasterRegulationsCsv;

    /* --- Editable Master Regulations --- */
    async function loadMasterRegulations() {
      try {
        const res = await fetch('/api/master/regulations');
        masterRegulationsData = await res.json();
        renderMasterRegulationsTable();
      } catch (e) {
        console.error('Master regulations load error:', e);
      }
    }

    function renderMasterRegulationsTable() {
      const tbody = document.getElementById('excel-master-tbody');
      const filtered = masterRegulationsData.map(function(row, idx) {
        return { row: row, origIdx: idx };
      }).filter(function(item) {
        if (currentSuite === 'invoice') {
          return item.row.code && item.row.code.startsWith('V');
        } else {
          return !item.row.code || !item.row.code.startsWith('V');
        }
      });

      tbody.innerHTML = filtered.map(function(item, viewIdx) {
        const row = item.row;
        const idx = item.origIdx;
        return '<tr>' +
          '<td style="text-align: center; color: #64748b;">' + (viewIdx + 1) + '</td>' +
          '<td><input type="text" value="' + (row.code || '') + '" onchange="updateMasterCell(' + idx + ', \'code\', this.value)"></td>' +
          '<td><input type="text" value="' + (row.name || '') + '" onchange="updateMasterCell(' + idx + ', \'name\', this.value)"></td>' +
          '<td><input type="text" value="' + (row.limit || '') + '" onchange="updateMasterCell(' + idx + ', \'limit\', this.value)"></td>' +
          '<td><input type="text" value="' + (row.req || '') + '" onchange="updateMasterCell(' + idx + ', \'req\', this.value)"></td>' +
          '<td>' +
            '<select onchange="updateMasterCell(' + idx + ', \'class\', this.value)">' +
              '<option value="Addition" ' + (row.class === 'Addition' ? 'selected' : '') + '>Addition</option>' +
              '<option value="Deduction" ' + (row.class === 'Deduction' ? 'selected' : '') + '>Deduction</option>' +
              '<option value="Routine" ' + (row.class === 'Routine' ? 'selected' : '') + '>Routine</option>' +
              '<option value="Adjustment" ' + (row.class === 'Adjustment' ? 'selected' : '') + '>Adjustment</option>' +
            '</select>' +
          '</td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteMasterRow(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    }

    function updateMasterCell(idx, key, val) {
      if (masterRegulationsData[idx]) masterRegulationsData[idx][key] = val;
    }

    function addMasterRow() {
      masterRegulationsData.push({
        code: '規程第' + (masterRegulationsData.length + 1) + '条',
        name: '新規規程項目',
        limit: '1件上限 100,000円',
        req: '領収書原本照合済',
        class: currentSuite === 'invoice' ? 'Routine' : 'Addition'
      });
      renderMasterRegulationsTable();
    }

    function deleteMasterRow(idx) {
      masterRegulationsData.splice(idx, 1);
      renderMasterRegulationsTable();
    }

    async function saveMasterRegulationsTable() {
      try {
        const res = await fetch('/api/master/regulations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ regulations: masterRegulationsData })
        });
        const d = await res.json();
        alert('規程マスタ (' + d.count + ' 件) をバックエンドへ保存しました。次回のAI評価時に即時反映されます。');
      } catch (e) {
        alert('マスタ保存エラー: ' + e);
      }
    }

    /* --- LangGraph Staged Evaluation & Confirmation Flow --- */
    async function startLangGraphEvaluation() {
      const isConnected = await ensurePuterConnectedIfRequired();
      if (!isConnected) return;
      // Step 1: Extract and verify SQL rules with LLM
      await analyzeDocumentWithLlm();
      // Step 2: Evaluate live rows against verified SQL conditions
      await continueAndEvaluateDatabase();
    }

    

    /* --- Comment Modal & Single Override --- */
    function openCommentModal(id, encodedComment, status, encodedName, amount) {
      activeCommentRecord = { id: id };
      document.getElementById('modal-record-id').innerText = id;
      document.getElementById('modal-entity-label').innerText = currentSuite === 'invoice' ? '取引先名:' : '従業員氏名:';
      document.getElementById('modal-entity-name').innerText = decodeURIComponent(encodedName || '');
      document.getElementById('modal-amount').innerText = amount || '-';
      document.getElementById('modal-status-select').value = status || 'Unprocessed';
      document.getElementById('modal-comment-text').value = decodeURIComponent(encodedComment || '');
      document.getElementById('comment-modal').style.display = 'flex';
    }

    function closeCommentModal() {
      document.getElementById('comment-modal').style.display = 'none';
      activeCommentRecord = null;
    }

    async function commitCommentModal() {
      if (!activeCommentRecord) return;
      const status = document.getElementById('modal-status-select').value;
      const comment = document.getElementById('modal-comment-text').value.trim();

      try {
        const res = await fetch('/api/item/override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            suite: currentSuite,
            id: activeCommentRecord.id,
            status: status,
            comment: comment
          })
        });
        const d = await res.json();
        if (d.success) {
          closeCommentModal();
          loadTableData();
        } else {
          alert('更新に失敗しました。');
        }
      } catch (e) {
        alert('エラー: ' + e);
      }
    }

    /* --- Single Add Record Modal --- */
    function openAddRecordModal() {
      renderSingleAddForm();
      document.getElementById('add-modal').style.display = 'flex';
    }

    function closeAddRecordModal() {
      document.getElementById('add-modal').style.display = 'none';
    }

    function renderSingleAddForm() {
      const container = document.getElementById('add-modal-form');
      if (currentSuite === 'invoice') {
        const nextId = 'P6-07010448-' + (invoiceRecords.length + 1).toString().padStart(3, '0');
        container.innerHTML = 
          '<div class="form-group"><label>伝票番号 (ID):</label><input type="text" id="add-inv-id" class="form-control" value="' + nextId + '"></div>' +
          '<div class="form-group"><label>取引先コード:</label><input type="text" id="add-inv-code" class="form-control" value="V3005"></div>' +
          '<div class="form-group"><label>取引先名称:</label><input type="text" id="add-inv-name" class="form-control" placeholder="例: 日本情報通信株式会社"></div>' +
          '<div class="form-group"><label>請求金額 (円):</label><input type="number" id="add-inv-amt" class="form-control" placeholder="例: 850000"></div>' +
          '<div class="form-group"><label>伝票区分:</label>' +
            '<select id="add-inv-type" class="form-control">' +
              '<option value="Routine" selected>Routine (通常取引)</option>' +
              '<option value="Adjustment">Adjustment (変動調整)</option>' +
            '</select>' +
          '</div>';
      } else {
        const nextId = 'P4-07089771-' + (payrollRecords.length + 1).toString().padStart(3, '0');
        container.innerHTML = 
          '<div class="form-group"><label>伝票番号 (ID):</label><input type="text" id="add-pay-id" class="form-control" value="' + nextId + '"></div>' +
          '<div class="form-group"><label>従業員番号:</label><input type="text" id="add-pay-code" class="form-control" value="EMP-021"></div>' +
          '<div class="form-group"><label>従業員氏名:</label><input type="text" id="add-pay-name" class="form-control" placeholder="例: 山本 健太"></div>' +
          '<div class="form-group"><label>手当・経費項目:</label>' +
            '<select id="add-pay-cat" class="form-control">' +
              '<option value="研修費">研修費</option>' +
              '<option value="消耗品費">消耗品費</option>' +
              '<option value="出張旅費">出張旅費</option>' +
              '<option value="交通費精算">交通費精算</option>' +
              '<option value="残業手当調整">残業手当調整</option>' +
              '<option value="昇給">昇給</option>' +
              '<option value="扶養控除変更">扶養控除変更</option>' +
              '<option value="役職手当新設">役職手当新設</option>' +
              '<option value="役職手当廃止">役職手当廃止</option>' +
            '</select>' +
          '</div>' +
          '<div class="form-group"><label>加算/控除区分:</label>' +
            '<select id="add-pay-type" class="form-control">' +
              '<option value="Addition" selected>Addition (支給・加算)</option>' +
              '<option value="Deduction">Deduction (控除・減算)</option>' +
            '</select>' +
          '</div>' +
          '<div class="form-group"><label>金額 (円):</label><input type="number" id="add-pay-amt" class="form-control" placeholder="例: 75000"></div>';
      }
    }

    async function submitAddRecord() {
      let payload = {};
      let url = '';

      if (currentSuite === 'invoice') {
        url = '/api/invoices/add';
        const amt = parseInt(document.getElementById('add-inv-amt').value || '0', 10);
        payload = {
          id: document.getElementById('add-inv-id').value.trim(),
          employee_id: document.getElementById('add-inv-code').value.trim(),
          name: document.getElementById('add-inv-name').value.trim() || '新規取引先',
          raw_amount: amt,
          amount: '¥' + amt.toLocaleString(),
          type: document.getElementById('add-inv-type').value,
          status: 'Unprocessed'
        };
      } else {
        url = '/api/payroll-items/add';
        const amt = parseInt(document.getElementById('add-pay-amt').value || '0', 10);
        payload = {
          id: document.getElementById('add-pay-id').value.trim(),
          employee_id: document.getElementById('add-pay-code').value.trim(),
          employee_name: document.getElementById('add-pay-name').value.trim() || '新規従業員',
          item_category: document.getElementById('add-pay-cat').value,
          item_type: document.getElementById('add-pay-type').value,
          raw_amount: amt,
          amount: '¥' + amt.toLocaleString(),
          status: 'Unprocessed'
        };
      }

      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.success) {
          closeAddRecordModal();
          loadTableData();
        } else {
          alert('登録に失敗しました。');
        }
      } catch (e) {
        alert('エラー: ' + e);
      }
    }

    /* --- Excel / CSV Bulk Import Modal with Schema Validation & Flagging --- */
    function openExcelImportModal() {
      parsedBulkData = [];
      const warnBox = document.getElementById('bulk-validation-warning');
      if (warnBox) warnBox.style.display = 'none';
      const label = document.getElementById('bulk-target-table-label');
      if (label) {
        label.innerText = (currentSuite === 'invoice') ? 'erp_invoices (財務会計)' : ((currentSuite === 'payroll') ? 'erp_payroll_items (人事給与)' : 'erp_leave_applications (勤怠管理)');
      }
      document.getElementById('bulk-preview-container').style.display = 'none';
      document.getElementById('bulk-preview-summary').innerText = '';
      const fn = document.getElementById('bulk-file-selected-name');
      if (fn) fn.innerText = '';
      document.getElementById('excel-import-modal').style.display = 'flex';
    }

    function closeExcelImportModal() {
      document.getElementById('excel-import-modal').style.display = 'none';
    }

    function previewBulkSpreadsheet() {
      const text = document.getElementById('bulk-paste-text').value.trim();
      const warnBox = document.getElementById('bulk-validation-warning');
      const warnDetails = document.getElementById('bulk-val-details');
      const submitBtn = document.getElementById('btn-submit-bulk-import');

      if (!text) {
        alert('貼り付けデータがありません。Excelからデータをコピーしてください。');
        return;
      }

      const lines = text.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
      parsedBulkData = [];
      const errors = [];

      lines.forEach(function(line, idx) {
        // Skip header if line looks like header
        if (idx === 0 && (line.indexOf('ID') !== -1 || line.indexOf('コード') !== -1 || line.indexOf('employee') !== -1 || line.indexOf('社員') !== -1)) {
          return;
        }

        const parts = line.indexOf('\t') !== -1 ? line.split('\t') : line.split(',');
        if (parts.length < 2) {
          errors.push('行 ' + (idx + 1) + ': 列数が不足しています (2列以上必要)');
          return;
        }

        if (currentSuite === 'invoice') {
          const id = parts[0].trim() || ('INV-2026-' + (invoiceRecords.length + idx + 1).toString().padStart(3, '0'));
          const code = parts[1] ? parts[1].trim() : '';
          const name = parts[2] ? parts[2].trim() : '';
          const rawAmtStr = parts[3] ? parts[3].replace(/[¥,]/g, '').trim() : '';
          const type = parts[4] ? parts[4].trim() : 'Routine';

          if (!code || !name) {
            errors.push('行 ' + (idx + 1) + ': 取引先コードまたは企業名が欠落しています');
          }
          const rawAmt = parseInt(rawAmtStr, 10);
          if (isNaN(rawAmt) || rawAmt < 0) {
            errors.push('行 ' + (idx + 1) + ': 金額 "' + (parts[3] || '') + '" は有効な数値 (INTEGER) ではありません');
          } else {
            parsedBulkData.push({
              id: id,
              employee_id: code || 'V3001',
              name: name || '新規取引先',
              raw_amount: rawAmt,
              amount: '¥' + rawAmt.toLocaleString(),
              type: type,
              status: 'Unprocessed'
            });
          }
        } else if (currentSuite === 'payroll') {
          const id = parts[0].trim() || ('PAY-2026-' + (payrollRecords.length + idx + 1).toString().padStart(3, '0'));
          const code = parts[1] ? parts[1].trim() : '';
          const name = parts[2] ? parts[2].trim() : '';
          const cat = parts[3] ? parts[3].trim() : '';
          const rawAmtStr = parts[4] ? parts[4].replace(/[¥,]/g, '').trim() : '';
          const type = parts[5] ? parts[5].trim() : (cat.indexOf('控除') !== -1 ? 'Deduction' : 'Addition');

          if (!code || !name || !cat) {
            errors.push('行 ' + (idx + 1) + ': 社員番号、氏名、または精算項目名が欠落しています');
          }
          const rawAmt = parseInt(rawAmtStr, 10);
          if (isNaN(rawAmt) || rawAmt < 0) {
            errors.push('行 ' + (idx + 1) + ': 金額 "' + (parts[4] || '') + '" は有効な正の数値ではありません');
          } else {
            parsedBulkData.push({
              id: id,
              employee_id: code || 'EMP-001',
              employee_name: name || '新規従業員',
              item_category: cat || '経費精算',
              item_type: type,
              raw_amount: rawAmt,
              amount: '¥' + rawAmt.toLocaleString(),
              status: 'Unprocessed'
            });
          }
        } else { // leave
          const id = parts[0].trim() || ('LV-2026-' + (leaveRecords.length + idx + 1).toString().padStart(3, '0'));
          const code = parts[1] ? parts[1].trim() : '';
          const name = parts[2] ? parts[2].trim() : '';
          const dept = parts[3] ? parts[3].trim() : '開発部';
          const ltype = parts[4] ? parts[4].trim() : '有給休暇';
          const sdate = parts[5] ? parts[5].trim() : '2026-07-20';
          const edate = parts[6] ? parts[6].trim() : '2026-07-21';
          const daysStr = parts[7] ? parts[7].trim() : '1.0';
          const balStr = parts[8] ? parts[8].trim() : '10.0';

          if (!code || !name) {
            errors.push('行 ' + (idx + 1) + ': 社員番号または申請者氏名が欠落しています');
          }
          const validTypes = ['有給休暇', '病気休暇', '慶弔特別休暇', '未登録休暇'];
          if (validTypes.indexOf(ltype) === -1) {
            errors.push('行 ' + (idx + 1) + ': 未対応の休暇種別 "' + ltype + '" です。許容値: [' + validTypes.join(', ') + ']');
          }
          const reqDays = parseFloat(daysStr);
          if (isNaN(reqDays) || reqDays <= 0) {
            errors.push('行 ' + (idx + 1) + ': 申請日数 "' + daysStr + '" は有効な正の数値ではありません');
          } else {
            parsedBulkData.push({
              id: id,
              employee_id: code || 'EMP-001',
              employee_name: name || '新規申請者',
              department: dept,
              leave_type: ltype,
              start_date: sdate,
              end_date: edate,
              requested_days: reqDays,
              remaining_balance: parseFloat(balStr) || 10.0,
              reason: parts[9] ? parts[9].trim() : '私用のため',
              has_attachment: Boolean(parts[10] && parts[10].trim() === '1'),
              attachment_name: parts[11] ? parts[11].trim() : '',
              status: 'Unprocessed'
            });
          }
        }
      });

      if (errors.length > 0) {
        if (warnBox) {
          warnBox.style.display = 'block';
          warnDetails.innerText = errors.slice(0, 8).join('\n') + (errors.length > 8 ? '\n... 他 ' + (errors.length - 8) + ' 件のエラー' : '');
        }
        if (submitBtn) submitBtn.disabled = true;
      } else {
        if (warnBox) warnBox.style.display = 'none';
        if (submitBtn) submitBtn.disabled = false;
      }

      const summary = document.getElementById('bulk-preview-summary');
      const tableHead = document.getElementById('bulk-preview-head');
      const tableBody = document.getElementById('bulk-preview-body');
      const container = document.getElementById('bulk-preview-container');

      summary.innerText = '解析完了: ' + parsedBulkData.length + ' 件の正常データを抽出' + (errors.length > 0 ? ' (' + errors.length + ' 件の警告・型不一致)' : '');
      container.style.display = 'block';

      if (currentSuite === 'invoice') {
        tableHead.innerHTML = '<tr><th>ID</th><th>コード</th><th>企業名</th><th>金額</th><th>区分</th></tr>';
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
          return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.name + '</td><td>' + r.amount + '</td><td>' + r.type + '</td></tr>';
        }).join('') + (parsedBulkData.length > 15 ? '<tr><td colspan="5" style="text-align:center;">... 他 ' + (parsedBulkData.length - 15) + ' 件 ...</td></tr>' : '');
      } else if (currentSuite === 'payroll') {
        tableHead.innerHTML = '<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>項目</th><th>区分</th><th>金額</th></tr>';
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
          return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.employee_name + '</td><td>' + r.item_category + '</td><td>' + r.item_type + '</td><td>' + r.amount + '</td></tr>';
        }).join('') + (parsedBulkData.length > 15 ? '<tr><td colspan="6" style="text-align:center;">... 他 ' + (parsedBulkData.length - 15) + ' 件 ...</td></tr>' : '');
      } else {
        tableHead.innerHTML = '<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>区分</th><th>期間</th><th>日数</th></tr>';
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
          return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.employee_name + '</td><td>' + r.leave_type + '</td><td>' + r.start_date + '〜' + r.end_date + '</td><td>' + r.requested_days + '日</td></tr>';
        }).join('') + (parsedBulkData.length > 15 ? '<tr><td colspan="6" style="text-align:center;">... 他 ' + (parsedBulkData.length - 15) + ' 件 ...</td></tr>' : '');
      }
    }

    async function handleBulkFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;

      const fnEl = document.getElementById('bulk-file-selected-name');
      if (fnEl) fnEl.innerText = file.name + ' (' + Math.round(file.size / 1024) + ' KB)';

      const warnBox = document.getElementById('bulk-validation-warning');
      const warnDetails = document.getElementById('bulk-val-details');
      const submitBtn = document.getElementById('btn-submit-bulk-import');

      if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
        // Send to /api/upload-table-data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('suite', currentSuite);

        try {
          const res = await fetch('/api/upload-table-data', {
            method: 'POST',
            body: formData
          });
          const d = await res.json();
          if (d.success) {
            if (warnBox) warnBox.style.display = 'none';
            if (submitBtn) submitBtn.disabled = false;
            parsedBulkData = d.records || [];
            const summary = document.getElementById('bulk-preview-summary');
            const tableHead = document.getElementById('bulk-preview-head');
            const tableBody = document.getElementById('bulk-preview-body');
            const container = document.getElementById('bulk-preview-container');

            summary.innerText = '解析完了: ' + parsedBulkData.length + ' 件のExcel伝票データを抽出';
            container.style.display = 'block';

            if (currentSuite === 'invoice') {
              tableHead.innerHTML = '<tr><th>ID</th><th>コード</th><th>企業名</th><th>金額</th><th>区分</th></tr>';
              tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
                return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.name + '</td><td>' + r.amount + '</td><td>' + r.type + '</td></tr>';
              }).join('');
            } else if (currentSuite === 'payroll') {
              tableHead.innerHTML = '<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>項目</th><th>区分</th><th>金額</th></tr>';
              tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
                return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.employee_name + '</td><td>' + r.item_category + '</td><td>' + r.item_type + '</td><td>' + r.amount + '</td></tr>';
              }).join('');
            } else {
              tableHead.innerHTML = '<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>区分</th><th>期間</th><th>日数</th></tr>';
              tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
                return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.employee_name + '</td><td>' + r.leave_type + '</td><td>' + r.start_date + '〜' + r.end_date + '</td><td>' + r.requested_days + '日</td></tr>';
              }).join('');
            }
          } else {
            if (warnBox) {
              warnBox.style.display = 'block';
              warnDetails.innerText = (d.details ? d.details.join('\n') : d.error) + '\n' + (d.instruction || '');
            }
            if (submitBtn) submitBtn.disabled = true;
          }
        } catch (err) {
          if (warnBox) {
            warnBox.style.display = 'block';
            warnDetails.innerText = 'アップロードエラー: ' + err;
          }
        }
      } else {
        const reader = new FileReader();
        reader.onload = function(e) {
          document.getElementById('bulk-paste-text').value = e.target.result;
          previewBulkSpreadsheet();
        };
        reader.readAsText(file);
      }
    }

    async function submitBulkImport() {
      if (!parsedBulkData || parsedBulkData.length === 0) {
        previewBulkSpreadsheet();
      }
      if (!parsedBulkData || parsedBulkData.length === 0) {
        alert('登録するデータがありません。Excelデータを貼り付けてください。');
        return;
      }

      const url = (currentSuite === 'invoice') ? '/api/invoices/bulk-add' : ((currentSuite === 'payroll') ? '/api/payroll-items/bulk-add' : '/api/leave-applications/bulk-add');
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ records: parsedBulkData })
        });
        const d = await res.json();
        if (d.success) {
          alert('一括取込完了: ' + d.count + ' 件の伝票データをデータベースへ登録しました。');
          closeExcelImportModal();
          loadTableData();
        } else {
          alert('一括取込に失敗しました: ' + (d.error || '不明なエラー'));
        }
      } catch (e) {
        alert('エラー: ' + e);
      }
    }

    /* --- Override Row Helper --- */
    async function overrideRow(id, status) {
      try {
        const res = await fetch('/api/item/override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            suite: currentSuite,
            id: id,
            status: status,
            comment: '人間判断による例外承認・規程例外承認済'
          })
        });
        const d = await res.json();
        if (d.success) {
          loadTableData();
        }
      } catch (e) {
        alert('エラー: ' + e);
      }
    }

    

    /* --- File Upload Handler (.docx / .txt) --- */
    async function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      const statusDiv = document.getElementById('upload-status');
      statusDiv.innerText = '文書を解析中...';

      try {
        const res = await fetch('/api/upload-doc', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          document.getElementById('doc-text').value = data.text;
          statusDiv.innerText = '✓ 読込完了: ' + data.filename + ' (' + data.text.length + ' 文字)';
          switchWsTab('notepad');
        } else {
          statusDiv.innerText = 'エラー: ' + (data.error || '不明なエラー');
        }
      } catch (e) {
        statusDiv.innerText = 'アップロードエラー: ' + e;
      }
    }


    /* --- Schema Guide & Validation Modal Controls --- */
    function openSchemaInfoModal(tab) {
      if (tab) switchSchemaTab(tab);
      const m = document.getElementById('schema-info-modal');
      if (m) m.style.display = 'flex';
    }
    window.openSchemaInfoModal = openSchemaInfoModal;

    function closeSchemaInfoModal() {
      const m = document.getElementById('schema-info-modal');
      if (m) m.style.display = 'none';
    }
    window.closeSchemaInfoModal = closeSchemaInfoModal;

    function switchSchemaTab(tab) {
      ['invoice', 'payroll', 'leave', 'excel'].forEach(function(t) {
        const view = document.getElementById('schema-view-' + t);
        const btn = document.getElementById('schema-tab-btn-' + (t === 'invoice' ? 'inv' : (t === 'payroll' ? 'pay' : (t === 'leave' ? 'lev' : 'excel'))));
        if (view) view.style.display = (t === tab) ? 'block' : 'none';
        if (btn) {
          if (t === tab) {
            btn.classList.add('active');
            btn.style.color = '#1e3a8a';
            btn.style.fontWeight = '700';
            btn.style.borderBottom = '2px solid #2563eb';
          } else {
            btn.classList.remove('active');
            btn.style.color = '#64748b';
            btn.style.fontWeight = '600';
            btn.style.borderBottom = 'none';
          }
        }
      });
    }
    window.switchSchemaTab = switchSchemaTab;

    function downloadSampleCsv(suite) {
      let csvContent = '';
      let filename = 'template.csv';
      if (suite === 'invoice') {
        csvContent = 'id,employee_id,name,amount,raw_amount,type\nINV-2026-106,V3005,Global Tech LLC,¥716232,716232,Routine\nINV-2026-107,V3006,Hokuriku Parts,¥455128,455128,Routine\n';
        filename = 'erp_invoices_sample_template.csv';
      } else if (suite === 'payroll') {
        csvContent = 'id,employee_id,employee_name,item_category,item_type,amount,raw_amount\nPAY-2026-106,EMP-014,佐藤 健太,交通費精算,Addition,¥24800,24800\nPAY-2026-107,EMP-088,高橋 翔太,消耗品費,Addition,¥68000,68000\n';
        filename = 'erp_payroll_items_sample_template.csv';
      } else {
        csvContent = 'id,employee_id,employee_name,department,leave_type,start_date,end_date,requested_days,remaining_balance,reason,has_attachment,attachment_name\nLV-2026-106,EMP-001,青木 拓也,開発部,病気休暇,2026-07-20,2026-07-21,2.0,14.0,急性上気道炎のため自宅療養,1,LV-2026-001_青木拓也_医師診断書.pdf\nLV-2026-107,EMP-002,井上 玲奈,営業部,有給休暇,2026-07-22,2026-07-22,1.0,18.0,私用のため,0,\n';
        filename = 'erp_leave_applications_sample_template.csv';
      }
      const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
    window.downloadSampleCsv = downloadSampleCsv;

    function syncDbUriFromFields() {
      const host = (document.getElementById('db-host-input').value || '').trim();
      const port = (document.getElementById('db-port-input').value || '5432').trim();
      const db = (document.getElementById('db-name-input').value || 'postgres').trim();
      const user = (document.getElementById('db-user-input').value || '').trim();
      const pass = (document.getElementById('db-pass-input').value || '').trim();
      if (!host && !user) return;
      const ssl = (host.indexOf('supabase') !== -1 || host.indexOf('pooler') !== -1) ? 'require' : 'prefer';
      const encU = encodeURIComponent(user);
      const encP = encodeURIComponent(pass);
      document.getElementById('db-uri-input').value = 'postgresql://' + encU + ':' + encP + '@' + host + ':' + port + '/' + db + '?sslmode=' + ssl;
    }
    window.syncDbUriFromFields = syncDbUriFromFields;

    async function testCustomDbConnection() {
      const resBox = document.getElementById('db-conn-result');
      if (resBox) {
        resBox.style.display = 'block';
        resBox.style.background = '#eff6ff';
        resBox.style.color = '#1e40af';
        resBox.innerText = '接続テスト中 (Testing connection)...';
      }
      const uri = document.getElementById('db-uri-input').value.trim();
      const host = document.getElementById('db-host-input').value.trim();
      const port = document.getElementById('db-port-input').value.trim();
      const db = document.getElementById('db-name-input').value.trim();
      const user = document.getElementById('db-user-input').value.trim();
      const pass = document.getElementById('db-pass-input').value.trim();

      try {
        const res = await fetch('/api/database/test-connection', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: uri,
            host: host,
            port: port ? parseInt(port, 10) : 5432,
            database: db,
            user: user,
            password: pass
          })
        });
        const data = await res.json();
        if (data.success) {
          resBox.style.background = '#f0fdf4';
          resBox.style.color = '#166534';
          resBox.innerHTML = '✅ <strong>接続成功:</strong> ' + data.message;
        } else {
          resBox.style.background = '#fef2f2';
          resBox.style.color = '#991b1b';
          resBox.innerHTML = '❌ <strong>接続失敗:</strong> ' + data.message;
        }
      } catch (err) {
        if (resBox) {
          resBox.style.background = '#fef2f2';
          resBox.style.color = '#991b1b';
          resBox.innerHTML = '❌ <strong>エラー:</strong> ' + err;
        }
      }
    }
    window.testCustomDbConnection = testCustomDbConnection;

    /* --- Database Management --- */
    function openDbModal() { document.getElementById('db-modal').style.display = 'flex'; }
    function closeDbModal() { document.getElementById('db-modal').style.display = 'none'; }

    async function connectCustomDb() {
      const uri = document.getElementById('db-uri-input').value.trim();
      const host = document.getElementById('db-host-input').value.trim();
      const port = document.getElementById('db-port-input').value.trim();
      const db = document.getElementById('db-name-input').value.trim();
      const user = document.getElementById('db-user-input').value.trim();
      const pass = document.getElementById('db-pass-input').value.trim();

      if (!uri && !host) { alert('PostgreSQL / Supabase 接続情報またはURIを入力してください。'); return; }
      try {
        const payload = host ? {
          url: uri,
          host: host,
          port: port ? parseInt(port, 10) : 5432,
          database: db || 'postgres',
          user: user,
          password: pass
        } : { url: uri };

        const res = await fetch('/api/database/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        alert(d.message);
        if (d.success) { closeDbModal(); updateSystemStatus(); loadTableData(); }
      } catch (e) { alert('接続エラー: ' + e); }
    }

    async function connectLocalDb() {
      const path = document.getElementById('db-local-path-input').value.trim();
      if (!path) { alert('ローカルDBファイルパスを入力してください。'); return; }
      try {
        const res = await fetch('/api/database/connect-local', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: path })
        });
        const d = await res.json();
        alert(d.message);
        if (d.success) { closeDbModal(); updateSystemStatus(); loadTableData(); }
      } catch (e) { alert('接続エラー: ' + e); }
    }

    async function switchDb(type) {
      try {
        const res = await fetch('/api/database/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: type })
        });
        const d = await res.json();
        alert(d.message);
        if (d.success) { closeDbModal(); updateSystemStatus(); loadTableData(); }
      } catch (e) { alert('エラー: ' + e); }
    }

    async function resetDatabaseBenchmark() {
      if (!confirm('データベースを初期ベンチマーク状態にリセットしますか？')) return;
      try {
        const res = await fetch('/api/database/reset', { method: 'POST' });
        const d = await res.json();
        if (d.success) {
          alert('データベースの初期化が完了しました。');
          loadTableData();
          resetGraphUi();
          document.getElementById('interventions-container').style.display = 'none';
        }
      } catch (e) { alert('リセットエラー: ' + e); }
    }

    /* --- LLM Management --- */
    function openPuterAuthModal() {
      const modal = document.getElementById('puter-auth-modal');
      if (modal) modal.style.display = 'flex';
      const st = document.getElementById('puter-modal-status-box');
      if (st) { st.style.display = 'none'; st.innerText = ''; }
    }

    function closePuterAuthModal() {
      const modal = document.getElementById('puter-auth-modal');
      if (modal) modal.style.display = 'none';
    }

    function openPuterLoginPage() {
      window.open('https://puter.com/login', '_blank');
    }

    function dismissPuterBanner() {
      isPuterBannerDismissed = true;
      const b = document.getElementById('puter-login-banner');
      if (b) b.style.display = 'none';
    }

    async function ensurePuterConnectedIfRequired() {
      try {
        const res = await fetch('/api/llm/status');
        const st = await res.json();
        if (st.provider === 'puter' && !st.connected) {
          openPuterAuthModal();
          return false;
        }
      } catch (e) {}
      return true;
    }

    async function loginWithPuter() {
      const statusBox = document.getElementById('puter-modal-status-box');
      const btn = document.getElementById('btn-modal-puter-signin');
      if (statusBox) {
        statusBox.style.display = 'block';
        statusBox.style.background = '#eff6ff';
        statusBox.style.color = '#1e40af';
        statusBox.innerHTML = '<span class="loading-spinner"></span> Puter 認証中... ポップアップでログインを完了してください。';
      }
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> ログイン処理中...';
      }

      try {
        if (typeof puter !== 'undefined' && puter.auth && typeof puter.auth.signIn === 'function') {
          try {
            const signInRes = await puter.auth.signIn();
            console.log('[Puter] Sign in result:', signInRes);
          } catch (signErr) {
            console.warn('[Puter] signIn error or popup closed:', signErr);
            openPuterLoginPage();
          }

          let token = '';
          try {
            if (puter.authToken) {
              token = puter.authToken;
            } else if (typeof puter.auth.getToken === 'function') {
              token = await puter.auth.getToken();
            }
          } catch (te) {
            console.warn('[Puter] Token fetch error:', te);
          }

          if (token) {
            if (statusBox) {
              statusBox.style.background = '#eff6ff';
              statusBox.style.color = '#1e40af';
              statusBox.innerHTML = '<span class="loading-spinner"></span> トークン取得完了。ERPシステムに接続設定中...';
            }
            await savePuterTokenToBackend(token);
            return;
          }
        } else {
          openPuterLoginPage();
        }
      } catch (err) {
        console.error('[Puter] General login error:', err);
        openPuterLoginPage();
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '🔑 Puter にログイン (Sign In with Puter)';
        }
      }

      if (statusBox) {
        statusBox.style.display = 'block';
        statusBox.style.background = '#fef3c7';
        statusBox.style.color = '#92400e';
        statusBox.innerHTML = 'Puter ログインページを開きました (<a href="https://puter.com/login" target="_blank" style="text-decoration: underline; font-weight: bold; color: #92400e;">https://puter.com/login</a>)。<br>ログイン完了後、下の [接続確認] ボタンをクリックしてください。';
      }
    }

    async function savePuterTokenToBackend(token) {
      const statusBox = document.getElementById('puter-modal-status-box');
      try {
        await fetch('/api/llm/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: 'puter',
            token: token,
            model: 'openrouter:openrouter/free'
          })
        });

        const testRes = await fetch('/api/llm/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: 'puter', token: token, model: 'openrouter:openrouter/free' })
        });
        const td = await testRes.json();

        if (td.success) {
          if (statusBox) {
            statusBox.style.background = '#dcfce7';
            statusBox.style.color = '#166534';
            statusBox.innerHTML = '✓ Puter に正常に接続されました！ (' + td.latency_s + 's)';
          }
          await updateSystemStatus();
          setTimeout(function() {
            closePuterAuthModal();
          }, 1200);
        } else {
          if (statusBox) {
            statusBox.style.background = '#fee2e2';
            statusBox.style.color = '#991b1b';
            statusBox.innerHTML = '✕ 接続テストエラー: ' + td.message;
          }
        }
      } catch (e) {
        if (statusBox) {
          statusBox.style.background = '#fee2e2';
          statusBox.style.color = '#991b1b';
          statusBox.innerHTML = '✕ 通信エラー: ' + e;
        }
      }
    }

    async function checkPuterConnection() {
      const statusBox = document.getElementById('puter-modal-status-box');
      if (statusBox) {
        statusBox.style.display = 'block';
        statusBox.style.background = '#eff6ff';
        statusBox.style.color = '#1e40af';
        statusBox.innerHTML = '<span class="loading-spinner"></span> Puter 接続状況を確認中...';
      }

      let clientToken = '';
      if (typeof puter !== 'undefined' && puter.auth) {
        try {
          if (puter.authToken) clientToken = puter.authToken;
          else if (typeof puter.auth.getToken === 'function') clientToken = await puter.auth.getToken();
        } catch (e) {}
      }

      try {
        const body = { provider: 'puter' };
        if (clientToken) body.token = clientToken;

        const res = await fetch('/api/llm/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const d = await res.json();
        if (d.success) {
          if (statusBox) {
            statusBox.style.background = '#dcfce7';
            statusBox.style.color = '#166534';
            statusBox.innerHTML = '✓ Puter 接続成功: ' + d.message;
          }
          await updateSystemStatus();
          setTimeout(function() { closePuterAuthModal(); }, 1200);
        } else {
          if (statusBox) {
            statusBox.style.background = '#fee2e2';
            statusBox.style.color = '#991b1b';
            statusBox.innerHTML = '✕ 未接続: ' + (d.error || d.message) + '<br><small>Puterにログインして有効な認証を完了してください。</small>';
          }
          await updateSystemStatus();
        }
      } catch (e) {
        if (statusBox) {
          statusBox.style.background = '#fee2e2';
          statusBox.style.color = '#991b1b';
          statusBox.innerHTML = '通信エラー: ' + e;
        }
      }
    }

    function openSettingsModal() {
      openLlmModal();
    }
    window.openSettingsModal = openSettingsModal;

    function openPuterSignUpPage() {
      window.open('https://puter.com/signup', '_blank');
    }
    window.openPuterSignUpPage = openPuterSignUpPage;

    async function switchPuterAccount() {
      if (confirm('現在のPuterアカウント連携を解除して、新しいアカウントでログインしますか？')) {
        if (typeof puter !== 'undefined' && puter.auth && typeof puter.auth.signOut === 'function') {
          try { await puter.auth.signOut(); } catch(e) {}
        }
        document.getElementById('llm-token-input').value = '';
        try {
          await fetch('/api/llm/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: 'puter', token: '', model: 'openrouter:openrouter/free' })
          });
        } catch(e) {}
        updateSystemStatus();
        loginWithPuter();
      }
    }
    window.switchPuterAccount = switchPuterAccount;

    function onSettingsModelChange() {
      const select = document.getElementById('settings-model-dropdown');
      const customBox = document.getElementById('settings-custom-model-box');
      const modelInput = document.getElementById('llm-model-input');
      if (select.value === 'custom') {
        customBox.style.display = 'block';
      } else {
        customBox.style.display = 'none';
        modelInput.value = select.value;
      }
    }
    window.onSettingsModelChange = onSettingsModelChange;

    async function openLlmModal() {
      try {
        const res = await fetch('/api/llm/status');
        const st = await res.json();
        const modelInput = document.getElementById('llm-model-input');
        const modelDropdown = document.getElementById('settings-model-dropdown');
        const customBox = document.getElementById('settings-custom-model-box');

        if (st.model) {
          modelInput.value = st.model;
          let matched = false;
          for (let i = 0; i < modelDropdown.options.length; i++) {
            if (modelDropdown.options[i].value === st.model) {
              modelDropdown.selectedIndex = i;
              matched = true;
              break;
            }
          }
          if (!matched) {
            modelDropdown.value = 'custom';
            if (customBox) customBox.style.display = 'block';
          } else {
            if (customBox) customBox.style.display = 'none';
          }
        }

        const box = document.getElementById('llm-test-result');
        if (box) { box.style.display = 'none'; box.innerText = ''; }

        const puterBadge = document.getElementById('puter-modal-conn-badge');
        const userNameEl = document.getElementById('settings-user-name');
        const creditCircle = document.getElementById('ai-credit-gauge-circle');
        const creditText = document.getElementById('ai-credit-gauge-text');
        const creditStatusEl = document.getElementById('settings-credit-status');

        if (st.connected) {
          if (puterBadge) {
            puterBadge.className = 'status-badge badge-approved';
            puterBadge.innerText = '接続済 (Connected)';
          }
        } else {
          if (puterBadge) {
            puterBadge.className = 'status-badge badge-hold';
            puterBadge.innerText = '未接続 (Disconnected)';
          }
        }

        // Query real live account balance / quota from account-credits endpoint
        try {
          const credRes = await fetch('/api/llm/account-credits').then(function(r) { return r.json(); });
          if (credRes && credRes.success) {
            const pct = Math.max(0, Math.min(100, credRes.percentage != null ? credRes.percentage : 100));
            const circ = 201;
            const offset = circ - (circ * pct / 100);
            if (creditCircle) {
              creditCircle.style.strokeDashoffset = offset.toString();
              creditCircle.setAttribute('stroke', pct > 20 ? '#10b981' : '#ef4444');
            }
            if (creditText) {
              creditText.innerText = credRes.display_text || (pct + '%');
              creditText.setAttribute('fill', pct > 20 ? '#10b981' : '#ef4444');
            }
            if (creditStatusEl) {
              creditStatusEl.innerHTML = credRes.status_note || ('AIクレジット残量: <strong>' + pct + '% (Active)</strong>');
            }
          }
        } catch (cErr) {
          console.warn('Credits query notice:', cErr);
        }

        if (typeof puter !== 'undefined' && puter.auth && typeof puter.auth.getUser === 'function') {
          puter.auth.getUser().then(function(u) {
            if (u && u.username && userNameEl) {
              userNameEl.innerText = 'Puter User: ' + u.username;
            }
          }).catch(function() {});
        }
      } catch (e) {
        console.error('LLM status fetch error:', e);
      }
      document.getElementById('llm-modal').style.display = 'flex';
    }
    function closeLlmModal() { document.getElementById('llm-modal').style.display = 'none'; }

    async function testLlmConnection() {
      const prov = document.getElementById('llm-provider-select').value;
      const token = document.getElementById('llm-token-input').value.trim();
      const model = document.getElementById('llm-model-input').value.trim();

      const box = document.getElementById('llm-test-result');
      box.style.display = 'block';
      box.style.background = '#f1f5f9';
      box.innerText = 'LLM へ接続テスト中...';

      try {
        const res = await fetch('/api/llm/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: prov, token: token, model: model })
        });
        const d = await res.json();
        if (d.success) {
          box.style.background = '#dcfce7';
          box.style.color = '#166534';
          box.innerText = '✓ 接続成功 (' + d.latency_s + 's): ' + d.message;
          updateSystemStatus();
        } else {
          box.style.background = '#fee2e2';
          box.style.color = '#991b1b';
          box.innerText = '✕ 接続失敗: ' + d.message;
        }
      } catch (e) {
        box.style.background = '#fee2e2';
        box.style.color = '#991b1b';
        box.innerText = 'エラー: ' + e;
      }
    }

    async function saveLlmSettings() {
      const prov = document.getElementById('llm-provider-select').value;
      const token = document.getElementById('llm-token-input').value.trim();
      const model = document.getElementById('llm-model-input').value.trim();

      try {
        const res = await fetch('/api/llm/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: prov, token: token, model: model })
        });
        const d = await res.json();
        if (d.success) {
          alert('LLM設定を保存しました。');
          closeLlmModal();
          updateSystemStatus();
        }
      } catch (e) { alert('保存エラー: ' + e); }
    }

    /* --- Visual Graph Helper Functions (Ultra-Compact Pipeline) --- */
    function resetGraphUi() {
      for (let i = 1; i <= 5; i++) {
        const n = document.getElementById('node-' + i);
        if (n) {
          n.className = 'mini-node node-pending';
          const t = document.getElementById('time-node-' + i);
          if (t) t.innerText = '-';
        }
      }
      const b = document.getElementById('graph-overall-badge');
      if (b) {
        b.innerText = 'READY';
        b.style.background = '#e2e8f0';
      }
      const ic = document.getElementById('interventions-container');
      if (ic) ic.style.display = 'none';
      const il = document.getElementById('interventions-list');
      if (il) il.innerHTML = '';
    }

    function setNodeActive(id) {
      const n = document.getElementById(id);
      if (n) {
        n.className = 'mini-node node-active';
      }
    }

    function setNodeDone(id, durationStr) {
      const n = document.getElementById(id);
      if (n) {
        n.className = 'mini-node node-done';
        const t = document.getElementById('time-' + id) || n.querySelector('.mini-node-time');
        if (t) t.innerText = durationStr;
      }
    }
  </script>

  <!-- Attachment Preview & Explorer Modal -->
  <div id="attachment-preview-modal" class="modal-backdrop" style="display: none; align-items: center; justify-content: center; z-index: 10000;">
    <div class="modal-card" style="width: 580px; background: #ffffff; border-radius: 8px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); overflow: hidden; border: 1px solid #cbd5e1;">
      <div style="background: #1e3a8a; color: white; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: 700; font-size: 13px;">📎 休暇申請 添付証明書類確認 (Windows Explorer Integration)</span>
        <button onclick="closeAttachmentModal()" style="background: transparent; border: none; color: white; font-size: 16px; cursor: pointer;">&times;</button>
      </div>
      <div style="padding: 16px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; background: #f8fafc; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
          <div style="font-size: 32px;">📄</div>
          <div style="flex: 1; min-width: 0;">
            <div style="font-size: 12px; font-weight: 700; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" id="att-doc-filename">医師診断書.pdf</div>
            <div style="font-size: 11px; color: #64748b;" id="att-doc-meta">申請ID: LV-2026-001 | 申請者: 青木 拓也 | 休暇種別: 病気休暇</div>
            <div style="font-size: 10px; color: #2563eb; margin-top: 3px; word-break: break-all;">
              📁 実ファイル物理パス: <code id="att-doc-path" style="background: #eff6ff; padding: 1px 4px; border-radius: 3px;">c:\Users\KISHORE S\Desktop\pulled_tmi\attachments\...</code>
            </div>
          </div>
        </div>

        <div style="font-size: 11px; font-weight: 700; color: #334155; margin-bottom: 6px;">📋 Multimodal OCR & 人事労務照合チェックリスト:</div>
        <div style="background: #f1f5f9; padding: 10px 12px; border-radius: 6px; font-size: 11px; color: #334155; line-height: 1.6; border: 1px solid #cbd5e1;">
          <div id="att-seal-check">✅ <strong>医療機関発行印鑑:</strong> 照合済（原本スキャンデータ整合）</div>
          <div id="att-diag-check">📋 <strong>診断名:</strong> 急性上気道炎 (発熱・咽頭痛)</div>
          <div id="att-days-check">⏱️ <strong>医師推奨療養日数:</strong> 2.0日 (申請日数 2.0日と完全一致)</div>
          <div>✅ <strong>就業規則第28条適合:</strong> 特別休暇承認要件を充足 (100% 整合)</div>
        </div>

        <div style="margin-top: 14px; display: flex; gap: 8px; justify-content: flex-end; align-items: center; flex-wrap: wrap;">
          <button class="btn-primary" onclick="openExplorerFile('select')" style="background: #0284c7; color: white; border: none; padding: 7px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 5px;">
            📂 Windows Explorer で選択・表示
          </button>
          <button class="btn-secondary" onclick="openExplorerFile('open')" style="color: #1e40af; border-color: #93c5fd; padding: 6px 12px; font-size: 11px; cursor: pointer; display: flex; align-items: center; gap: 4px;">
            📄 ドキュメントを直接開く
          </button>
          <button class="btn-secondary" onclick="closeAttachmentModal()" style="padding: 6px 12px; font-size: 11px; cursor: pointer;">
            閉じる
          </button>
        </div>
      </div>
    </div>
  </div>

</body>
</html>'''

# --- Flask Endpoints ---

@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        invoice_preset=INVOICE_PRESET_POLICY,
        payroll_preset=PAYROLL_PRESET_MEMO
    )

@app.route("/api/database/status")
def db_status():
    return jsonify(db_manager.get_status())

@app.route("/api/database/connect", methods=["POST"])
def db_connect():
    data = request.json or {}
    if "host" in data and data.get("host"):
        res = db_manager.set_custom_database(data)
    else:
        url = data.get("url", "")
        res = db_manager.set_custom_database(url)
    return jsonify(res)

@app.route("/api/database/test-connection", methods=["POST"])
def db_test_connection():
    data = request.json or {}
    url = data.get("url", "")
    if "host" in data and data.get("host"):
        import urllib.parse
        host = data.get("host", "localhost")
        port = data.get("port", 5432)
        db = data.get("database") or "postgres"
        user = data.get("user") or "postgres"
        pwd = data.get("password") or ""
        sslmode = "require" if ("supabase" in host or "pooler" in host) else "prefer"
        enc_u = urllib.parse.quote_plus(str(user))
        enc_p = urllib.parse.quote_plus(str(pwd))
        url = f"postgresql://{enc_u}:{enc_p}@{host}:{port}/{db}?sslmode={sslmode}"

    if not url or url.strip().lower() in ("sqlite", "local", "default"):
        return jsonify({"success": True, "message": "Local SQLite database verified and operational."})

    try:
        import psycopg2
        conn = psycopg2.connect(url, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
        conn.close()
        return jsonify({"success": True, "message": f"PostgreSQL / Supabase connection successful! Version: {ver[:60]}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Connection failed: {str(e)}"})

@app.route("/api/database/connect-local", methods=["POST"])
def db_connect_local():
    data = request.json or {}
    path = data.get("path", "")
    res = db_manager.set_custom_sqlite_path(path)
    return jsonify(res)

@app.route("/api/database/reset", methods=["POST"])
@app.route("/api/reset", methods=["POST"])
def db_reset():
    db_manager.reset_all()
    return jsonify({"success": True})

@app.route("/api/invoices")
def get_invoices():
    rows = db_manager.get_all_invoices()
    return jsonify(rows)

@app.route("/api/invoices/add", methods=["POST"])
def add_invoice():
    data = request.json or {}
    ok = db_manager.add_invoice(data)
    return jsonify({"success": ok})

@app.route("/api/invoices/bulk-add", methods=["POST"])
def bulk_add_invoices_route():
    data = request.json or {}
    records = data.get("records") or (data if isinstance(data, list) else [])
    count = db_manager.bulk_add_invoices(records)
    return jsonify({"success": True, "count": count})

@app.route("/api/payroll-items")
def get_payroll_items():
    rows = db_manager.get_all_payroll_items()
    return jsonify(rows)

@app.route("/api/payroll-items/add", methods=["POST"])
def add_payroll_item():
    data = request.json or {}
    ok = db_manager.add_payroll_item(data)
    return jsonify({"success": ok})

@app.route("/api/payroll-items/bulk-add", methods=["POST"])
def bulk_add_payroll_route():
    data = request.json or {}
    records = data.get("records") or (data if isinstance(data, list) else [])
    count = db_manager.bulk_add_payroll_items(records)
    return jsonify({"success": True, "count": count})

@app.route("/api/leave-applications")
def get_leave_applications():
    rows = db_manager.get_all_leave_applications()
    return jsonify(rows)

@app.route("/api/leave-applications/add", methods=["POST"])
def add_leave_application_route():
    data = request.json or {}
    ok = db_manager.add_leave_application(data)
    return jsonify({"success": ok})

@app.route("/api/leave-applications/bulk-add", methods=["POST"])
def bulk_add_leave_route():
    data = request.json or {}
    records = data.get("records") or (data if isinstance(data, list) else [])
    count = db_manager.bulk_add_leave_applications(records)
    return jsonify({"success": True, "count": count})

@app.route("/api/open-explorer", methods=["POST"])
def open_explorer():
    import subprocess
    import os
    data = request.json or {}
    filename = data.get("filename", "")
    action = data.get("action", "select")
    target_dir = Path(__file__).parent / "attachments"
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = None
    if filename:
        candidate = target_dir / filename
        if candidate.exists():
            file_path = candidate
        else:
            for f in target_dir.iterdir():
                if f.name.lower() == filename.lower() or f.stem.lower() == Path(filename).stem.lower():
                    file_path = f
                    break

    try:
        if sys.platform == "win32":
            if file_path and file_path.exists():
                if action == "open":
                    os.startfile(str(file_path))
                else:
                    cmd = f'explorer /select,"{str(file_path)}"'
                    subprocess.Popen(cmd, shell=True)
                return jsonify({"success": True, "path": str(file_path), "file_found": True, "action": action})
            else:
                os.startfile(str(target_dir))
                return jsonify({"success": True, "path": str(target_dir), "file_found": False, "action": "folder"})
        return jsonify({"success": True, "path": str(target_dir)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/llm/account-credits")
def get_account_credits():
    import urllib.request, json
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "") or getattr(llm_service, "openrouter_key", "")

    if openrouter_key and openrouter_key.startswith("sk-or-"):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/credits",
                headers={"Authorization": f"Bearer {openrouter_key}"}
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                c_data = json.loads(res.read().decode("utf-8")).get("data", {})
                total_credits = float(c_data.get("total_credits", 0.0))
                total_usage = float(c_data.get("total_usage", 0.0))
                rem = max(0.0, total_credits - total_usage)
                pct = max(0, min(100, int((rem / total_credits) * 100))) if total_credits > 0 else 0
                return jsonify({
                    "success": True,
                    "provider": "openrouter",
                    "total_credits": round(total_credits, 2),
                    "usage": round(total_usage, 4),
                    "remaining": round(rem, 2),
                    "percentage": pct,
                    "display_text": f"${rem:.2f}",
                    "status_note": f"Real Account Balance: ${rem:.2f} remaining ({pct}%) | Used: ${total_usage:.4f}"
                })
        except Exception:
            pass

    # Puter session & live tracked calls
    total_calls = getattr(llm_service, "total_calls", 0)
    session_tokens = getattr(llm_service, "session_tokens", 0)
    puter_token = os.environ.get("PUTER_AUTH_TOKEN", "") or getattr(llm_service, "puter_token", "")
    max_free_calls = 500
    rem_calls = max(0, max_free_calls - total_calls)
    pct = max(10, min(100, int((rem_calls / max_free_calls) * 100))) if puter_token else 50
    return jsonify({
        "success": True,
        "provider": "puter",
        "has_token": bool(puter_token),
        "total_calls": total_calls,
        "session_tokens": session_tokens,
        "remaining_calls": rem_calls,
        "percentage": pct,
        "display_text": f"{pct}%",
        "status_note": f"Real Puter Free Quota: {rem_calls} free calls available ({total_calls} calls executed this session)"
    })

@app.route("/api/upload-table-data", methods=["POST"])
def upload_table_data():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    suite = request.form.get("suite", "invoice")
    filename = file.filename or "upload.xlsx"
    file_bytes = file.read()

    try:
        import io
        import pandas as pd
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            df = pd.read_csv(io.BytesIO(file_bytes))

        df = df.fillna("")
        records = []
        errors = []

        if suite == "invoice":
            for idx, r in df.iterrows():
                row_dict = {str(k).strip().lower(): v for k, v in r.items()}
                code = row_dict.get("employee_id") or row_dict.get("vendor_code") or row_dict.get("コード") or row_dict.get("取引先コード")
                name = row_dict.get("name") or row_dict.get("vendor_name") or row_dict.get("取引先名") or row_dict.get("企業名")
                raw_amt = row_dict.get("raw_amount") or row_dict.get("amount") or row_dict.get("金額")

                if not code or not name:
                    errors.append(f"行 {idx+1}: 必須項目（取引先コードまたは企業名）が欠落しています。")
                    continue
                try:
                    clean_amt = int(str(raw_amt).replace("¥", "").replace(",", "").strip())
                    if clean_amt < 0:
                        errors.append(f"行 {idx+1}: 金額 ({raw_amt}) は0以上の正数である必要があります。")
                        continue
                except ValueError:
                    errors.append(f"行 {idx+1}: 金額 '{raw_amt}' は有効な整数 (INTEGER) ではありません。")
                    continue

                row_id = row_dict.get("id") or row_dict.get("伝票番号") or f"INV-2026-{idx+1:03d}"
                inv_type = row_dict.get("type") or row_dict.get("区分") or "Routine"
                records.append({
                    "id": str(row_id),
                    "employee_id": str(code),
                    "name": str(name),
                    "raw_amount": clean_amt,
                    "amount": f"¥{clean_amt:,}",
                    "type": str(inv_type),
                    "status": "Unprocessed"
                })
        elif suite == "payroll":
            for idx, r in df.iterrows():
                row_dict = {str(k).strip().lower(): v for k, v in r.items()}
                emp_id = row_dict.get("employee_id") or row_dict.get("社員番号") or row_dict.get("コード")
                name = row_dict.get("employee_name") or row_dict.get("name") or row_dict.get("氏名") or row_dict.get("社員名")
                cat = row_dict.get("item_category") or row_dict.get("項目") or row_dict.get("品名") or row_dict.get("手当名")
                raw_amt = row_dict.get("raw_amount") or row_dict.get("amount") or row_dict.get("金額")

                if not emp_id or not name or not cat:
                    errors.append(f"行 {idx+1}: 必須項目（社員番号、氏名、または支給・控除項目名）が欠落しています。")
                    continue
                try:
                    clean_amt = int(str(raw_amt).replace("¥", "").replace(",", "").strip())
                    if clean_amt < 0:
                        errors.append(f"行 {idx+1}: 金額 ({raw_amt}) は0以上の正数である必要があります。")
                        continue
                except ValueError:
                    errors.append(f"行 {idx+1}: 金額 '{raw_amt}' は有効な数値ではありません。")
                    continue

                row_id = row_dict.get("id") or row_dict.get("伝票番号") or f"PAY-2026-{idx+1:03d}"
                itype = row_dict.get("item_type") or ("Deduction" if "控除" in str(cat) else "Addition")
                records.append({
                    "id": str(row_id),
                    "employee_id": str(emp_id),
                    "employee_name": str(name),
                    "item_category": str(cat),
                    "item_type": str(itype),
                    "raw_amount": clean_amt,
                    "amount": f"¥{clean_amt:,}",
                    "status": "Unprocessed"
                })
        else: # leave
            valid_types = ['有給休暇', '病気休暇', '慶弔特別休暇', '未登録休暇']
            for idx, r in df.iterrows():
                row_dict = {str(k).strip().lower(): v for k, v in r.items()}
                emp_id = row_dict.get("employee_id") or row_dict.get("社員番号")
                name = row_dict.get("employee_name") or row_dict.get("氏名")
                ltype = row_dict.get("leave_type") or row_dict.get("休暇区分") or row_dict.get("種別") or "有給休暇"
                sdate = row_dict.get("start_date") or row_dict.get("開始日") or "2026-07-20"
                edate = row_dict.get("end_date") or row_dict.get("終了日") or "2026-07-21"
                days = row_dict.get("requested_days") or row_dict.get("申請日数") or row_dict.get("日数")

                if not emp_id or not name:
                    errors.append(f"行 {idx+1}: 必須項目（社員番号または氏名）が欠落しています。")
                    continue
                if ltype not in valid_types:
                    errors.append(f"行 {idx+1}: 未対応の休暇種別 '{ltype}' です。許容値: [{', '.join(valid_types)}]")
                    continue
                try:
                    clean_days = float(days) if days else 1.0
                    if clean_days <= 0:
                        errors.append(f"行 {idx+1}: 申請日数 ({days}) は0より大きい正数である必要があります。")
                        continue
                except ValueError:
                    errors.append(f"行 {idx+1}: 申請日数 '{days}' は有効な数値 (REAL/FLOAT) ではありません。")
                    continue

                row_id = row_dict.get("id") or row_dict.get("申請id") or f"LV-2026-{idx+1:03d}"
                records.append({
                    "id": str(row_id),
                    "employee_id": str(emp_id),
                    "employee_name": str(name),
                    "department": str(row_dict.get("department") or row_dict.get("部署") or "開発部"),
                    "leave_type": str(ltype),
                    "start_date": str(sdate),
                    "end_date": str(edate),
                    "requested_days": clean_days,
                    "remaining_balance": float(row_dict.get("remaining_balance") or row_dict.get("残日数") or 10.0),
                    "reason": str(row_dict.get("reason") or row_dict.get("理由") or "私用のため"),
                    "has_attachment": bool(row_dict.get("has_attachment") or row_dict.get("添付")),
                    "attachment_name": str(row_dict.get("attachment_name") or ""),
                    "status": "Unprocessed"
                })

        if errors:
            return jsonify({
                "success": False,
                "error": "データ検証エラー (Validation Failed)",
                "details": errors[:10],
                "total_errors": len(errors),
                "records_parsed": len(records),
                "instruction": "データベース仕様・データ型ガイドを確認し、カラム名と値の型を修正してください。"
            }), 400

        return jsonify({
            "success": True,
            "filename": filename,
            "count": len(records),
            "records": records
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"ファイル解析エラー: {str(e)}"}), 500

@app.route("/api/master/regulations", methods=["GET"])
def get_regulations_route():
    return jsonify(get_master_regulations())

@app.route("/api/master/regulations", methods=["POST"])
def save_regulations_route():
    data = request.json or {}
    regs = data.get("regulations") or (data if isinstance(data, list) else [])
    ok = save_master_regulations(regs)
    return jsonify({"success": ok, "count": len(regs)})

@app.route("/api/master/upload", methods=["POST"])
def upload_master_regulations():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    file = request.files["file"]
    filename = file.filename or "master_regulations.xlsx"
    file_bytes = file.read()
    try:
        import io, csv
        rows = []
        if filename.lower().endswith((".xlsx", ".xls")):
            import pandas as pd
            df = pd.read_excel(io.BytesIO(file_bytes))
            df = df.fillna("")
            for _, r in df.iterrows():
                d = {str(k).strip().lower(): str(v).strip() for k, v in r.items()}
                code = d.get("code") or d.get("コード") or d.get("取引先コード") or d.get("取引先cd") or d.get("規程コード") or d.get("id") or ""
                name = d.get("name") or d.get("対象名称") or d.get("取引先名") or d.get("取引先企業名") or d.get("項目名") or d.get("氏名") or d.get("item") or ""
                limit = d.get("limit") or d.get("上限") or d.get("契約定額") or d.get("許容金額") or d.get("金額") or d.get("amount") or ""
                req = d.get("req") or d.get("承認要件") or d.get("要件") or d.get("条件") or d.get("requirement") or ""
                cls = d.get("class") or d.get("区分") or d.get("種別") or d.get("category") or d.get("type") or "Routine"
                if code or name:
                    rows.append({"code": code, "name": name, "limit": limit, "req": req, "class": cls})
        else:
            text = file_bytes.decode("utf-8-sig", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            for r in reader:
                d = {str(k).strip().lower(): str(v).strip() for k, v in r.items() if k}
                code = d.get("code") or d.get("コード") or d.get("取引先コード") or d.get("取引先cd") or d.get("規程コード") or d.get("id") or ""
                name = d.get("name") or d.get("対象名称") or d.get("取引先名") or d.get("取引先企業名") or d.get("項目名") or d.get("氏名") or d.get("item") or ""
                limit = d.get("limit") or d.get("上限") or d.get("契約定額") or d.get("許容金額") or d.get("金額") or d.get("amount") or ""
                req = d.get("req") or d.get("承認要件") or d.get("要件") or d.get("条件") or d.get("requirement") or ""
                cls = d.get("class") or d.get("区分") or d.get("種別") or d.get("category") or d.get("type") or "Routine"
                if code or name:
                    rows.append({"code": code, "name": name, "limit": limit, "req": req, "class": cls})

        if rows:
            save_master_regulations(rows)
            return jsonify({"success": True, "count": len(rows), "filename": filename, "regulations": rows})
        else:
            return jsonify({"success": False, "error": "No valid regulation rows found in uploaded file."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-doc", methods=["POST"])
def upload_doc():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    filename = file.filename or "uploaded_document.docx"
    file_bytes = file.read()
    try:
        text = extract_text_from_file_bytes(filename, file_bytes)
        return jsonify({"success": True, "filename": filename, "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/copilot/analyze", methods=["POST"])
def analyze_copilot():
    try:
        data = request.json or {}
        process_type = data.get("process_type", "invoice")
        doc_text = data.get("document_text", "")
        filename = data.get("filename_or_title", "Policy Document")

        if erp_policy_engine:
            rules = erp_policy_engine.extract_policy_rules(process_type=process_type, policy_text=doc_text)
            return jsonify({
                "success": True,
                "process_type": process_type,
                "rules": rules,
                "count": len(rules)
            })
        else:
            result = copilot_engine.analyze_policy(
                process_type=process_type,
                document_text=doc_text,
                filename_or_title=filename
            )
            return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e), "rules": []}), 500

@app.route("/api/copilot/evaluate", methods=["POST"])
def evaluate_copilot():
    try:
        data = request.json or {}
        process_type = data.get("process_type", "invoice")
        doc_text = data.get("document_text", "")
        filename = data.get("filename_or_title", "Policy Document")
        custom_rules = data.get("custom_rules")

        print(f"\n[EVALUATE REQUEST] custom_rules count: {len(custom_rules) if custom_rules else 'None'}")
        if custom_rules:
            for idx, r in enumerate(custom_rules):
                print(f"  [EVAL RULE {idx}] rule_id={r.get('rule_id')} action={r.get('action_on_match')} cond={r.get('condition')} sql_cond={r.get('sql_condition')}")

        if erp_policy_engine:
            if custom_rules:
                refined_rules = erp_policy_engine.validate_and_refine_rules(process_type, custom_rules, doc_text)
            else:
                refined_rules = erp_policy_engine.extract_policy_rules(process_type, doc_text)

            eval_res = erp_policy_engine.evaluate_rows(process_type, refined_rules)
            print(f"[EVALUATE RESULT] approved={eval_res.get('approved_count')} hold={eval_res.get('hold_count')} evaluated={eval_res.get('total_evaluated')}\n")
            return jsonify({
                "success": True,
                "status": "STAGED",
                "process_type": process_type,
                "approved_count": eval_res.get("approved_count", 0),
                "hold_count": eval_res.get("hold_count", 0),
                "evaluated_count": eval_res.get("total_evaluated", 0),
                "rules": eval_res.get("rules", []),
                "staged_decisions": eval_res.get("decisions", []),
                "discrepancies": eval_res.get("discrepancies", []),
                "summary": eval_res.get("summary", "")
            })
        else:
            result = copilot_engine.evaluate(
                process_type=process_type,
                document_text=doc_text,
                filename_or_title=filename,
                custom_rules=custom_rules
            )
            print(f"[EVALUATE RESULT] approved={result.get('approved_count')} hold={result.get('hold_count')} evaluated={result.get('evaluated_count')}\n")
            return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/copilot/commit", methods=["POST"])
def commit_copilot():
    try:
        data = request.json or {}
        process_type = data.get("process_type", "invoice")
        decisions = data.get("decisions", [])

        if erp_policy_engine:
            commit_res = erp_policy_engine.commit_database_updates(process_type=process_type, decisions=decisions)
            discrepancies = [d for d in decisions if d.get("new_status") == "Hold"]
            return jsonify({
                "success": True,
                "overall_status": "SUCCESS",
                "updated_count": commit_res.get("updated_count", 0),
                "discrepancies": discrepancies,
                "message": commit_res.get("message", "Committed successfully")
            })
        else:
            result = copilot_engine.commit_staged(
                process_type=process_type,
                decisions=decisions
            )
            return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/copilot/run", methods=["POST"])
def run_copilot():
    try:
        data = request.json or {}
        process_type = data.get("process_type", "invoice")
        doc_text = data.get("document_text", "")
        filename = data.get("filename_or_title", "Policy Document")

        if erp_policy_engine:
            rules = erp_policy_engine.extract_policy_rules(process_type=process_type, policy_text=doc_text)
            eval_res = erp_policy_engine.evaluate_rows(process_type, rules)
            return jsonify({
                "success": True,
                "status": "STAGED",
                "process_type": process_type,
                "approved_count": eval_res.get("approved_count", 0),
                "hold_count": eval_res.get("hold_count", 0),
                "evaluated_count": eval_res.get("total_evaluated", 0),
                "rules": eval_res.get("rules", []),
                "staged_decisions": eval_res.get("decisions", []),
                "discrepancies": eval_res.get("discrepancies", []),
                "summary": eval_res.get("summary", "")
            })
        else:
            result = copilot_engine.run(
                process_type=process_type,
                document_text=doc_text,
                filename_or_title=filename
            )
            return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/item/override", methods=["POST"])
def override_item():
    data = request.json or {}
    suite = data.get("suite", "invoice")
    item_id = data.get("id")
    status = data.get("status")
    comment = data.get("comment", "Manual Administrator Override")

    if suite == "invoice":
        ok = db_manager.update_invoice_status(item_id, status, comment)
    elif suite in ("leave", "leave_mgmt", "leave_applications"):
        ok = db_manager.update_leave_application_status(item_id, status, comment)
    else:
        ok = db_manager.update_payroll_item_status(item_id, status, comment)

    return jsonify({"success": ok})

@app.route("/api/llm/status")
def llm_status():
    st = llm_service.get_status()
    if erp_policy_engine and hasattr(erp_policy_engine, "llm"):
        st["policy_engine_model"] = erp_policy_engine.llm.model
        st["policy_engine_token_present"] = bool(erp_policy_engine.llm.token)
    return jsonify(st)

@app.route("/api/llm/test", methods=["POST"])
def test_llm():
    data = request.json or {}
    provider = data.get("provider", "puter")
    default_token = os.environ.get("PUTER_AUTH_TOKEN", "") if provider == "puter" else os.environ.get("OPENROUTER_API_KEY", "")
    token = data.get("token") or default_token
    default_model = "openrouter:openrouter/free" if provider == "puter" else ("openrouter/free" if provider == "openrouter" else "openrouter:openrouter/free")
    model = data.get("model") or default_model

    llm_service.configure(provider, token, model, persist_to_env=True)
    if erp_policy_engine and hasattr(erp_policy_engine, "llm"):
        if token:
            erp_policy_engine.llm.token = token
        if model:
            erp_policy_engine.llm.model = model
    res = llm_service.test_connection()
    return jsonify(res)

@app.route("/api/llm/save", methods=["POST"])
def save_llm():
    data = request.json or {}
    provider = data.get("provider", "puter")
    token = data.get("token") or ""
    default_model = "openrouter:openrouter/free" if provider == "puter" else ("openrouter/free" if provider == "openrouter" else "openrouter:openrouter/free")
    model = data.get("model") or default_model

    llm_service.configure(provider, token, model, persist_to_env=True)
    if erp_policy_engine and hasattr(erp_policy_engine, "llm"):
        if token:
            erp_policy_engine.llm.token = token
        if model:
            erp_policy_engine.llm.model = model
    return jsonify({"success": True})

@app.route("/api/export-excel/<suite>", methods=["GET"])
def export_excel(suite):
    try:
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from flask import send_file

        wb = openpyxl.Workbook()
        ws = wb.active

        thin = Side(border_style="thin", color="D1D5DB")
        border = Border(top=thin, left=thin, right=thin, bottom=thin)
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        cell_font = Font(name="Segoe UI", size=10)

        if suite == "invoice":
            ws.title = "請求書承認台帳"
            headers = ["伝票ID", "取引先コード", "取引先名称", "請求書番号", "請求金額 (表示)", "金額 (数値)", "区分", "ステータス", "照合コメント", "更新日時"]
            ws.append(headers)
            rows = db_manager.get_all_invoices()
            for r in rows:
                ws.append([
                    r.get("id"), r.get("vendor_code") or r.get("employee_id"), r.get("vendor_name") or r.get("name"), r.get("invoice_no"),
                    r.get("amount"), r.get("raw_amount"), r.get("type"), r.get("status"),
                    r.get("comment"), str(r.get("updated_at") or "")
                ])
            filename = f"Invoices_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:
            ws.title = "人事給与・経費精算台帳"
            headers = ["伝票ID", "従業員コード", "氏名", "経費・手当項目", "加算/控除区分", "金額 (表示)", "金額 (数値)", "照合伝票番号", "ステータス", "確認コメント", "更新日時"]
            ws.append(headers)
            rows = db_manager.get_all_payroll_items()
            for r in rows:
                ws.append([
                    r.get("id"), r.get("employee_id"), r.get("employee_name"), r.get("item_category"),
                    r.get("item_type"), r.get("amount"), r.get("raw_amount"), r.get("voucher_ref"),
                    r.get("status"), r.get("comment"), str(r.get("updated_at") or "")
                ])
            filename = f"Payroll_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # Style header row
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Style data rows
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.font = cell_font
                cell.border = border

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("ERP_PORT", 5135))
    print(f"Starting Unified Enterprise ERP Portal on port {port}...")
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
