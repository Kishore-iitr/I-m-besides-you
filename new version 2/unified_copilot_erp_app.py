"""
Unified Enterprise ERP Portal & LangGraph AI Co-Pilot
Dual Operational Suites:
  1. 財務会計システム (Financial Accounting - Invoice Processing)
  2. HR人事給与システム (HR & Payroll - Payroll Item Processing)
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

from erp_db import db_manager, INITIAL_INVOICES, INITIAL_PAYROLL_ITEMS, get_master_regulations, save_master_regulations
from copilot_langgraph_engine import copilot_engine, llm_service, extract_text_from_file_bytes

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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enterprise ERP System & AI Co-Pilot</title>
  <style>
    :root {
      --primary: #1e3a8a;
      --primary-hover: #172554;
      --accent: #0284c7;
      --bg-slate: #f8fafc;
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
    body { background-color: #f1f5f9; color: var(--text-main); font-size: 13px; line-height: 1.45; min-height: 100vh; display: flex; flex-direction: column; }

    /* Top Corporate Navigation Bar */
    header.erp-header {
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      height: 60px;
      padding: 0 24px;
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
      gap: 12px;
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
      letter-spacing: -0.5px;
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

    /* Dual Suite Navigator (High-Visibility Prominent Tabs) */
    .suite-nav-tabs-prominent {
      display: flex;
      background: #e2e8f0;
      padding: 4px;
      border-radius: 10px;
      gap: 6px;
    }
    .prominent-tab-btn {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 18px;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      background: transparent;
      color: #475569;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .prominent-tab-btn .tab-icon {
      font-size: 18px;
    }
    .prominent-tab-btn .tab-text-wrap {
      display: flex;
      flex-direction: column;
      text-align: left;
    }
    .prominent-tab-btn .tab-main-title {
      font-size: 13px;
      font-weight: 700;
      line-height: 1.2;
    }
    .prominent-tab-btn .tab-sub-title {
      font-size: 10px;
      color: #64748b;
      line-height: 1.2;
    }
    .prominent-tab-btn.active {
      background: #ffffff;
      color: var(--primary);
      border-color: #cbd5e1;
      box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .prominent-tab-btn.active .tab-sub-title {
      color: var(--accent);
      font-weight: 600;
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

    /* Module Banner: Unmistakable visual separation */
    .module-banner {
      background: #ffffff;
      border-bottom: 2px solid #bfdbfe;
      padding: 10px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.2s ease;
    }
    .module-banner.payroll {
      border-bottom: 2px solid #99f6e4;
    }
    .banner-content { display: flex; flex-direction: column; gap: 2px; }
    .banner-badge {
      display: inline-block;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.8px;
      color: var(--primary);
    }
    .banner-title {
      font-size: 15px;
      font-weight: 800;
      color: #0f172a;
    }
    .banner-desc {
      font-size: 11px;
      color: var(--text-muted);
    }
    .banner-meta {
      display: flex;
      gap: 8px;
    }
    .meta-tag {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      color: #475569;
    }

    /* Main Resizable Layout */
    .main-layout {
      display: flex;
      flex-direction: row;
      gap: 0;
      padding: 14px 20px;
      flex: 1;
      align-items: stretch;
      min-height: 0;
      position: relative;
    }

    /* Side Workspace Panel (Resizable Width) */
    .workspace-panel {
      width: 490px;
      min-width: 330px;
      max-width: 850px;
      flex-shrink: 0;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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
      transition: background 0.15s ease;
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
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .workspace-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .workspace-tabs {
      display: flex;
      gap: 6px;
      border-bottom: 1px solid var(--border-color);
      background: #f1f5f9;
      padding: 6px 12px 0 12px;
    }
    .ws-tab-btn {
      padding: 6px 12px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 6px 6px 0 0;
      border: 1px solid transparent;
      border-bottom: none;
      background: transparent;
      color: var(--text-muted);
      cursor: pointer;
    }
    .ws-tab-btn.active {
      background: #ffffff;
      color: var(--primary);
      border-color: var(--border-color);
      border-bottom: 1px solid #ffffff;
      margin-bottom: -1px;
    }

    /* Clean Corporate Policy Editor (Replaces Retro Notepad) */
    .policy-editor-box {
      display: flex;
      flex-direction: column;
      height: 280px;
      border-bottom: 1px solid var(--border-color);
      background: #ffffff;
    }
    .editor-toolbar {
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 4px 10px;
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
      height: 280px;
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

    /* Word Window */
    .word-window {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      height: 280px;
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
      padding: 10px 14px;
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      max-height: 200px;
      overflow-y: auto;
    }
    .rules-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .rules-count-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      background: #dbeafe;
      color: #1e40af;
      border-radius: 10px;
    }
    .global-rule-banner {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-left: 3px solid #0284c7;
      padding: 5px 8px;
      font-size: 11px;
      color: #334155;
      margin-bottom: 6px;
      border-radius: 3px;
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
      background: #f1f5f9;
      color: #475569;
      font-weight: 600;
      font-size: 10px;
    }

    /* LangGraph Visualizer */
    .graph-tracker-box {
      padding: 12px 14px;
      background: #ffffff;
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
    .graph-steps-container {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .graph-node {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 5px;
      padding: 6px 10px;
      font-size: 11px;
      transition: all 0.2s ease;
    }
    .graph-node.node-active {
      border-color: #0284c7;
      background: #f0f9ff;
      box-shadow: 0 0 0 1px #0284c7;
    }
    .graph-node.node-done {
      border-color: #16a34a;
      background: #f0fdf4;
    }
    .graph-node.node-pending {
      opacity: 0.6;
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

    /* Right: ERP Table Section */
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
    }
    .table-top-toolbar {
      padding: 12px 16px;
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
      display: flex;
      gap: 12px;
      padding: 10px 16px;
      background: #ffffff;
      border-bottom: 1px solid #f1f5f9;
    }
    .metric-card {
      flex: 1;
      padding: 6px 12px;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      background: #f8fafc;
    }
    .metric-card.approved { border-left: 4px solid var(--success); }
    .metric-card.hold { border-left: 4px solid var(--danger); }
    .metric-card.unprocessed { border-left: 4px solid #64748b; }
    .metric-card-label { font-size: 11px; color: var(--text-muted); }
    .metric-card-val { font-size: 17px; font-weight: 700; color: var(--text-main); margin-top: 2px; }

    /* Main ERP Table */
    .table-scroll-container {
      flex: 1;
      max-height: calc(100vh - 240px);
      overflow-y: auto;
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

    /* Sober & Professional Corporate Human Intervention Cards */
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

    /* Tab Switcher inside Modal */
    .modal-inner-tabs {
      display: flex;
      border-bottom: 1px solid #e2e8f0;
      margin-bottom: 14px;
      gap: 8px;
    }
    .modal-inner-tab-btn {
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: #64748b;
    }
    .modal-inner-tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }
  </style>
</head>
<body>

  <!-- Top Corporate ERP Header -->
  <header class="erp-header">
    <div class="header-brand">
      <div class="erp-logo-icon">ERP</div>
      <div class="header-title-box">
        <span class="header-title">基幹統合業務システム (Enterprise ERP Platform)</span>
        <span class="header-subtitle">LangGraph AI Co-Pilot & Database Management</span>
      </div>
    </div>

    <!-- Dual Suite Navigator (High-Visibility Prominent Tabs) -->
    <div class="suite-nav-tabs-prominent">
      <button class="prominent-tab-btn active" id="tab-invoice" onclick="switchSuite('invoice')">
        <span class="tab-icon">🏛️</span>
        <div class="tab-text-wrap">
          <span class="tab-main-title">財務会計システム</span>
          <span class="tab-sub-title">売掛・買掛・請求書照合 (Dataset A)</span>
        </div>
      </button>
      <button class="prominent-tab-btn" id="tab-payroll" onclick="switchSuite('payroll')">
        <span class="tab-icon">👥</span>
        <div class="tab-text-wrap">
          <span class="tab-main-title">HR人事給与システム</span>
          <span class="tab-sub-title">給与・諸手当・経費精算SOP (Dataset B)</span>
        </div>
      </button>
    </div>

    <!-- Header Status Indicators & Actions -->
    <div class="header-actions">
      <!-- LLM Provider Pill -->
      <div class="status-pill llm" onclick="openLlmModal()" title="LLM接続設定">
        <span class="dot" id="llm-dot"></span>
        <span id="llm-pill-text">LLM: Puter (gpt-4o-mini)</span>
      </div>

      <!-- Database Status Pill -->
      <div class="status-pill db" onclick="openDbModal()" title="データベース接続設定">
        <span class="dot"></span>
        <span id="db-pill-text">DB: PostgreSQL Active</span>
      </div>

      <button class="btn-header" onclick="resetDatabaseBenchmark()" title="ベンチマークデータを初期化">
        ↺ データ初期化
      </button>
    </div>
  </header>

  <!-- Module Banner: Unmistakable visual separation -->
  <div class="module-banner" id="module-banner">
    <div class="banner-content">
      <span class="banner-badge" id="banner-badge">🏛️ FINANCIAL ACCOUNTING SUITE</span>
      <h2 class="banner-title" id="banner-title">財務会計システム：月次定額保守・取引先請求伝票 照合承認基盤</h2>
      <p class="banner-desc" id="banner-desc">
        定額保守契約マスタおよび業務委託規程に基づく自動突合（Straight-Through Processing）。変動・調整取引（Adjustment）の検知とJ-SOX統制監査。
      </p>
    </div>
    <div class="banner-meta">
      <span class="meta-tag" id="banner-mode-tag">モジュール: 財務会計</span>
      <span class="meta-tag">J-SOX 内部統制準拠</span>
    </div>
  </div>

  <!-- Main Resizable Split Layout -->
  <main class="main-layout" id="main-layout">

    <!-- Left: Co-Pilot Reference & Multi-Window Workspace -->
    <aside class="workspace-panel" id="workspace-panel">
      <div class="workspace-header">
        <div class="workspace-title">
          <span>AI Co-Pilot 参照ワークスペース</span>
        </div>
        <button class="btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="loadPresetDocument()">
          規定メモ読込
        </button>
      </div>

      <!-- Mimic Navigation Tabs -->
      <div class="workspace-tabs">
        <button class="ws-tab-btn active" id="ws-btn-notepad" onclick="switchWsTab('notepad')">
          📋 規程・メモ入力
        </button>
        <button class="ws-tab-btn" id="ws-btn-excel" onclick="switchWsTab('excel')">
          📊 規程マスタ (編集可能)
        </button>
        <button class="ws-tab-btn" id="ws-btn-word" onclick="switchWsTab('word')">
          📁 Word &amp; Excel 文書
        </button>
      </div>

      <!-- Tab 1: Policy / Memo Clean Editor -->
      <div id="ws-tab-notepad" class="policy-editor-box">
        <div class="editor-toolbar">
          <span id="notepad-filename">月次定額保守取引先一覧.txt (参照規程)</span>
          <div style="display: flex; gap: 6px;">
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="document.getElementById('doc-text').value='';">クリア</button>
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="loadPresetDocument()">再読込</button>
          </div>
        </div>
        <textarea id="doc-text" class="policy-textarea" spellcheck="false">{{ invoice_preset }}</textarea>
      </div>

      <!-- Tab 2: Editable Master Spreadsheet -->
      <div id="ws-tab-excel" class="excel-window" style="display: none;">
        <div class="excel-toolbar">
          <span style="font-weight: 700; color: #15803d;">📊 業務委託規程・契約マスタ (編集可能)</span>
          <div style="display: flex; gap: 6px;">
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="addMasterRow()">+ 行追加</button>
            <button class="btn-primary" style="padding: 2px 8px; font-size: 10px; background: #15803d;" onclick="saveMasterRegulationsTable()">💾 マスタ保存</button>
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

      <!-- Tab 3: Word Upload Window -->
      <div id="ws-tab-word" class="word-window" style="display: none;">
        <div class="dropzone" onclick="document.getElementById('file-upload').click()">
          <div style="font-size: 24px; margin-bottom: 8px;">📁</div>
          <div style="font-weight: 600; color: #1e3a8a;">Word (.docx) / Excel (.xlsx, .csv) をアップロード</div>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">またはここをクリックしてファイルを選択</div>
          <input type="file" id="file-upload" accept=".docx,.xlsx,.xls,.csv,.txt" style="display: none;" onchange="handleFileUpload(event)">
        </div>
        <div id="upload-status" style="font-size: 11px; color: #166534; font-weight: 600;"></div>
      </div>

      <!-- Extracted Active Rules Container -->
      <div class="extracted-rules-box" id="extracted-rules-box">
        <div class="rules-header">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; display: flex; align-items: center; gap: 6px;">
            <span>📋</span>
            <span id="rules-title">適用規程・判定ルール一覧 (Active Rule Engine)</span>
          </div>
          <span class="rules-count-badge" id="rules-count-badge">8 ルール有効</span>
        </div>
        <div class="global-rule-banner" id="global-rule-banner">
          【グローバル原則】単一伝票200万円以下かつ区分Routine(通常)のみ自動承認。区分Adjustment(調整)は全件要人間精査(Hold)。
        </div>
        <table class="rules-table">
          <thead>
            <tr>
              <th style="width: 75px;">ルールID</th>
              <th style="width: 100px;">対象</th>
              <th>判定条件</th>
              <th style="width: 55px;">判定</th>
              <th>説明</th>
            </tr>
          </thead>
          <tbody id="rules-table-body">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>

      <!-- LangGraph Pipeline Visualizer -->
      <div class="graph-tracker-box">
        <div class="graph-title">
          <span>LangGraph 4-Node 実行パイプライン</span>
          <span id="graph-overall-badge" style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #e2e8f0;">READY</span>
        </div>
        <div class="graph-steps-container">
          <div class="graph-node node-pending" id="node-1">
            <span><strong>Node 1:</strong> parse_document_to_schema_json</span>
            <span id="time-node-1" style="font-size: 11px; color: var(--text-muted);">-</span>
          </div>
          <div class="graph-node node-pending" id="node-2">
            <span><strong>Node 2:</strong> compare_features_and_decide</span>
            <span id="time-node-2" style="font-size: 11px; color: var(--text-muted);">-</span>
          </div>
          <div class="graph-node node-pending" id="node-3">
            <span><strong>Node 3:</strong> commit_database_updates</span>
            <span id="time-node-3" style="font-size: 11px; color: var(--text-muted);">-</span>
          </div>
          <div class="graph-node node-pending" id="node-4">
            <span><strong>Node 4:</strong> human_in_the_loop_audit</span>
            <span id="time-node-4" style="font-size: 11px; color: var(--text-muted);">-</span>
          </div>
        </div>

        <button class="btn-run-agent" id="btn-run" onclick="startLangGraphEvaluation()">
          ⚡ Run LangGraph Co-Pilot Agent
        </button>

        <!-- Professional Human Intervention Container -->
        <div id="interventions-container" style="display: none; margin-top: 12px;">
          <div style="font-weight: 700; color: #92400e; font-size: 12px; margin-bottom: 4px;">
            ⚠️ 内部統制・要人間精査項目 (Audit Required):
          </div>
          <div id="interventions-list"></div>
        </div>
      </div>
    </aside>

    <!-- Draggable Vertical Splitter Handle -->
    <div class="drag-splitter" id="drag-splitter" title="左右にドラッグしてパネル幅を調整"></div>

    <!-- Right: Real-time ERP Live Database Grid -->
    <section class="erp-content" id="erp-content">
      <!-- Toolbar -->
      <div class="table-top-toolbar">
        <div class="toolbar-left">
          <span style="font-weight: 700; font-size: 13px;" id="table-suite-title">財務会計システム - 請求書一覧</span>
          <span style="font-size: 11px; color: #64748b;" id="table-row-count">(105 件)</span>
        </div>
        <div class="toolbar-right">
          <button class="btn-secondary" onclick="exportToExcel()" title="現在の一覧をExcel形式 (.xlsx) でダウンロード" style="background: #166534; color: white; border-color: #15803d; font-weight: 600;">
            📊 Excelエクスポート
          </button>
          <button class="btn-secondary" onclick="loadTableData()" title="最新データに再読込">
            🔄 更新
          </button>
          <button class="btn-primary" onclick="openAddRecordModal()">
            + 新規伝票追加 / 一括取込
          </button>
        </div>
      </div>

      <!-- Metric Cards -->
      <div class="table-metric-cards">
        <div class="metric-card approved">
          <div class="metric-card-label" id="metric-label-approved">自動承認済</div>
          <div class="metric-card-val" id="metric-approved-count">0</div>
        </div>
        <div class="metric-card hold">
          <div class="metric-card-label">保留・精査要 (Hold)</div>
          <div class="metric-card-val" id="metric-hold-count">0</div>
        </div>
        <div class="metric-card unprocessed">
          <div class="metric-card-label">未処理伝票</div>
          <div class="metric-card-val" id="metric-unprocessed-count">0</div>
        </div>
      </div>

      <!-- Scrollable Data Grid -->
      <div class="table-scroll-container">
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
  </main>

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
            <span style="color: #64748b; font-size: 11px;">伝票番号 (Voucher ID):</span>
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
          <label>承認ステータス (Status):</label>
          <select id="modal-status-select" class="form-control">
            <option value="Unprocessed">未処理 (Unprocessed)</option>
            <option value="Approved">承認済 (Approved)</option>
            <option value="Confirmed">確認済 (Confirmed)</option>
            <option value="Hold">保留 (Hold)</option>
            <option value="Rejected">差戻 (Rejected)</option>
          </select>
        </div>

        <div class="form-group">
          <label>処理内容・確認コメント (Certified Audit Comment):</label>
          <textarea id="modal-comment-text" class="form-control" rows="4" placeholder="コメントを入力してください…"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeCommentModal()">閉じる</button>
        <button class="btn-primary" onclick="commitCommentModal()">💾 DBへ直接コミット (Save to DB)</button>
      </div>
    </div>
  </div>

  <!-- Modal 2: Staged Decision Review & Commit Confirmation (ALL Rows Visible + Info Icon) -->
  <div class="modal-overlay" id="staged-modal">
    <div class="modal-card large">
      <div class="modal-header">
        <span>⚡ LangGraph 評価結果の確認 & DB反映承認</span>
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
          <input type="text" id="staged-search-input" class="form-control" style="width: 200px; padding: 3px 8px; font-size: 11px;" placeholder="伝票ID / 氏名で絞込…" oninput="filterStagedRows(currentStagedFilter)">
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
                <th>適用ルール & LLMコメント</th>
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
          ✓ データベースへ反映・コミット (Commit to DB)
        </button>
      </div>
    </div>
  </div>

  <!-- Modal 3: Add Record Dialog (Single + Bulk Excel/CSV Import) -->
  <div class="modal-overlay" id="add-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span id="add-modal-title">+ 新規伝票追加 / 一括取込</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeAddRecordModal()">✕</button>
      </div>
      <div class="modal-body">
        <!-- Inner Tab Switcher -->
        <div class="modal-inner-tabs">
          <button class="modal-inner-tab-btn active" id="tab-add-single" onclick="switchAddTab('single')">個別入力</button>
          <button class="modal-inner-tab-btn" id="tab-add-bulk" onclick="switchAddTab('bulk')">📊 Excel/CSV 一括取込</button>
        </div>

        <!-- Section 1: Single Record Entry Form -->
        <div id="add-single-form">
          <!-- Injected based on active suite -->
        </div>

        <!-- Section 2: Bulk Spreadsheet Import Form -->
        <div id="add-bulk-form" style="display: none;">
          <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">
            Excelからコピーした表データ（タブ区切りまたはカンマ区切り）を貼り付けるか、CSVファイルを取り込んでください。
          </div>
          <div class="form-group">
            <label>Excel/CSV 貼り付け (タブ/カンマ区切り):</label>
            <textarea id="bulk-paste-text" class="form-control" rows="6" placeholder="P6-07010448-106&#9;V3005&#9;Global Tech LLC&#9;¥716,232&#9;Routine&#10;P6-07010448-107&#9;V3006&#9;Hokuriku Parts&#9;¥455,128&#9;Routine"></textarea>
          </div>
          <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <button class="btn-secondary" style="font-size: 11px;" onclick="previewBulkSpreadsheet()">📋 解析プレビュー</button>
            <input type="file" id="bulk-file-input" accept=".csv,.tsv,.txt" style="display: none;" onchange="handleBulkFileSelect(event)">
            <button class="btn-secondary" style="font-size: 11px;" onclick="document.getElementById('bulk-file-input').click()">📁 CSVファイル選択</button>
          </div>
          <div id="bulk-preview-summary" style="font-size: 11px; color: #1e3a8a; font-weight: 600; margin-bottom: 6px;"></div>
          <div id="bulk-preview-container" style="max-height: 140px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 4px; display: none;">
            <table class="erp-table" style="font-size: 10px;">
              <thead id="bulk-preview-head"></thead>
              <tbody id="bulk-preview-body"></tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeAddRecordModal()">キャンセル</button>
        <button class="btn-primary" id="btn-submit-add" onclick="submitAddRecord()">データベースへ登録</button>
      </div>
    </div>
  </div>

  <!-- Modal 4: LLM Configuration Dialog -->
  <div class="modal-overlay" id="llm-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>🤖 LLM 接続設定 (AI Engine Configuration)</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeLlmModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>LLM プロバイダー (Provider):</label>
          <select id="llm-provider-select" class="form-control" onchange="onLlmProviderChange()">
            <option value="puter">Puter.js AI Driver (Free / Multi-Model)</option>
            <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
            <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
            <option value="local">J-SOX Certified Local Engine (Offline/Emulator)</option>
          </select>
        </div>

        <div class="form-group">
          <label>モデル名 (Model):</label>
          <input type="text" id="llm-model-input" class="form-control" value="gpt-4o-mini">
        </div>

        <div class="form-group">
          <label>Auth Token / API Key:</label>
          <input type="password" id="llm-token-input" class="form-control" placeholder="eyJ... / sk-...">
          <small style="color: #64748b; font-size: 11px;">※ Puterの認証トークンまたはOpenAI/Claude APIキー</small>
        </div>

        <div id="llm-test-result" style="display: none; padding: 8px 12px; border-radius: 6px; font-size: 11px; margin-top: 10px;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="testLlmConnection()">⚡ 接続テスト (Test Connection)</button>
        <button class="btn-primary" onclick="saveLlmSettings()">設定を保存 (Save)</button>
      </div>
    </div>
  </div>

  <!-- Modal 5: Database Connection Dialog (Remote Postgres & Custom Local SQLite) -->
  <div class="modal-overlay" id="db-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>🗄️ データベース接続設定 (Database Management)</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeDbModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="font-size: 12px; color: #475569; margin-bottom: 12px;">
          現在の接続先: <strong id="modal-db-current" style="color: var(--primary);">PostgreSQL</strong>
        </div>

        <!-- Section 1: PostgreSQL Connection -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-bottom: 14px;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">1. リモート PostgreSQL / Supabase 接続</div>
          <div class="form-group" style="margin-bottom: 8px;">
            <label>PostgreSQL 接続URI:</label>
            <input type="text" id="db-uri-input" class="form-control" placeholder="postgresql://postgres:password@host:5432/postgres">
          </div>
          <button class="btn-primary" style="font-size: 11px;" onclick="connectCustomDb()">PostgreSQL へ接続</button>
        </div>

        <!-- Section 2: Local Database File Path -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;">
          <div style="font-weight: 700; font-size: 12px; color: #15803d; margin-bottom: 6px;">2. ローカル SQLite データベース (ファイルパス指定)</div>
          <div class="form-group" style="margin-bottom: 8px;">
            <label>ローカル DB ファイルパス:</label>
            <input type="text" id="db-local-path-input" class="form-control" placeholder="C:/Users/.../erp_local.db または ./erp_unified.db">
            <small style="color: #64748b; font-size: 11px;">※ 指定したパスにデータベースファイルが存在しない場合は自動初期化されます</small>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" style="font-size: 11px;" onclick="connectLocalDb()">📂 指定ローカルDBに接続</button>
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

    /* --- Resizable Splitter Logic --- */
    (function initResizableSplitter() {
      const splitter = document.getElementById('drag-splitter');
      const panel = document.getElementById('workspace-panel');
      let isDragging = false;
      let startX, startWidth;

      const savedWidth = localStorage.getItem('erp_ws_width');
      if (savedWidth) {
        panel.style.width = savedWidth + 'px';
      }

      splitter.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startWidth = parseInt(window.getComputedStyle(panel).width, 10);
        splitter.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
      });

      document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        let newWidth = startWidth + dx;
        if (newWidth < 320) newWidth = 320;
        if (newWidth > 850) newWidth = 850;
        panel.style.width = newWidth + 'px';
      });

      document.addEventListener('mouseup', () => {
        if (isDragging) {
          isDragging = false;
          splitter.classList.remove('dragging');
          document.body.style.cursor = '';
          document.body.style.userSelect = '';
          localStorage.setItem('erp_ws_width', parseInt(panel.style.width, 10));
        }
      });
    })();

    /* --- Application Initialization --- */
    window.addEventListener('DOMContentLoaded', async () => {
      await loadMasterRegulations();
      await updateSystemStatus();
      await loadTableData();
      renderInitialExtractedRules();
    });

    /* --- Module Navigation & Visual Theme --- */
    function switchSuite(suite) {
      currentSuite = suite;

      const tabInv = document.getElementById('tab-invoice');
      const tabPay = document.getElementById('tab-payroll');
      const banner = document.getElementById('module-banner');
      const bannerBadge = document.getElementById('banner-badge');
      const bannerTitle = document.getElementById('banner-title');
      const bannerDesc = document.getElementById('banner-desc');
      const bannerMode = document.getElementById('banner-mode-tag');

      if (suite === 'invoice') {
        tabInv.classList.add('active');
        tabPay.classList.remove('active');
        banner.classList.remove('payroll');

        bannerBadge.innerText = '🏛️ FINANCIAL ACCOUNTING SUITE';
        bannerTitle.innerText = '財務会計システム：月次定額保守・取引先請求伝票 照合承認基盤';
        bannerDesc.innerText = '定額保守契約マスタおよび業務委託規程に基づく自動突合（Straight-Through Processing）。変動・調整取引（Adjustment）の検知とJ-SOX統制監査。';
        bannerMode.innerText = 'モジュール: 財務会計 (Dataset A)';

        document.getElementById('table-suite-title').innerText = '財務会計システム - 請求書一覧';
        document.getElementById('metric-label-approved').innerText = '自動承認済';
        document.getElementById('notepad-filename').innerText = '月次定額保守取引先一覧.txt (参照規程)';
        document.getElementById('doc-text').value = INVOICE_PRESET;
      } else {
        tabPay.classList.add('active');
        tabInv.classList.remove('active');
        banner.classList.add('payroll');

        bannerBadge.innerText = '👥 HR & PAYROLL SUITE';
        bannerTitle.innerText = 'HR人事給与システム：給与・諸手当・業務委託経費精算 照合基盤 (Rank 2 Candidate SOP)';
        bannerDesc.innerText = '精算確認メモおよび業務委託給与規程に基づく給与控除・経費改定突合。接待交際費10万円超過・控除区分不整合の自動検知。';
        bannerMode.innerText = 'モジュール: HR人事給与 (Dataset B)';

        document.getElementById('table-suite-title').innerText = 'HR人事給与システム - 支給控除項目一覧';
        document.getElementById('metric-label-approved').innerText = '確認済 (Confirmed)';
        document.getElementById('notepad-filename').innerText = '*精算確認メモ.txt (確認メモ)';
        document.getElementById('doc-text').value = PAYROLL_PRESET;
      }

      resetGraphUi();
      renderInitialExtractedRules();
      loadTableData();
    }

    /* --- Status Check & Refresh --- */
    async function updateSystemStatus() {
      try {
        const dbRes = await fetch('/api/database/status').then(r => r.json());
        const pillText = document.getElementById('db-pill-text');
        pillText.innerText = `DB: ${dbRes.display_target}`;
        document.getElementById('modal-db-current').innerText = dbRes.display_target;
        if (dbRes.sqlite_path) {
          document.getElementById('db-local-path-input').value = dbRes.sqlite_path;
        }

        const llmRes = await fetch('/api/llm/status').then(r => r.json());
        document.getElementById('llm-pill-text').innerText = `LLM: ${llmRes.display}`;
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
    function renderInvoiceTable(records) {
      document.getElementById('table-row-count').innerText = `(${records.length} 件)`;
      let appCount = 0, holdCount = 0, unpCount = 0;

      const thead = document.getElementById('erp-table-head');
      thead.innerHTML = `
        <tr>
          <th style="width: 130px;">伝票番号</th>
          <th style="width: 80px;">取引先CD</th>
          <th>取引先企業名</th>
          <th style="width: 100px;">請求番号</th>
          <th style="width: 90px; text-align: right;">金額</th>
          <th style="width: 80px;">区分</th>
          <th style="width: 90px;">ステータス</th>
          <th style="width: 250px;">確認コメント (Certified Comment)</th>
        </tr>
      `;

      const tbody = document.getElementById('erp-table-body');
      tbody.innerHTML = records.map(r => {
        if (r.status === 'Approved') appCount++;
        else if (r.status === 'Hold') holdCount++;
        else unpCount++;

        const badgeClass = r.status === 'Approved' ? 'badge-approved' : (r.status === 'Hold' ? 'badge-hold' : 'badge-unprocessed');
        const commentHtml = r.comment ? 
          `<button class="btn-comment-icon" onclick="openCommentModal('${r.id}', '${encodeURIComponent(r.comment)}', '${r.status}', '${encodeURIComponent(r.name)}', '${r.amount}')">💬 ${r.comment}</button>` :
          `<button class="btn-comment-icon comment-empty" onclick="openCommentModal('${r.id}', '', '${r.status}', '${encodeURIComponent(r.name)}', '${r.amount}')">💬 コメント追加…</button>`;

        return `
          <tr>
            <td><strong>${r.id}</strong></td>
            <td>${r.employee_id || '-'}</td>
            <td>${r.name}</td>
            <td><span style="font-family: monospace; color: #64748b;">${r.invoice_no || '-'}</span></td>
            <td style="text-align: right; font-weight: 700; color: #1e3a8a;">${r.amount}</td>
            <td><span style="font-size: 11px; font-weight: 600; color: ${r.type === 'Adjustment' ? '#b45309' : '#0284c7'};">${r.type || 'Routine'}</span></td>
            <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
            <td>${commentHtml}</td>
          </tr>
        `;
      }).join('');

      document.getElementById('metric-approved-count').innerText = appCount;
      document.getElementById('metric-hold-count').innerText = holdCount;
      document.getElementById('metric-unprocessed-count').innerText = unpCount;
    }

    /* --- Render Payroll Table --- */
    function renderPayrollTable(records) {
      document.getElementById('table-row-count').innerText = `(${records.length} 件)`;
      let appCount = 0, holdCount = 0, unpCount = 0;

      const thead = document.getElementById('erp-table-head');
      thead.innerHTML = `
        <tr>
          <th style="width: 130px;">伝票番号</th>
          <th style="width: 80px;">従業員ID</th>
          <th>氏名</th>
          <th style="width: 110px;">経費/手当項目</th>
          <th style="width: 70px;">加算/控除</th>
          <th style="width: 90px; text-align: right;">金額</th>
          <th style="width: 120px;">照合伝票番号</th>
          <th style="width: 90px;">ステータス</th>
          <th style="width: 250px;">確認コメント (Certified Comment)</th>
        </tr>
      `;

      const tbody = document.getElementById('erp-table-body');
      tbody.innerHTML = records.map(r => {
        if (r.status === 'Confirmed') appCount++;
        else if (r.status === 'Hold') holdCount++;
        else unpCount++;

        const badgeClass = r.status === 'Confirmed' ? 'badge-confirmed' : (r.status === 'Hold' ? 'badge-hold' : 'badge-unprocessed');
        const commentHtml = r.comment ? 
          `<button class="btn-comment-icon" onclick="openCommentModal('${r.id}', '${encodeURIComponent(r.comment)}', '${r.status}', '${encodeURIComponent(r.employee_name)}', '${r.amount}')">💬 ${r.comment}</button>` :
          `<button class="btn-comment-icon comment-empty" onclick="openCommentModal('${r.id}', '', '${r.status}', '${encodeURIComponent(r.employee_name)}', '${r.amount}')">💬 コメント追加…</button>`;

        return `
          <tr>
            <td><strong>${r.id}</strong></td>
            <td>${r.employee_id || '-'}</td>
            <td><strong>${r.employee_name}</strong></td>
            <td>${r.item_category}</td>
            <td><span style="font-size: 11px; font-weight: 600; color: ${r.item_type === 'Deduction' ? '#b45309' : '#15803d'};">${r.item_type}</span></td>
            <td style="text-align: right; font-weight: 700; color: #1e3a8a;">${r.amount}</td>
            <td><span style="font-family: monospace; font-size: 11px; color: #64748b;">${r.voucher_ref || '-'}</span></td>
            <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
            <td>${commentHtml}</td>
          </tr>
        `;
      }).join('');

      document.getElementById('metric-approved-count').innerText = appCount;
      document.getElementById('metric-hold-count').innerText = holdCount;
      document.getElementById('metric-unprocessed-count').innerText = unpCount;
    }

    /* --- Extracted Active Rules Rendering --- */
    function renderInitialExtractedRules() {
      const banner = document.getElementById('global-rule-banner');
      const tbody = document.getElementById('rules-table-body');
      const badge = document.getElementById('rules-count-badge');

      if (currentSuite === 'invoice') {
        banner.innerText = '【グローバル原則】単一伝票200万円以下かつ区分Routine(通常)のみ自動承認。区分Adjustment(調整)は全件要人間精査(Hold)。';
        badge.innerText = '6 ルール有効';
        tbody.innerHTML = `
          <tr><td>RULE-INV-01</td><td>Global Tech LLC (V3005)</td><td>月次定額 ¥716,232 (Routine)</td><td><span class="status-badge badge-approved">Approved</span></td><td>契約内整合・自動承認</td></tr>
          <tr><td>RULE-INV-02</td><td>北陸部品工業 (V3006)</td><td>定期保守 ¥455,128 / ¥452,219</td><td><span class="status-badge badge-approved">Approved</span></td><td>通常部品保守として承認</td></tr>
          <tr><td>RULE-INV-03</td><td>大和商事 (V3002)</td><td>事務委託 ¥1,237,439 / ¥1,218,687</td><td><span class="status-badge badge-approved">Approved</span></td><td>業務委託契約書照合済</td></tr>
          <tr><td>RULE-INV-04</td><td>福岡システムデザイン (V3007)</td><td>基幹運用保守 (Routine)</td><td><span class="status-badge badge-approved">Approved</span></td><td>IT基盤保守契約内承認</td></tr>
          <tr><td>RULE-INV-ADJ</td><td>沖縄物流センター (V3008) / 他</td><td>伝票区分が「Adjustment」</td><td><span class="status-badge badge-hold">Hold</span></td><td>物流受領書及び経理課長承認要</td></tr>
          <tr><td>RULE-INV-CEIL</td><td>全取引先共通</td><td>請求金額 > 2,000,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>自動承認限度額超過・役員決裁要</td></tr>
        `;
      } else {
        banner.innerText = '【グローバル原則】接待交際費10万円超過および単一経費15万円超過は役員決裁要(Hold)。扶養控除等控除項目の加算登録は区分不整合保留。';
        badge.innerText = '7 ルール有効';
        tbody.innerHTML = `
          <tr><td>RULE-PAY-01</td><td>青木 拓也 (P4-07089771-001)</td><td>研修費 ¥77,224 (上限10万以内)</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>規程第4条適合確認済</td></tr>
          <tr><td>RULE-PAY-02</td><td>菊池 理恵 (P4-07089771-002)</td><td>消耗品費 ¥55,571</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>領収書照合済</td></tr>
          <tr><td>RULE-PAY-03</td><td>坂本 裕二 (P4-07089771-003)</td><td>出張旅費 ¥64,200</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>出張報告書整合済</td></tr>
          <tr><td>RULE-PAY-ENT</td><td>全従業員共通 (接待交際費)</td><td>金額 > 100,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>規程第7条上限超過・役員特別決裁要</td></tr>
          <tr><td>RULE-PAY-CLASS</td><td>扶養控除変更 / 役職手当廃止</td><td>区分が「Addition」として誤登録</td><td><span class="status-badge badge-hold">Hold</span></td><td>控除項目の加算誤登録・区分不整合</td></tr>
          <tr><td>RULE-PAY-CEIL</td><td>全経費項目共通</td><td>金額 > 150,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>社内決済上限超過・要事前稟議確認</td></tr>
          <tr><td>RULE-PAY-UNK</td><td>全手当項目共通</td><td>マスタ未定義手当コード</td><td><span class="status-badge badge-hold">Hold</span></td><td>人事給与マスタ未定義の手当コード</td></tr>
        `;
      }
    }

    function updateExtractedRulesUi(policyJson) {
      if (!policyJson) return;
      const banner = document.getElementById('global-rule-banner');
      const tbody = document.getElementById('rules-table-body');
      const badge = document.getElementById('rules-count-badge');

      if (policyJson.global_rules && policyJson.global_rules.summary) {
        banner.innerText = policyJson.global_rules.summary;
      }

      const criteria = policyJson.item_criteria || [];
      badge.innerText = `${criteria.length} ルール抽出`;

      if (criteria.length > 0) {
        tbody.innerHTML = criteria.map(c => `
          <tr>
            <td><strong>${c.rule_id || 'RULE'}</strong></td>
            <td>${c.match_value || c.name || '-'}</td>
            <td>${c.condition || (c.expected_amounts ? '金額: ' + c.expected_amounts.join(', ') : '規程照合')}</td>
            <td><span class="status-badge ${c.action_on_match === 'Hold' ? 'badge-hold' : (currentSuite === 'invoice' ? 'badge-approved' : 'badge-confirmed')}">${c.action_on_match}</span></td>
            <td>${c.description || '-'}</td>
          </tr>
        `).join('');
      }
    }

    /* --- Workspace Tabs --- */
    function switchWsTab(tab) {
      ['notepad', 'excel', 'word'].forEach(t => {
        document.getElementById('ws-btn-' + t).classList.toggle('active', t === tab);
        document.getElementById('ws-tab-' + t).style.display = (t === tab) ? 'flex' : 'none';
      });
    }

    function loadPresetDocument() {
      document.getElementById('doc-text').value = (currentSuite === 'invoice') ? INVOICE_PRESET : PAYROLL_PRESET;
    }

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
      tbody.innerHTML = masterRegulationsData.map((row, idx) => `
        <tr>
          <td style="text-align: center; color: #64748b;">${idx + 1}</td>
          <td><input type="text" value="${row.code || ''}" onchange="updateMasterCell(${idx}, 'code', this.value)"></td>
          <td><input type="text" value="${row.name || ''}" onchange="updateMasterCell(${idx}, 'name', this.value)"></td>
          <td><input type="text" value="${row.limit || ''}" onchange="updateMasterCell(${idx}, 'limit', this.value)"></td>
          <td><input type="text" value="${row.req || ''}" onchange="updateMasterCell(${idx}, 'req', this.value)"></td>
          <td>
            <select onchange="updateMasterCell(${idx}, 'class', this.value)">
              <option value="Addition" ${row.class === 'Addition' ? 'selected' : ''}>Addition</option>
              <option value="Deduction" ${row.class === 'Deduction' ? 'selected' : ''}>Deduction</option>
              <option value="Routine" ${row.class === 'Routine' ? 'selected' : ''}>Routine</option>
              <option value="Adjustment" ${row.class === 'Adjustment' ? 'selected' : ''}>Adjustment</option>
            </select>
          </td>
          <td style="text-align: center;">
            <button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteMasterRow(${idx})">✕</button>
          </td>
        </tr>
      `).join('');
    }

    function updateMasterCell(idx, key, val) {
      if (masterRegulationsData[idx]) masterRegulationsData[idx][key] = val;
    }

    function addMasterRow() {
      masterRegulationsData.push({
        code: `規程第${masterRegulationsData.length + 1}条`,
        name: "新規規程項目",
        limit: "1件上限 100,000円",
        req: "領収書原本照合済",
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
        alert(`規程マスタ (${d.count} 件) をバックエンドへ保存しました。次回のAI評価時に即時反映されます。`);
      } catch (e) {
        alert('マスタ保存エラー: ' + e);
      }
    }

    /* --- LangGraph Staged Evaluation & Confirmation Flow --- */
    async function startLangGraphEvaluation() {
      const docText = document.getElementById('doc-text').value.trim();
      if (!docText) {
        alert('参照メモまたは規程方針を入力してください。');
        return;
      }

      const btn = document.getElementById('btn-run');
      btn.disabled = true;
      btn.innerText = 'LangGraph Node 1 & 2 評価中...';

      resetGraphUi();
      setNodeActive('node-1');

      try {
        const res = await fetch('/api/copilot/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            process_type: currentSuite,
            document_text: docText,
            filename_or_title: currentSuite === 'invoice' ? '月次定額保守取引先一覧.txt' : '*精算確認メモ.txt'
          })
        });
        const result = await res.json();

        // Update node visual status
        (result.execution_steps || []).forEach((step, idx) => {
          setNodeDone('node-' + (idx + 1), step.duration_s + 's');
        });

        // Update visible rules inspector with extracted rules
        updateExtractedRulesUi(result.policy_json);

        stagedDecisionsData = result.staged_decisions || [];

        // Show Staged Decisions Confirmation Modal (All Rows Visible)
        openStagedModal(result);

      } catch (e) {
        alert('LangGraph エラー: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerText = '⚡ Run LangGraph Co-Pilot Agent';
      }
    }

    function openStagedModal(result) {
      document.getElementById('stage-approved-count').innerText = result.approved_count || 0;
      document.getElementById('stage-hold-count').innerText = result.hold_count || 0;
      document.getElementById('stage-total-count').innerText = result.evaluated_count || 0;

      currentStagedFilter = 'all';
      expandedStagedRows.clear();
      filterStagedRows('all');

      document.getElementById('staged-modal').style.display = 'flex';
    }

    function closeStagedModal() {
      document.getElementById('staged-modal').style.display = 'none';
    }

    function filterStagedRows(filterType) {
      currentStagedFilter = filterType;
      document.getElementById('btn-filter-all').classList.toggle('active', filterType === 'all');
      document.getElementById('btn-filter-approved').classList.toggle('active', filterType === 'approved');
      document.getElementById('btn-filter-hold').classList.toggle('active', filterType === 'hold');

      const search = (document.getElementById('staged-search-input').value || '').toLowerCase().trim();

      const tbody = document.getElementById('staged-preview-body');
      const filtered = stagedDecisionsData.map((d, idx) => ({ ...d, originalIdx: idx })).filter(d => {
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

      tbody.innerHTML = filtered.map(d => {
        const idx = d.originalIdx;
        const isExpanded = expandedStagedRows.has(d.id);
        const detailHtml = isExpanded ? `
          <tr id="detail-row-${d.id}" style="background: #f8fafc;">
            <td colspan="6" style="padding: 8px 14px;">
              <div class="row-detail-box">
                <div><strong>伝票ID:</strong> ${d.id}</div>
                <div><strong>取引先/従業員:</strong> ${d.entity_name || '-'}</div>
                <div><strong>申請金額:</strong> <span style="color: #1e3a8a; font-weight: 700;">${d.amount || ('¥' + (d.raw_amount || 0).toLocaleString())}</span></div>
                <div><strong>伝票区分:</strong> ${d.type || '-'}</div>
                <div><strong>照合伝票・注文番号:</strong> ${d.ref || '-'}</div>
                <div><strong>適用判定ルール:</strong> <span style="color: #1e40af; font-weight: 700;">[${d.matched_rule_id || 'RULE'}] ${d.matched_rule_summary || ''}</span></div>
                <div style="grid-column: span 2;"><strong>判定事由 / 指摘事項:</strong> ${(d.reasons || []).join(' / ') || '契約・規程整合確認済'}</div>
                <div style="grid-column: span 2;"><strong>LLM監査コメント:</strong> <span style="color: #047857;">${d.comment || '-'}</span></div>
              </div>
            </td>
          </tr>
        ` : '';

        return `
          <tr>
            <td style="text-align: center;">
              <button class="btn-detail-toggle" onclick="toggleStagedDetail('${d.id}')" title="伝票の詳細情報を表示">
                ${isExpanded ? '▲' : 'ℹ️'}
              </button>
            </td>
            <td><strong>${d.id}</strong></td>
            <td>${d.entity_name || '-'}</td>
            <td style="color: #1e3a8a; font-weight: 700;">${d.amount || ('¥' + (d.raw_amount || 0).toLocaleString())}</td>
            <td>
              <select class="form-control" style="padding:2px 4px; font-size:11px;" onchange="updateStagedDecisionStatus(${idx}, this.value)">
                <option value="${d.new_status}" selected>${d.new_status}</option>
                <option value="${d.new_status === 'Hold' ? (currentSuite === 'invoice' ? 'Approved' : 'Confirmed') : 'Hold'}">
                  ${d.new_status === 'Hold' ? (currentSuite === 'invoice' ? 'Approved' : 'Confirmed') : 'Hold'}
                </option>
              </select>
            </td>
            <td>
              <div style="font-size: 10px; color: #1e40af; font-weight: 600; margin-bottom: 2px;">
                [${d.matched_rule_id || 'RULE'}] ${d.matched_rule_summary || ''}
              </div>
              <input type="text" class="form-control" style="font-size:11px; padding:2px 6px;" value="${d.comment || ''}" onchange="updateStagedDecisionComment(${idx}, this.value)">
            </td>
          </tr>
          ${detailHtml}
        `;
      }).join('');
    }

    function toggleStagedDetail(id) {
      if (expandedStagedRows.has(id)) {
        expandedStagedRows.delete(id);
      } else {
        expandedStagedRows.add(id);
      }
      filterStagedRows(currentStagedFilter);
    }

    function updateStagedDecisionStatus(idx, val) {
      if (stagedDecisionsData[idx]) stagedDecisionsData[idx].new_status = val;
    }
    function updateStagedDecisionComment(idx, val) {
      if (stagedDecisionsData[idx]) stagedDecisionsData[idx].comment = val;
    }

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
        document.getElementById('graph-overall-badge').innerText = commitRes.overall_status || 'SUCCESS';
        document.getElementById('graph-overall-badge').style.background = commitRes.overall_status === 'SUCCESS' ? '#dcfce7' : '#fef3c7';

        // Render sober corporate human intervention cards if any
        const discrepancies = commitRes.discrepancies || [];
        const cont = document.getElementById('interventions-container');
        const list = document.getElementById('interventions-list');
        if (discrepancies.length > 0) {
          cont.style.display = 'block';
          list.innerHTML = discrepancies.map(d => `
            <div class="intervention-card">
              <div class="intervention-header">
                <span class="intervention-title">伝票: <strong>${d.id}</strong> (${d.name || ''}) - ${d.amount || ''}</span>
                <span class="intervention-rule-badge">[${d.rule_id || 'RULE'}] ${d.rule_summary || ''}</span>
              </div>
              <div class="intervention-reason">${(d.reasons || []).join(' / ')}</div>
              <div style="display: flex; justify-content: flex-end; gap: 6px;">
                <button class="btn-override" onclick="overrideRow('${d.id}', '${currentSuite === 'invoice' ? 'Approved' : 'Confirmed'}')">
                  承認確認 (Approve Override)
                </button>
              </div>
            </div>
          `).join('');
        } else {
          cont.style.display = 'none';
        }

        // Refresh live database table
        loadTableData();

      } catch (e) {
        alert('DBコミットエラー: ' + e);
      }
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

    /* --- Add Record Modal (Single + Bulk) --- */
    function openAddRecordModal() {
      switchAddTab('single');
      renderSingleAddForm();
      document.getElementById('add-modal').style.display = 'flex';
    }

    function closeAddRecordModal() {
      document.getElementById('add-modal').style.display = 'none';
      parsedBulkData = [];
    }

    function switchAddTab(tab) {
      const isSingle = (tab === 'single');
      document.getElementById('tab-add-single').classList.toggle('active', isSingle);
      document.getElementById('tab-add-bulk').classList.toggle('active', !isSingle);
      document.getElementById('add-single-form').style.display = isSingle ? 'block' : 'none';
      document.getElementById('add-bulk-form').style.display = isSingle ? 'none' : 'block';
      document.getElementById('btn-submit-add').innerText = isSingle ? 'データベースへ登録' : '一括登録実行 (Bulk Insert)';
    }

    function renderSingleAddForm() {
      const container = document.getElementById('add-single-form');
      if (currentSuite === 'invoice') {
        const nextId = `P6-07010448-${(invoiceRecords.length + 1).toString().padStart(3, '0')}`;
        container.innerHTML = `
          <div class="form-group"><label>伝票番号 (ID):</label><input type="text" id="add-inv-id" class="form-control" value="${nextId}"></div>
          <div class="form-group"><label>取引先コード (Vendor Code):</label><input type="text" id="add-inv-code" class="form-control" value="V3005"></div>
          <div class="form-group"><label>取引先名称 (Vendor Name):</label><input type="text" id="add-inv-name" class="form-control" placeholder="例: 日本情報通信株式会社"></div>
          <div class="form-group"><label>請求金額 (Amount in JPY):</label><input type="number" id="add-inv-amt" class="form-control" placeholder="例: 850000"></div>
          <div class="form-group"><label>伝票区分 (Classification):</label>
            <select id="add-inv-type" class="form-control">
              <option value="Routine" selected>Routine (定額・通常取引)</option>
              <option value="Adjustment">Adjustment (変動・調整取引)</option>
            </select>
          </div>
        `;
      } else {
        const nextId = `P4-07089771-${(payrollRecords.length + 1).toString().padStart(3, '0')}`;
        container.innerHTML = `
          <div class="form-group"><label>伝票番号 (ID):</label><input type="text" id="add-pay-id" class="form-control" value="${nextId}"></div>
          <div class="form-group"><label>従業員番号 (Employee ID):</label><input type="text" id="add-pay-code" class="form-control" value="EMP-021"></div>
          <div class="form-group"><label>従業員氏名 (Employee Name):</label><input type="text" id="add-pay-name" class="form-control" placeholder="例: 山本 健太"></div>
          <div class="form-group"><label>手当・経費項目 (Category):</label>
            <select id="add-pay-cat" class="form-control">
              <option value="研修費">研修費</option>
              <option value="消耗品費">消耗品費</option>
              <option value="出張旅費">出張旅費</option>
              <option value="交通費精算">交通費精算</option>
              <option value="残業手当調整">残業手当調整</option>
              <option value="昇給">昇給</option>
              <option value="扶養控除変更">扶養控除変更</option>
              <option value="役職手当新設">役職手当新設</option>
              <option value="役職手当廃止">役職手当廃止</option>
            </select>
          </div>
          <div class="form-group"><label>加算/控除区分 (Item Type):</label>
            <select id="add-pay-type" class="form-control">
              <option value="Addition" selected>Addition (支給・加算)</option>
              <option value="Deduction">Deduction (控除・減算)</option>
            </select>
          </div>
          <div class="form-group"><label>金額 (Amount in JPY):</label><input type="number" id="add-pay-amt" class="form-control" placeholder="例: 75000"></div>
        `;
      }
    }

    function previewBulkSpreadsheet() {
      const text = document.getElementById('bulk-paste-text').value.trim();
      if (!text) {
        alert('貼り付けデータがありません。');
        return;
      }

      const lines = text.split('\n').filter(l => l.trim().length > 0);
      parsedBulkData = [];

      lines.forEach((line, idx) => {
        const parts = line.includes('\t') ? line.split('\t') : line.split(',');
        if (parts.length >= 3) {
          if (currentSuite === 'invoice') {
            const id = parts[0].trim() || `P6-07010448-${(invoiceRecords.length + idx + 1).toString().padStart(3, '0')}`;
            const code = parts[1].trim() || 'V3001';
            const name = parts[2].trim() || '新規取引先';
            const rawAmt = parseInt(parts[3] ? parts[3].replace(/[¥,]/g, '').trim() : '0', 10) || 100000;
            const type = parts[4] ? parts[4].trim() : 'Routine';

            parsedBulkData.push({
              id: id,
              employee_id: code,
              name: name,
              raw_amount: rawAmt,
              amount: '¥' + rawAmt.toLocaleString(),
              type: type,
              status: 'Unprocessed'
            });
          } else {
            const id = parts[0].trim() || `P4-07089771-${(payrollRecords.length + idx + 1).toString().padStart(3, '0')}`;
            const code = parts[1].trim() || 'EMP-001';
            const name = parts[2].trim() || '新規従業員';
            const cat = parts[3] ? parts[3].trim() : '経費精算';
            const rawAmt = parseInt(parts[4] ? parts[4].replace(/[¥,]/g, '').trim() : '0', 10) || 50000;
            const type = parts[5] ? parts[5].trim() : (cat.includes('控除') ? 'Deduction' : 'Addition');

            parsedBulkData.push({
              id: id,
              employee_id: code,
              employee_name: name,
              item_category: cat,
              item_type: type,
              raw_amount: rawAmt,
              amount: '¥' + rawAmt.toLocaleString(),
              status: 'Unprocessed'
            });
          }
        }
      });

      const summary = document.getElementById('bulk-preview-summary');
      const tableHead = document.getElementById('bulk-preview-head');
      const tableBody = document.getElementById('bulk-preview-body');
      const container = document.getElementById('bulk-preview-container');

      summary.innerText = `解析完了: ${parsedBulkData.length} 件の伝票データを抽出`;
      container.style.display = 'block';

      if (currentSuite === 'invoice') {
        tableHead.innerHTML = `<tr><th>ID</th><th>コード</th><th>企業名</th><th>金額</th><th>区分</th></tr>`;
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(r => `
          <tr><td>${r.id}</td><td>${r.employee_id}</td><td>${r.name}</td><td>${r.amount}</td><td>${r.type}</td></tr>
        `).join('') + (parsedBulkData.length > 15 ? `<tr><td colspan="5" style="text-align:center;">... 他 ${parsedBulkData.length - 15} 件 ...</td></tr>` : '');
      } else {
        tableHead.innerHTML = `<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>項目</th><th>区分</th><th>金額</th></tr>`;
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(r => `
          <tr><td>${r.id}</td><td>${r.employee_id}</td><td>${r.employee_name}</td><td>${r.item_category}</td><td>${r.item_type}</td><td>${r.amount}</td></tr>
        `).join('') + (parsedBulkData.length > 15 ? `<tr><td colspan="6" style="text-align:center;">... 他 ${parsedBulkData.length - 15} 件 ...</td></tr>` : '');
      }
    }

    function handleBulkFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        document.getElementById('bulk-paste-text').value = e.target.result;
        previewBulkSpreadsheet();
      };
      reader.readAsText(file);
    }

    async function submitAddRecord() {
      const isSingle = document.getElementById('tab-add-single').classList.contains('active');

      if (isSingle) {
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

      } else {
        // Bulk import
        if (!parsedBulkData || parsedBulkData.length === 0) {
          previewBulkSpreadsheet();
        }
        if (!parsedBulkData || parsedBulkData.length === 0) {
          alert('登録するデータがありません。Excelデータを貼り付けてください。');
          return;
        }

        const url = (currentSuite === 'invoice') ? '/api/invoices/bulk-add' : '/api/payroll-items/bulk-add';
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ records: parsedBulkData })
          });
          const d = await res.json();
          if (d.success) {
            alert(`一括取込完了: ${d.count} 件のデータを登録しました。`);
            closeAddRecordModal();
            loadTableData();
          } else {
            alert('一括取込に失敗しました。');
          }
        } catch (e) {
          alert('エラー: ' + e);
        }
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
          statusDiv.innerText = `✓ 読込完了: ${data.filename} (${data.text.length} 文字)`;
          switchWsTab('notepad');
        } else {
          statusDiv.innerText = 'エラー: ' + (data.error || '不明なエラー');
        }
      } catch (e) {
        statusDiv.innerText = 'アップロードエラー: ' + e;
      }
    }

    /* --- Excel Export Handler --- */
    function exportToExcel() {
      window.location.href = `/api/export-excel/${currentSuite}`;
    }

    /* --- Database Management --- */
    function openDbModal() { document.getElementById('db-modal').style.display = 'flex'; }
    function closeDbModal() { document.getElementById('db-modal').style.display = 'none'; }

    async function connectCustomDb() {
      const uri = document.getElementById('db-uri-input').value.trim();
      if (!uri) { alert('PostgreSQL URI を入力してください。'); return; }
      try {
        const res = await fetch('/api/database/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: uri })
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
      if (!confirm('データベースを初期ベンチマーク状態（105件＋エッジケース）にリセットしますか？')) return;
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
    function openLlmModal() { document.getElementById('llm-modal').style.display = 'flex'; }
    function closeLlmModal() { document.getElementById('llm-modal').style.display = 'none'; }

    function onLlmProviderChange() {
      const prov = document.getElementById('llm-provider-select').value;
      const modelInput = document.getElementById('llm-model-input');
      if (prov === 'puter') modelInput.value = 'gpt-4o-mini';
      else if (prov === 'openai') modelInput.value = 'gpt-4o-mini';
      else if (prov === 'anthropic') modelInput.value = 'claude-3-5-sonnet-20241022';
      else if (prov === 'local') modelInput.value = 'jsox-emulator-v1';
    }

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
          box.innerText = `✓ 接続成功 (${d.latency_s}s): ${d.message}`;
          updateSystemStatus();
        } else {
          box.style.background = '#fee2e2';
          box.style.color = '#991b1b';
          box.innerText = `✕ 接続失敗: ${d.message}`;
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

    /* --- Visual Graph Helper Functions --- */
    function resetGraphUi() {
      for (let i = 1; i <= 4; i++) {
        const n = document.getElementById('node-' + i);
        n.className = 'graph-node node-pending';
        document.getElementById('time-node-' + i).innerText = '-';
      }
      document.getElementById('graph-overall-badge').innerText = 'READY';
      document.getElementById('graph-overall-badge').style.background = '#e2e8f0';
    }

    function setNodeActive(id) {
      const n = document.getElementById(id);
      if (n) {
        n.className = 'graph-node node-active';
      }
    }

    function setNodeDone(id, durationStr) {
      const n = document.getElementById(id);
      if (n) {
        n.className = 'graph-node node-done';
        const t = n.querySelector('span:last-child');
        if (t) t.innerText = durationStr;
      }
    }
  </script>
</body>
</html>
"""

# --- Flask Endpoints ---

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
    url = data.get("url", "")
    res = db_manager.set_custom_database(url)
    return jsonify(res)

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

@app.route("/api/master/regulations", methods=["GET"])
def get_regulations_route():
    return jsonify(get_master_regulations())

@app.route("/api/master/regulations", methods=["POST"])
def save_regulations_route():
    data = request.json or {}
    regs = data.get("regulations") or (data if isinstance(data, list) else [])
    ok = save_master_regulations(regs)
    return jsonify({"success": ok, "count": len(regs)})

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

@app.route("/api/copilot/evaluate", methods=["POST"])
def evaluate_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    doc_text = data.get("document_text", "")
    filename = data.get("filename_or_title", "Policy Document")

    result = copilot_engine.evaluate(
        process_type=process_type,
        document_text=doc_text,
        filename_or_title=filename
    )
    return jsonify(result)

@app.route("/api/copilot/commit", methods=["POST"])
def commit_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    decisions = data.get("decisions", [])

    result = copilot_engine.commit_staged(
        process_type=process_type,
        decisions=decisions
    )
    return jsonify(result)

@app.route("/api/copilot/run", methods=["POST"])
def run_copilot():
    data = request.json or {}
    process_type = data.get("process_type", "invoice")
    doc_text = data.get("document_text", "")
    filename = data.get("filename_or_title", "Policy Document")

    result = copilot_engine.run(
        process_type=process_type,
        document_text=doc_text,
        filename_or_title=filename
    )
    return jsonify(result)

@app.route("/api/item/override", methods=["POST"])
def override_item():
    data = request.json or {}
    suite = data.get("suite", "invoice")
    item_id = data.get("id")
    status = data.get("status")
    comment = data.get("comment", "Manual Administrator Override")

    if suite == "invoice":
        ok = db_manager.update_invoice_status(item_id, status, comment)
    else:
        ok = db_manager.update_payroll_item_status(item_id, status, comment)

    return jsonify({"success": ok})

@app.route("/api/llm/status")
def llm_status():
    return jsonify(llm_service.get_status())

@app.route("/api/llm/test", methods=["POST"])
def test_llm():
    data = request.json or {}
    provider = data.get("provider", "puter")
    token = data.get("token") or os.environ.get("PUTER_AUTH_TOKEN", "")
    model = data.get("model", "gpt-4o-mini")

    llm_service.configure(provider, token, model)
    res = llm_service.test_connection()
    return jsonify(res)

@app.route("/api/llm/save", methods=["POST"])
def save_llm():
    data = request.json or {}
    provider = data.get("provider", "puter")
    token = data.get("token") or ""
    model = data.get("model", "gpt-4o-mini")

    llm_service.configure(provider, token, model)
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
                    r.get("id"), r.get("employee_id"), r.get("name"), r.get("invoice_no"),
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
    app.run(host="0.0.0.0", port=port, debug=False)
