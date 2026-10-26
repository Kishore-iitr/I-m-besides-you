"""
Web Application: Financial Accounting & Enterprise Invoice Processing Portal
Version 2 Architecture: LangGraph AI Routing Agent + Supabase PostgreSQL
Human-in-the-Loop Review Modal & Staged Pre-Commit Pipeline
Port: 5136
"""

import os
import sys
import json
import time
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string
from sqlalchemy import text

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Remove script directory from sys.path temporarily so langgraph imports from site-packages
_this_dir = str(Path(__file__).resolve().parent)
_removed = False
if sys.path and sys.path[0] == _this_dir:
    sys.path.pop(0)
    _removed = True

from langgraph.graph import StateGraph, END

if _removed:
    sys.path.insert(0, _this_dir)

import importlib.util

_langgraph_file = Path(__file__).resolve().parent / "langgraph_v2.py"
_spec = importlib.util.spec_from_file_location("local_langgraph_engine", _langgraph_file)
_agent_mod = importlib.util.module_from_spec(_spec)
sys.modules["local_langgraph_engine"] = _agent_mod
_spec.loader.exec_module(_agent_mod)

engine = _agent_mod.engine
processing_agent = _agent_mod.processing_agent
processing_agent_detailed = _agent_mod.processing_agent_detailed
stage_agent_decisions = _agent_mod.stage_agent_decisions
stage_unprocessed_as_hold = _agent_mod.stage_unprocessed_as_hold
commit_staged_decisions = _agent_mod.commit_staged_decisions
structured_llm = _agent_mod.structured_llm
openai_api_key = _agent_mod.openai_api_key

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# ------------------------------------------------------------------------------
# Database Helper Functions
# ------------------------------------------------------------------------------
def fetch_invoices_from_db(status_filter=None, search_query=None):
    """Fetches invoice records from PostgreSQL erp_invoices / orders."""
    sql = """
        SELECT 
            id, 
            employee_id, 
            name, 
            invoice_no, 
            amount, 
            raw_amount, 
            type, 
            status, 
            ref, 
            comment, 
            updated_at 
        FROM erp_invoices
    """
    conditions = []
    params = {}

    if status_filter and status_filter.lower() != "all":
        conditions.append("LOWER(status) = :status")
        params["status"] = status_filter.lower()

    if search_query:
        conditions.append("""(
            name ILIKE :q OR 
            invoice_no ILIKE :q OR 
            id ILIKE :q OR 
            employee_id ILIKE :q OR 
            type ILIKE :q
        )""")
        params["q"] = f"%{search_query}%"

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id ASC;"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        invoices = []
        for r in rows:
            invoices.append({
                "id": r[0],
                "employee_id": r[1] or "",
                "name": r[2] or "",
                "invoice_no": r[3] or "",
                "amount": r[4] or (f"¥{r[5]:,}" if r[5] else "¥0"),
                "raw_amount": r[5] or 0,
                "type": r[6] or "Routine",
                "status": r[7] or "unprocessed",
                "ref": r[8] or "",
                "comment": r[9] or "",
                "updated_at": str(r[10]) if r[10] else ""
            })
        return invoices

def fetch_invoice_counts():
    """Returns status distribution counts."""
    sql = "SELECT LOWER(status) as st, COUNT(*) FROM erp_invoices GROUP BY LOWER(status);"
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
        counts = {"unprocessed": 0, "approved": 0, "hold": 0, "total": 0}
        for st, cnt in rows:
            if st in counts:
                counts[st] = cnt
            counts["total"] += cnt
        return counts

# ------------------------------------------------------------------------------
# Frontend HTML Template (Matches Dataset B Real Screenshots & Staged Modal)
# ------------------------------------------------------------------------------
PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>財務会計システム - 請求書承認・処理 (Version 2 LangGraph Portal)</title>
  <style>
    :root {
      --primary: #1e3a8a;
      --primary-hover: #1e40af;
      --accent: #0284c7;
      --bg-main: #f8fafc;
      --bg-card: #ffffff;
      --border-color: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --success: #15803d;
      --success-bg: #dcfce7;
      --warning: #b45309;
      --warning-bg: #fef3c7;
      --danger: #b91c1c;
      --danger-bg: #fee2e2;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    html, body { height: 100%; overflow: hidden; background-color: #f1f5f9; color: var(--text-main); font-size: 13px; }
    body { display: flex; flex-direction: column; }

    /* Corporate Header */
    header.portal-header {
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      height: 56px;
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .header-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-logo-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #1e3a8a, #0284c7);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 800;
      font-size: 15px;
      letter-spacing: -0.5px;
    }

    .header-title-box {
      display: flex;
      flex-direction: column;
    }

    .header-title {
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: -0.2px;
    }

    .header-subtitle {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Live Pills */
    .header-pills {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-pill {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      border: 1px solid transparent;
    }

    .status-pill.db { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
    .status-pill.agent { background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }
    .status-pill.llm { background: #faf5ff; color: #7e22ce; border-color: #e9d5ff; }
    .status-pill .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn {
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 5px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      border: 1px solid transparent;
    }

    .btn-secondary {
      background: #ffffff;
      border: 1px solid var(--border-color);
      color: #334155;
    }
    .btn-secondary:hover { background: #f8fafc; border-color: #94a3b8; }
    .btn-secondary.active { background: #1e3a8a; color: #ffffff; border-color: #1e3a8a; }

    .btn-primary {
      background: var(--primary);
      color: #ffffff;
    }
    .btn-primary:hover { background: var(--primary-hover); }

    .btn-success {
      background: var(--success);
      color: #ffffff;
    }
    .btn-success:hover { background: #166534; }

    .btn-danger {
      background: var(--danger);
      color: #ffffff;
    }
    .btn-danger:hover { background: #991b1b; }

    /* Action buttons in Table */
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
    }
    .btn-action-hold:hover {
      background: #ef4444;
      color: #ffffff;
      border-color: #ef4444;
      transform: translateY(-1px);
    }

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
      background: #16a34a;
      color: #ffffff;
      border-color: #16a34a;
      transform: translateY(-1px);
    }

    /* Main Split Layout */
    .main-layout {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    /* Left Section: Real Accounting Invoice Table */
    .erp-pane {
      flex: 6.2;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border-color);
      background: #ffffff;
      overflow: hidden;
    }

    .table-top-bar {
      padding: 10px 16px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: #f8fafc;
      flex-shrink: 0;
    }

    .search-input {
      width: 240px;
      padding: 6px 10px;
      font-size: 12px;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      background: #ffffff;
      outline: none;
    }
    .search-input:focus { border-color: var(--accent); }

    .filter-tabs {
      display: flex;
      gap: 4px;
    }

    .filter-btn {
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 4px;
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: #475569;
      cursor: pointer;
    }
    .filter-btn.active {
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
    }

    /* Metric Summary Bar */
    .metric-summary-bar {
      padding: 8px 16px;
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      gap: 12px;
      flex-shrink: 0;
    }

    .metric-card {
      flex: 1;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: #ffffff;
      display: flex;
      flex-direction: column;
    }

    .metric-card.unprocessed { border-left: 4px solid #64748b; }
    .metric-card.approved { border-left: 4px solid var(--success); }
    .metric-card.hold { border-left: 4px solid var(--danger); }
    .metric-card.total { border-left: 4px solid var(--accent); }

    .metric-card-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 2px;
    }

    .metric-card-val {
      font-size: 18px;
      font-weight: 800;
      color: #0f172a;
    }

    /* Table Container */
    .table-container {
      flex: 1;
      overflow-y: auto;
      background: #ffffff;
    }

    table.invoice-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    table.invoice-table thead th {
      position: sticky;
      top: 0;
      background: #f1f5f9;
      padding: 8px 12px;
      font-size: 11px;
      font-weight: 700;
      color: #334155;
      border-bottom: 1px solid var(--border-color);
      z-index: 5;
    }

    table.invoice-table tbody tr {
      border-bottom: 1px solid #f1f5f9;
      transition: background 0.1s ease;
    }
    table.invoice-table tbody tr:hover {
      background: #f8fafc;
    }

    table.invoice-table td {
      padding: 7px 12px;
      font-size: 12px;
      color: #1e293b;
      vertical-align: middle;
    }

    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-align: center;
    }
    .badge-unprocessed { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .badge-approved { background: var(--success-bg); color: var(--success); border: 1px solid #bbf7d0; }
    .badge-hold { background: var(--danger-bg); color: var(--danger); border: 1px solid #fecaca; }

    .btn-table-action {
      padding: 3px 8px;
      font-size: 11px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      border-radius: 4px;
      cursor: pointer;
      color: #1e3a8a;
      font-weight: 600;
    }
    .btn-table-action:hover { background: #eff6ff; border-color: #93c5fd; }

    /* Right Section: AI Routing Agent Pane */
    .agent-pane {
      flex: 4.8;
      display: flex;
      flex-direction: column;
      background: #f8fafc;
      overflow: hidden;
    }

    .agent-header {
      padding: 12px 16px;
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }

    .agent-title {
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .agent-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .agent-intro-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 11px;
      line-height: 1.5;
      color: #475569;
    }

    .prompt-box {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .prompt-label {
      font-size: 11px;
      font-weight: 700;
      color: #334155;
    }

    .prompt-textarea {
      width: 100%;
      height: 60px;
      padding: 8px 10px;
      font-size: 12px;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      outline: none;
      resize: vertical;
      font-family: inherit;
    }
    .prompt-textarea:focus { border-color: var(--accent); }

    .quick-triggers {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    .trigger-chip {
      font-size: 10.5px;
      padding: 3px 8px;
      border-radius: 12px;
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      color: #334155;
      cursor: pointer;
      transition: all 0.1s ease;
    }
    .trigger-chip:hover {
      background: #e2e8f0;
      color: #0f172a;
    }

    /* Pipeline Status Card */
    .pipeline-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 12px;
    }

    .pipeline-title {
      font-size: 11px;
      font-weight: 700;
      color: #475569;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
    }

    .graph-nodes {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .graph-node {
      flex: 1;
      padding: 6px 4px;
      border-radius: 4px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      text-align: center;
      font-size: 10px;
      color: #64748b;
      transition: all 0.2s ease;
    }
    .graph-node.active {
      background: #eff6ff;
      border-color: #3b82f6;
      color: #1d4ed8;
      font-weight: 700;
    }
    .graph-node.success {
      background: #f0fdf4;
      border-color: #22c55e;
      color: #15803d;
      font-weight: 700;
    }
    .graph-node.warning {
      background: #fffbeb;
      border-color: #f59e0b;
      color: #b45309;
      font-weight: 700;
    }

    /* Per-Rule Distinct Cards */
    .rule-card {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-left: 4px solid var(--accent);
      border-radius: 6px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .rule-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      font-weight: 700;
      color: #1e3a8a;
    }

    .rule-action-badge {
      font-size: 10px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 3px;
      text-transform: uppercase;
    }
    .action-badge-approved { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .action-badge-hold { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

    .rule-sql-box {
      background: #0f172a;
      color: #38bdf8;
      border-radius: 4px;
      padding: 6px 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      line-height: 1.4;
      overflow-x: auto;
    }

    .rule-card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 2px;
    }

    .rule-result-pill {
      font-size: 10.5px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .pill-success { background: #dcfce7; color: #15803d; }
    .pill-warning { background: #fef3c7; color: #b45309; }
    .pill-info { background: #e0f2fe; color: #0369a1; }

    /* Terminal Box */
    .terminal-box {
      background: #0f172a;
      border-radius: 6px;
      padding: 10px 12px;
      color: #e2e8f0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      line-height: 1.5;
      height: 140px;
      overflow-y: auto;
    }

    .terminal-line { margin-bottom: 3px; white-space: pre-wrap; word-break: break-all; }
    .terminal-line.success { color: #4ade80; }
    .terminal-line.warning { color: #fbbf24; }
    .terminal-line.error { color: #f87171; }

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
      width: 580px;
      max-width: 90vw;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      border: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: modalFadeIn 0.15s ease-out;
    }

    .modal-card.large {
      width: 920px;
      max-width: 95vw;
    }

    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.97); }
      to { opacity: 1; transform: scale(1); }
    }

    .modal-header {
      background: #f8fafc;
      border-bottom: 1px solid var(--border-color);
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
    }

    .modal-body {
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      max-height: 80vh;
    }

    .modal-footer {
      background: #f8fafc;
      border-top: 1px solid var(--border-color);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
    }

    /* Staged Decisions Expandable Row Detail */
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

    /* Compact ERP Staging Table */
    .erp-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11.5px;
    }
    .erp-table th {
      background: #f1f5f9;
      padding: 6px 10px;
      font-weight: 700;
      color: #334155;
      border-bottom: 1px solid #cbd5e1;
      text-align: left;
    }
    .erp-table td {
      padding: 6px 10px;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: middle;
    }

    /* Voucher Modal Grid */
    .voucher-details-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 12px;
    }

    .detail-item {
      display: flex;
      flex-direction: column;
    }
    .detail-label { font-size: 10.5px; color: #64748b; font-weight: 600; }
    .detail-val { font-size: 12px; font-weight: 700; color: #1e293b; margin-top: 1px; }

    .comment-textarea {
      width: 100%;
      height: 70px;
      padding: 8px 10px;
      font-size: 12px;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      outline: none;
      resize: vertical;
    }
    .comment-textarea:focus { border-color: var(--accent); }

    .quick-comment-btn {
      font-size: 10.5px;
      padding: 3px 8px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      border-radius: 4px;
      cursor: pointer;
    }
    .quick-comment-btn:hover { background: #dbeafe; }
  </style>
</head>
<body>

  <!-- Top Corporate Header -->
  <header class="portal-header">
    <div class="header-brand">
      <div class="header-logo-icon">財務</div>
      <div class="header-title-box">
        <span class="header-title">財務会計システム (Financial Accounting Portal)</span>
        <span class="header-subtitle">2026年度 経理部門 | 請求書承認・処理 (Dataset B Core SOP)</span>
      </div>
    </div>

    <!-- Live Status Indicators -->
    <div class="header-pills">
      <div class="status-pill db" title="Supabase PostgreSQL Active Connection">
        <span class="dot"></span>
        <span id="pill-db-text">PostgreSQL: Supabase Connected</span>
      </div>
      <div class="status-pill agent" title="LangGraph Routing Pipeline State">
        <span class="dot"></span>
        <span>Agent: LangGraph StateGraph (Active)</span>
      </div>
      <div class="status-pill llm" title="Deterministic LLM Engine">
        <span class="dot"></span>
        <span id="pill-llm-text">LLM: gpt-4o / Deterministic</span>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn btn-secondary" onclick="loadInvoices()" title="最新データベースへ更新">
        🔄 再読込
      </button>
      <button class="btn btn-secondary" onclick="resetDatabaseBenchmark()" title="全伝票を未処理に戻す">
        ↺ データ初期化
      </button>
    </div>
  </header>

  <!-- Main Split Layout -->
  <main class="main-layout">
    <!-- Left Pane: Invoices Data Grid -->
    <section class="erp-pane">
      <!-- Toolbar -->
      <div class="table-top-bar">
        <div style="display: flex; align-items: center; gap: 8px;">
          <input type="text" id="search-box" class="search-input" placeholder="🔍 取引先・請求書番号で検索..." oninput="handleSearch(this.value)">
          <div class="filter-tabs">
            <button class="filter-btn active" id="f-all" onclick="setFilter('all')">すべて (All)</button>
            <button class="filter-btn" id="f-unprocessed" onclick="setFilter('unprocessed')">未処理</button>
            <button class="filter-btn" id="f-approved" onclick="setFilter('approved')">承認済</button>
            <button class="filter-btn" id="f-hold" onclick="setFilter('hold')">保留</button>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <button class="btn btn-secondary" style="color: #b91c1c; border-color: #fca5a5; font-weight: 700; background: #fff1f2;" onclick="openHoldAllUnprocessedModal()" title="すべての未処理伝票を保留として確認ウィンドウを開く">
            ⚡ 未処理を保留にする (Stage Unprocessed as HOLD)
          </button>
          <span style="font-size: 11px; color: #64748b;" id="record-summary-text">読込中...</span>
        </div>
      </div>

      <!-- Metric Cards -->
      <div class="metric-summary-bar">
        <div class="metric-card unprocessed">
          <div class="metric-card-label">未処理 (Unprocessed)</div>
          <div class="metric-card-val" id="cnt-unprocessed">0</div>
        </div>
        <div class="metric-card approved">
          <div class="metric-card-label">承認済 (Approved)</div>
          <div class="metric-card-val" id="cnt-approved">0</div>
        </div>
        <div class="metric-card hold">
          <div class="metric-card-label">保留 (On Hold)</div>
          <div class="metric-card-val" id="cnt-hold">0</div>
        </div>
        <div class="metric-card total">
          <div class="metric-card-label">伝票総数 (Total)</div>
          <div class="metric-card-val" id="cnt-total">0</div>
        </div>
      </div>

      <!-- Invoices Table -->
      <div class="table-container">
        <table class="invoice-table">
          <thead>
            <tr>
              <th style="width: 135px;">伝票ID (Voucher)</th>
              <th style="width: 125px;">請求書番号 (Invoice)</th>
              <th style="width: 85px;">取引先コード</th>
              <th>取引先名称 (Vendor)</th>
              <th style="width: 100px;">請求金額</th>
              <th style="width: 80px;">区分</th>
              <th style="width: 75px;">状態</th>
              <th>照合コメント</th>
              <th style="width: 155px; text-align: center;">操作 (Actions)</th>
            </tr>
          </thead>
          <tbody id="invoice-table-body">
            <!-- Dynamically populated rows -->
          </tbody>
        </table>
      </div>
    </section>

    <!-- Right Pane: AI Routing Agent (Version 2 Architecture) -->
    <aside class="agent-pane">
      <div class="agent-header">
        <div class="agent-title">
          <span>🤖 LangGraph Database Routing Agent (Version 2)</span>
        </div>
        <span style="font-size: 11px; color: #166534; background: #dcfce7; padding: 2px 8px; border-radius: 10px; font-weight: 700;">
          Human-in-the-Loop Active
        </span>
      </div>

      <div class="agent-body">
        <!-- Architecture Explanation Box -->
        <div class="agent-intro-box">
          <strong>⚡ Version 2 Multi-Rule & Staging Architecture:</strong><br>
          1. <strong>Independent Rules:</strong> Decomposes requests into distinct, readable rules instead of giant mixed SQL queries.<br>
          2. <strong>One-by-One Search:</strong> Each clean, standalone SQL SELECT command executes independently on PostgreSQL.<br>
          3. <strong>Pre-Commit Review Window:</strong> Candidate records are staged and displayed in a confirmation modal with all details before DB write.<br>
          4. <strong>Safe User Commit:</strong> Changes are only committed to PostgreSQL when the user clicks "Commit to Database".
        </div>

        <!-- Quick Triggers Chips -->
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <span class="prompt-label">⚡ クイックトリガー (Quick Example Prompts):</span>
          <div class="quick-triggers">
            <button class="trigger-chip" onclick="setPrompt('Unprocessed details can directly be changed as HOLD')">
              ⚡ 未処理伝票をすべて保留 (Change Unprocessed to HOLD)
            </button>
            <button class="trigger-chip" onclick="setPrompt('Approve routine invoices under 500000 yen, and put a freeze on orders over 1000000')">
              Approve routine &lt; 500k, freeze &gt; 1M
            </button>
            <button class="trigger-chip" onclick="setPrompt('Put a freeze on unprocessed orders over 1000000')">
              Freeze unprocessed orders &gt; 1,000,000
            </button>
            <button class="trigger-chip" onclick="setPrompt('Approve routine invoices for Hokuriku Parts Industry')">
              Approve Hokuriku Parts Industry
            </button>
            <button class="trigger-chip" onclick="setPrompt('Put a freeze on adjustment and spot invoices')">
              Freeze Adjustment &amp; Spot invoices
            </button>
          </div>
        </div>

        <!-- Prompt Input Form -->
        <div class="prompt-box">
          <span class="prompt-label">💬 自然言語プロンプト指示 (Natural Language Rule Directive):</span>
          <textarea id="agent-prompt" class="prompt-textarea" placeholder="例: Unprocessed details can directly be changed as HOLD"></textarea>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button class="btn btn-secondary" onclick="document.getElementById('agent-prompt').value=''">クリア</button>
            <button class="btn btn-primary" id="btn-run-agent" onclick="runAgent()">
              🚀 評価 &amp; 確認ウィンドウを開く
            </button>
          </div>
        </div>

        <!-- Horizontal LangGraph Pipeline State -->
        <div class="pipeline-card">
          <div class="pipeline-title">
            <span>📊 LangGraph StateGraph Execution Pipeline</span>
          </div>
          <div class="graph-nodes">
            <div class="graph-node" id="node-1">
              <strong>1. Parse Rules</strong><br>
              <small>Decompose to Rules</small>
            </div>
            <div class="graph-node" id="node-2">
              <strong>2. Independent SQL</strong><br>
              <small>Execute One-by-One</small>
            </div>
            <div class="graph-node" id="node-3">
              <strong>3. Stage Review</strong><br>
              <small>Modal Confirmation</small>
            </div>
            <div class="graph-node" id="node-4">
              <strong>4. User Commit</strong><br>
              <small>Commit to Database</small>
            </div>
          </div>
        </div>

        <!-- Distinct Independent Rules Cards Section -->
        <div id="rules-results-section" style="display: none; flex-direction: column; gap: 8px;">
          <span class="prompt-label">📋 分割ルール・独立SQLコマンド一覧 (Independent SQL Rules Executed):</span>
          <div id="rules-cards-container" style="display: flex; flex-direction: column; gap: 8px;">
            <!-- Dynamically populated per-rule cards -->
          </div>
        </div>

        <!-- Execution Result Log Terminal -->
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <span class="prompt-label">🖥️ 実行ログ・監査証跡 (Execution Terminal & Audit Logs):</span>
          <div class="terminal-box" id="terminal-output">
            <div class="terminal-line">[System Ready] LangGraph Routing Pipeline connected to Supabase PostgreSQL.</div>
            <div class="terminal-line">Enter a prompt above or click a quick trigger chip to run.</div>
          </div>
        </div>
      </div>
    </aside>
  </main>

  <!-- Modal 1: Staged Decision Review & Commit Confirmation (ALL Rows Visible + Info Icon) -->
  <div class="modal-overlay" id="staged-modal">
    <div class="modal-card large">
      <div class="modal-header">
        <span>⚡ 評価結果の確認 &amp; データベース反映承認 (Staged Decisions Review)</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeStagedModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="display: flex; gap: 12px; margin-bottom: 4px;">
          <div class="metric-card approved" style="flex: 1;">
            <div class="metric-card-label">承認/確認 予定 (To Approve)</div>
            <div class="metric-card-val" id="stage-approved-count">0</div>
          </div>
          <div class="metric-card hold" style="flex: 1;">
            <div class="metric-card-label">保留・精査 予定 (To Hold)</div>
            <div class="metric-card-val" id="stage-hold-count">0</div>
          </div>
          <div class="metric-card total" style="flex: 1;">
            <div class="metric-card-label">総評価件数 (Total Staged)</div>
            <div class="metric-card-val" id="stage-total-count">0</div>
          </div>
        </div>

        <!-- Filter & Search Controls in Staged Modal -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; gap: 10px;">
          <div style="display: flex; gap: 6px;">
            <button class="btn-secondary active" id="btn-stage-filter-all" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('all')">全件表示</button>
            <button class="btn-secondary" id="btn-stage-filter-approved" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('approved')">承認/確認のみ</button>
            <button class="btn-secondary" id="btn-stage-filter-hold" style="padding: 3px 10px; font-size: 11px;" onclick="filterStagedRows('hold')">保留のみ</button>
          </div>
          <input type="text" id="staged-search-input" class="search-input" style="width: 220px; padding: 4px 8px; font-size: 11px;" placeholder="伝票ID / 氏名で絞込…" oninput="filterStagedRows(currentStagedFilter)">
        </div>

        <div style="max-height: 380px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 6px;">
          <table class="erp-table">
            <thead>
              <tr>
                <th style="width: 40px; text-align: center;">詳細</th>
                <th style="width: 120px;">伝票番号</th>
                <th style="width: 140px;">取引先 / 氏名</th>
                <th style="width: 85px;">金額</th>
                <th style="width: 105px;">ステータス</th>
                <th>適用ルール &amp; コメント</th>
              </tr>
            </thead>
            <tbody id="staged-preview-body">
              <!-- Dynamically populated with candidate rows -->
            </tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeStagedModal()">キャンセル (Cancel)</button>
        <button class="btn btn-primary" style="background: var(--success); font-weight: 700;" onclick="confirmCommitStaged()">
          ✓ データベースへ反映・コミット (Commit to Database)
        </button>
      </div>
    </div>
  </div>

  <!-- Modal 2: Single Record Comments & Status Confirmation Dialog -->
  <div class="modal-overlay" id="comment-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>💬 伝票ステータス変更・確認ウィンドウ</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeCommentModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin-bottom: 4px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="color: #64748b; font-size: 11px;">伝票番号:</span>
            <strong id="modal-record-id">-</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="color: #64748b; font-size: 11px;">取引先 / 氏名:</span>
            <strong id="modal-entity-name">-</strong>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: #64748b; font-size: 11px;">金額:</span>
            <strong id="modal-amount" style="color: #1e3a8a;">-</strong>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 4px;">
          <label style="font-size: 11px; font-weight: 700; color: #475569;">承認ステータス:</label>
          <select id="modal-status-select" class="prompt-textarea" style="height: 32px; padding: 4px 8px;">
            <option value="unprocessed">未処理 (Unprocessed)</option>
            <option value="approved">承認済 (Approved)</option>
            <option value="hold">保留 (Hold)</option>
          </select>
        </div>

        <div style="display: flex; flex-direction: column; gap: 4px;">
          <label style="font-size: 11px; font-weight: 700; color: #475569;">処理内容・確認コメント:</label>
          <textarea id="modal-comment-text" class="comment-textarea" placeholder="処理内容・確認コメントを入力してください…"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeCommentModal()">キャンセル</button>
        <button class="btn btn-primary" onclick="commitCommentModal()">💾 保存してDB更新 (Commit)</button>
      </div>
    </div>
  </div>

  <!-- Modal 3: Detail Invoice Voucher Modal -->
  <div class="modal-overlay" id="voucher-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span id="modal-invoice-title">請求書承認・バウチャー照合 [INV-2026-XXXX]</span>
        <button style="border: none; background: transparent; font-size: 16px; cursor: pointer; color: #64748b;" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="voucher-details-grid">
          <div class="detail-item">
            <span class="detail-label">取引先名称 (Supplier Name)</span>
            <span class="detail-val" id="modal-vendor-name">-</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">取引先コード (Vendor Code)</span>
            <span class="detail-val" id="modal-vendor-code">-</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">請求金額 / 税抜 (Subtotal)</span>
            <span class="detail-val" id="modal-subtotal">-</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">消費税額 10% (Consumption Tax)</span>
            <span class="detail-val" id="modal-tax">-</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">税込合計請求金額 (Total Billing Sum)</span>
            <span class="detail-val" style="color: #1e3a8a; font-size: 14px;" id="modal-total-amt">-</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">会計伝票番号 (Voucher Ref)</span>
            <span class="detail-val" style="color: #0284c7;" id="modal-voucher-ref">-</span>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 6px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label style="font-size: 11px; font-weight: 700; color: #475569;">
              処理内容・確認コメント (Mandatory Verification Comment):
            </label>
            <button class="quick-comment-btn" onclick="pastePresetComment()">
              📋 定額取引先一覧照合済を挿入
            </button>
          </div>
          <textarea id="modal-comment" class="comment-textarea" placeholder="処理内容・確認コメントを入力してください…"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeModal()">閉じる</button>
        <button class="btn btn-danger" onclick="submitModalAction('hold')">⏸️ 保留 (Hold)</button>
        <button class="btn btn-success" onclick="submitModalAction('approved')">承認 (Approve)</button>
      </div>
    </div>
  </div>

  <script>
    let activeInvoices = [];
    let currentFilter = 'all';
    let currentSearch = '';
    let activeModalInvoice = null;
    let activeCommentRecord = null;

    // Staged decisions state
    let stagedDecisionsData = [];
    let currentStagedFilter = 'all';
    let expandedStagedRows = new Set();

    // Load Invoices from DB
    async function loadInvoices() {
      try {
        const url = `/api/invoices?status=${encodeURIComponent(currentFilter)}&q=${encodeURIComponent(currentSearch)}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
          activeInvoices = data.invoices;
          renderInvoiceRows(activeInvoices);
          updateMetricCards(data.counts);
          document.getElementById('record-summary-text').innerText = `${activeInvoices.length} 件表示中`;
        }
      } catch (err) {
        console.error("Failed to load invoices:", err);
      }
    }

    function renderInvoiceRows(invoices) {
      const tbody = document.getElementById('invoice-table-body');
      tbody.innerHTML = '';

      if (invoices.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #94a3b8; padding: 24px;">該当する伝票データがありません</td></tr>`;
        return;
      }

      invoices.forEach(inv => {
        const tr = document.createElement('tr');
        
        let badgeClass = 'badge-unprocessed';
        let badgeText = '未処理';
        const st = (inv.status || '').toLowerCase();
        if (st === 'approved') {
          badgeClass = 'badge-approved';
          badgeText = '承認済';
        } else if (st === 'hold') {
          badgeClass = 'badge-hold';
          badgeText = '保留';
        }

        tr.innerHTML = `
          <td><strong>${inv.id}</strong></td>
          <td><button class="btn-table-action" onclick="openVoucherModal('${inv.id}')" title="バウチャー詳細を開く">請求書承認 ${inv.invoice_no}</button></td>
          <td><code>${inv.employee_id}</code></td>
          <td><strong>${inv.name}</strong></td>
          <td style="font-weight: 700; color: #0f172a;">${inv.amount}</td>
          <td><span style="font-size: 11px; color: #475569;">${inv.type}</span></td>
          <td><span class="status-badge ${badgeClass}">${badgeText}</span></td>
          <td style="color: #64748b; font-size: 11px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${inv.comment || '-'}</td>
          <td style="text-align: center;">
            <div style="display: inline-flex; gap: 4px; align-items: center;">
              <button class="btn-action-hold" onclick="quickHoldRow('${inv.id}')" title="この伝票を保留にする確認ウィンドウを開く">✕ 保留</button>
              <button class="btn-action-approve" onclick="quickApproveRow('${inv.id}')" title="この伝票を承認する確認ウィンドウを開く">✓ 承認</button>
              <button class="btn-table-action" onclick="openVoucherModal('${inv.id}')" title="バウチャー詳細を開く">詳細</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    function updateMetricCards(counts) {
      if (!counts) return;
      document.getElementById('cnt-unprocessed').innerText = counts.unprocessed || 0;
      document.getElementById('cnt-approved').innerText = counts.approved || 0;
      document.getElementById('cnt-hold').innerText = counts.hold || 0;
      document.getElementById('cnt-total').innerText = counts.total || 0;
    }

    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById(`f-${filter}`);
      if (activeBtn) activeBtn.classList.add('active');
      loadInvoices();
    }

    function handleSearch(val) {
      currentSearch = val.trim();
      loadInvoices();
    }

    function setPrompt(p) {
      document.getElementById('agent-prompt').value = p;
    }

    // --- Modal 1: Staged Review & Human-in-the-Loop Commit Modal ---
    function openStagedModal(result) {
      try {
        stagedDecisionsData = result.staged_decisions || [];
        document.getElementById('stage-approved-count').innerText = result.approved_count || 0;
        document.getElementById('stage-hold-count').innerText = result.hold_count || 0;
        document.getElementById('stage-total-count').innerText = result.evaluated_count || 0;

        currentStagedFilter = 'all';
        expandedStagedRows.clear();
        filterStagedRows('all');

        const modal = document.getElementById('staged-modal');
        if (modal) modal.style.display = 'flex';
      } catch (err) {
        console.warn('openStagedModal error:', err);
      }
    }

    function closeStagedModal() {
      const modal = document.getElementById('staged-modal');
      if (modal) modal.style.display = 'none';
    }

    function filterStagedRows(filterType) {
      currentStagedFilter = filterType;
      const bAll = document.getElementById('btn-stage-filter-all');
      const bApp = document.getElementById('btn-stage-filter-approved');
      const bHld = document.getElementById('btn-stage-filter-hold');
      if (bAll) bAll.classList.toggle('active', filterType === 'all');
      if (bApp) bApp.classList.toggle('active', filterType === 'approved');
      if (bHld) bHld.classList.toggle('active', filterType === 'hold');

      const searchInput = document.getElementById('staged-search-input');
      const search = (searchInput ? searchInput.value : '').toLowerCase().trim();

      const tbody = document.getElementById('staged-preview-body');
      if (!tbody) return;

      const filtered = stagedDecisionsData.map((d, idx) => {
        return Object.assign({}, d, { originalIdx: idx });
      }).filter(d => {
        const isApproved = (d.new_status === 'Approved' || d.new_status === 'approved' || d.new_status === 'Confirmed');
        const isHold = (d.new_status === 'Hold' || d.new_status === 'hold');

        if (filterType === 'approved' && !isApproved) return false;
        if (filterType === 'hold' && !isHold) return false;

        if (search) {
          const matchId = (d.id || '').toLowerCase().includes(search);
          const matchInv = (d.invoice_no || '').toLowerCase().includes(search);
          const matchName = (d.entity_name || '').toLowerCase().includes(search);
          if (!matchId && !matchInv && !matchName) return false;
        }
        return true;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:16px; color:#94a3b8;">該当する候補レコードはありません</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(d => {
        const idx = d.originalIdx;
        const isExpanded = expandedStagedRows.has(d.id);
        const detailHtml = isExpanded ? `
          <tr id="detail-row-${d.id}" style="background: #f8fafc;">
            <td colspan="6" style="padding: 8px 14px;">
              <div class="row-detail-box">
                <div><strong>伝票ID:</strong> ${d.id}</div>
                <div><strong>取引先 / 氏名:</strong> ${d.entity_name || '-'}</div>
                <div><strong>請求金額:</strong> <span style="color: #1e3a8a; font-weight: 700;">${d.amount}</span></div>
                <div><strong>伝票区分:</strong> ${d.type || '-'}</div>
                <div><strong>照合伝票・注文番号:</strong> ${d.ref || '-'}</div>
                <div><strong>適用判定ルール:</strong> <span style="color: #1e40af; font-weight: 700;">[${d.matched_rule_id || 'RULE'}] ${d.matched_rule_summary || ''}</span></div>
                <div style="grid-column: span 2;"><strong>判定事由 / 指摘事項:</strong> ${(d.reasons || []).join(' / ') || '規程整合確認済'}</div>
                <div style="grid-column: span 2;"><strong>監査コメント:</strong> <span style="color: #047857;">${d.comment || '-'}</span></div>
              </div>
            </td>
          </tr>` : '';

        return `<tr>
          <td style="text-align: center;">
            <button class="btn-detail-toggle" data-id="${d.id}" onclick="toggleStagedDetail(this.dataset.id)" title="伝票の詳細情報を表示">
              ${isExpanded ? '▲' : 'ℹ️'}
            </button>
          </td>
          <td><strong>${d.invoice_no || d.id}</strong></td>
          <td>${d.entity_name || '-'}</td>
          <td style="color: #1e3a8a; font-weight: 700;">${d.amount}</td>
          <td>
            <select class="prompt-textarea" style="height: 26px; padding: 2px 4px; font-size: 11px;" onchange="updateStagedDecisionStatus(${idx}, this.value)">
              <option value="Hold" ${d.new_status.toLowerCase() === 'hold' ? 'selected' : ''}>Hold (保留)</option>
              <option value="Approved" ${d.new_status.toLowerCase() === 'approved' ? 'selected' : ''}>Approved (承認)</option>
            </select>
          </td>
          <td>
            <div style="font-size: 10px; color: #1e40af; font-weight: 600; margin-bottom: 2px;">
              [${d.matched_rule_id || 'RULE'}] ${d.matched_rule_summary || ''}
            </div>
            <input type="text" class="prompt-textarea" style="height: 24px; padding: 2px 6px; font-size: 11px; width: 100%;" value="${d.comment || ''}" onchange="updateStagedDecisionComment(${idx}, this.value)">
          </td>
        </tr>${detailHtml}`;
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
      if (stagedDecisionsData[idx]) {
        stagedDecisionsData[idx].new_status = val;
        const appCount = stagedDecisionsData.filter(d => d.new_status.toLowerCase() === 'approved').length;
        const hldCount = stagedDecisionsData.filter(d => d.new_status.toLowerCase() === 'hold').length;
        document.getElementById('stage-approved-count').innerText = appCount;
        document.getElementById('stage-hold-count').innerText = hldCount;
      }
    }

    function updateStagedDecisionComment(idx, val) {
      if (stagedDecisionsData[idx]) {
        stagedDecisionsData[idx].comment = val;
      }
    }

    async function confirmCommitStaged() {
      if (!stagedDecisionsData || stagedDecisionsData.length === 0) {
        alert("反映対象のレコードがありません。");
        return;
      }

      closeStagedModal();
      appendTerminal(`\n💾 [User Confirmed] Committing ${stagedDecisionsData.length} staged changes to PostgreSQL database...`);

      try {
        const res = await fetch('/api/agent/commit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decisions: stagedDecisionsData })
        });
        const commitRes = await res.json();

        if (commitRes.success) {
          appendTerminal(`✅ [Database Commit Succeeded] ${commitRes.message}`, 'success');
          highlightNode(4, 'success');
          loadInvoices();
        } else {
          appendTerminal(`❌ [Commit Error] ${commitRes.error || 'Failed to commit'}`, 'error');
        }
      } catch (err) {
        appendTerminal(`❌ [Commit Communication Error] ${err}`, 'error');
      }
    }

    // Direct Action: Open Modal to Stage All Unprocessed as HOLD
    async function openHoldAllUnprocessedModal() {
      appendTerminal(`\n⚡ [Action Triggered] Staging all unprocessed invoices as HOLD...`);
      try {
        const res = await fetch('/api/agent/stage-unprocessed-hold', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          appendTerminal(`🔍 Staged ${data.evaluated_count} unprocessed records for user review.`);
          highlightNode(1, 'success');
          highlightNode(2, 'success');
          highlightNode(3, 'success');
          openStagedModal(data);
        } else {
          alert("エラー: " + (data.error || "保留処理の準備に失敗しました。"));
        }
      } catch (e) {
        alert("通信エラー: " + e);
      }
    }

    // --- Modal 2: Single Record Status/Comment Confirmation Modal ---
    function quickHoldRow(id) {
      const inv = activeInvoices.find(x => x.id === id);
      if (!inv) return;
      activeCommentRecord = inv;
      document.getElementById('modal-record-id').innerText = inv.invoice_no || inv.id;
      document.getElementById('modal-entity-name').innerText = inv.name;
      document.getElementById('modal-amount').innerText = inv.amount;
      document.getElementById('modal-status-select').value = 'hold';
      document.getElementById('modal-comment-text').value = inv.comment || '[HOLD] 請求金額または契約範囲要確認につき保留';
      document.getElementById('comment-modal').style.display = 'flex';
    }

    function quickApproveRow(id) {
      const inv = activeInvoices.find(x => x.id === id);
      if (!inv) return;
      activeCommentRecord = inv;
      document.getElementById('modal-record-id').innerText = inv.invoice_no || inv.id;
      document.getElementById('modal-entity-name').innerText = inv.name;
      document.getElementById('modal-amount').innerText = inv.amount;
      document.getElementById('modal-status-select').value = 'approved';
      document.getElementById('modal-comment-text').value = inv.comment || '月次定額取引先一覧照合済・金額一致確認';
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
        const res = await fetch(`/api/invoices/${encodeURIComponent(activeCommentRecord.id)}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: status, comment: comment })
        });
        const d = await res.json();
        if (d.success) {
          appendTerminal(`✅ [Record Updated] ${activeCommentRecord.id} -> ${status.toUpperCase()}`, 'success');
          closeCommentModal();
          loadInvoices();
        } else {
          alert("エラー: " + (d.error || "更新に失敗しました。"));
        }
      } catch (e) {
        alert("通信エラー: " + e);
      }
    }

    // --- Modal 3: Voucher Modal Operations ---
    function openVoucherModal(id) {
      const inv = activeInvoices.find(x => x.id === id);
      if (!inv) return;
      activeModalInvoice = inv;

      document.getElementById('modal-invoice-title').innerText = `請求書承認・バウチャー照合 [${inv.invoice_no}]`;
      document.getElementById('modal-vendor-name').innerText = inv.name;
      document.getElementById('modal-vendor-code').innerText = inv.employee_id;
      
      const raw = inv.raw_amount || 0;
      const tax = Math.round(raw * 0.1);
      const total = raw + tax;

      document.getElementById('modal-subtotal').innerText = `¥${raw.toLocaleString()}`;
      document.getElementById('modal-tax').innerText = `¥${tax.toLocaleString()}`;
      document.getElementById('modal-total-amt').innerText = `¥${total.toLocaleString()}`;
      document.getElementById('modal-voucher-ref').innerText = inv.id;
      document.getElementById('modal-comment').value = inv.comment || '';

      document.getElementById('voucher-modal').style.display = 'flex';
    }

    function closeModal() {
      document.getElementById('voucher-modal').style.display = 'none';
      activeModalInvoice = null;
    }

    function pastePresetComment() {
      document.getElementById('modal-comment').value = "月次定額取引先一覧照合済・金額一致確認";
    }

    async function submitModalAction(action) {
      if (!activeModalInvoice) return;
      const comment = document.getElementById('modal-comment').value.trim();
      if (!comment) {
        alert("⚠️ 処理内容・確認コメントを入力してください。");
        return;
      }

      try {
        const res = await fetch(`/api/invoices/${encodeURIComponent(activeModalInvoice.id)}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: action, comment: comment })
        });
        const d = await res.json();
        if (d.success) {
          appendTerminal(`✅ [Voucher Action] ${activeModalInvoice.id} shifted to ${action}.`, 'success');
          closeModal();
          loadInvoices();
        } else {
          alert("エラー: " + (d.error || "処理に失敗しました。"));
        }
      } catch (e) {
        alert("通信エラー: " + e);
      }
    }

    // Reset Database Benchmark
    async function resetDatabaseBenchmark() {
      if (!confirm("すべての伝票ステータスを初期状態 ('unprocessed') に戻しますか？")) return;
      try {
        const res = await fetch('/api/database/reset', { method: 'POST' });
        const d = await res.json();
        appendTerminal(`🔄 [Database Reset] ${d.message}`);
        loadInvoices();
      } catch (e) {
        alert("リセット失敗: " + e);
      }
    }

    // Run AI Routing Agent
    async function runAgent() {
      const prompt = document.getElementById('agent-prompt').value.trim();
      if (!prompt) {
        alert("指示プロンプトを入力してください。");
        return;
      }

      const btn = document.getElementById('btn-run-agent');
      btn.disabled = true;
      btn.innerText = "⏳ 評価・解析中...";

      resetPipelineVisual();
      appendTerminal(`\n🚀 [Agent Triggered] Prompt: "${prompt}"`);

      try {
        highlightNode(1, 'active');
        const res = await fetch('/api/agent/stage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt })
        });
        const data = await res.json();

        // Step Logs to Terminal
        if (data.step_logs) {
          data.step_logs.forEach(l => appendTerminal(l));
        }

        // Render Distinct Independent Rule Cards
        const rulesSec = document.getElementById('rules-results-section');
        const container = document.getElementById('rules-cards-container');
        if (data.rules && data.rules.length > 0) {
          container.innerHTML = '';
          rulesSec.style.display = 'flex';

          data.rules.forEach((r, idx) => {
            const card = document.createElement('div');
            card.className = 'rule-card';
            
            const isApproved = r.target_action === 'approved';
            const actionBadgeClass = isApproved ? 'action-badge-approved' : 'action-badge-hold';
            const actionBadgeText = isApproved ? 'APPROVE (承認)' : 'HOLD (保留)';

            let pillClass = 'pill-info';
            if (r.status === 'SUCCESS' || r.status === 'STAGED') pillClass = 'pill-success';
            else if (r.status === 'GUARDRAIL_ABORTED' || r.status === 'ERROR') pillClass = 'pill-warning';

            card.innerHTML = `
              <div class="rule-card-header">
                <strong>${r.rule_name}</strong>
                <span class="rule-action-badge ${actionBadgeClass}">${actionBadgeText}</span>
              </div>
              <div class="rule-sql-box">
                <span style="font-size: 10px; color: #94a3b8; font-family: sans-serif; display: block; margin-bottom: 2px;">⚡ Independent SQL Command:</span>
                <code>${r.select_sql_query}</code>
              </div>
              ${r.rationale ? `<div style="font-size: 11px; color: #475569; margin-top: 3px;">💡 ${r.rationale}</div>` : ''}
              <div class="rule-card-footer">
                <span class="rule-result-pill ${pillClass}">${r.message}</span>
                <span style="font-size: 11px; color: #64748b;">対象: ${r.target_count || 0} 件</span>
              </div>
            `;
            container.appendChild(card);
          });
        }

        const finalMsg = data.overall_message || '評価完了';
        appendTerminal(`📌 [Status] ${finalMsg}`, data.success ? 'success' : 'warning');

        // Update pipeline nodes
        highlightNode(1, 'success');
        highlightNode(2, 'success');
        highlightNode(3, 'success');

        // Automatically open the review and commit confirmation modal!
        if (data.staged_decisions && data.staged_decisions.length > 0) {
          openStagedModal(data);
        } else {
          appendTerminal("ℹ️ 条件に合致する未処理レコードはありませんでした。", 'warning');
        }

      } catch (e) {
        appendTerminal(`❌ [Agent Error] ${e}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerText = "🚀 評価 & 確認ウィンドウを開く";
      }
    }

    function resetPipelineVisual() {
      for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`node-${i}`);
        if (el) el.className = 'graph-node';
      }
    }

    function highlightNode(nodeNum, status) {
      const el = document.getElementById(`node-${nodeNum}`);
      if (el) {
        el.className = `graph-node ${status}`;
      }
    }

    function appendTerminal(msg, type = '') {
      const box = document.getElementById('terminal-output');
      const div = document.createElement('div');
      div.className = `terminal-line ${type}`;
      div.innerText = msg;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }

    // Initial load
    window.addEventListener('DOMContentLoaded', () => {
      loadInvoices();
    });
  </script>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(PORTAL_HTML)

@app.route("/api/invoices", methods=["GET"])
def api_get_invoices():
    status_filter = request.args.get("status", "all")
    search_q = request.args.get("q", "")
    invoices = fetch_invoices_from_db(status_filter, search_q)
    counts = fetch_invoice_counts()
    return jsonify({
        "success": True,
        "invoices": invoices,
        "counts": counts
    })

@app.route("/api/invoices/<inv_id>", methods=["GET"])
def api_get_invoice_detail(inv_id):
    invoices = fetch_invoices_from_db()
    for inv in invoices:
        if inv["id"] == inv_id or inv["invoice_no"] == inv_id:
            return jsonify({"success": True, "invoice": inv})
    return jsonify({"success": False, "error": "Invoice not found"}), 404

@app.route("/api/invoices/<inv_id>/action", methods=["POST"])
def api_invoice_action(inv_id):
    data = request.get_json() or {}
    action = data.get("action", "approved").lower()
    comment = data.get("comment", "月次定額取引先一覧照合済・金額一致確認")

    if action not in ("approved", "hold", "unprocessed"):
        return jsonify({"success": False, "error": "Invalid action. Must be 'approved', 'hold', or 'unprocessed'."}), 400

    sql = """
        UPDATE erp_invoices 
        SET status = :status, comment = :comment, updated_at = CURRENT_TIMESTAMP
        WHERE (id = :id OR invoice_no = :id);
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(sql), {"status": action, "comment": comment, "id": inv_id})
        return jsonify({"success": True, "message": f"Invoice {inv_id} updated to {action}."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/agent/stage", methods=["POST"])
def api_agent_stage():
    """Human-in-the-loop: Stages candidate records for modal confirmation without writing to DB."""
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400

    result = stage_agent_decisions(prompt)
    return jsonify(result)

@app.route("/api/agent/stage-unprocessed-hold", methods=["POST"])
def api_agent_stage_unprocessed_hold():
    """Directly stages all currently unprocessed records as HOLD for confirmation modal."""
    data = request.get_json() or {}
    comment = data.get("comment", "")
    result = stage_unprocessed_as_hold(comment)
    return jsonify(result)

@app.route("/api/agent/commit", methods=["POST"])
def api_agent_commit():
    """User confirms staged decisions from the modal -> commits to PostgreSQL."""
    data = request.get_json() or {}
    decisions = data.get("decisions", [])
    if not decisions:
        return jsonify({"success": False, "error": "No decisions provided to commit"}), 400

    result = commit_staged_decisions(decisions)
    return jsonify(result)

@app.route("/api/agent/process", methods=["POST"])
def api_agent_process():
    """Legacy alias that routes to staging for human review."""
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400

    result = stage_agent_decisions(prompt)
    return jsonify(result)

@app.route("/api/database/reset", methods=["POST"])
def api_database_reset():
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
        return jsonify({"success": True, "message": "All invoices reset to 'unprocessed' with current timestamp."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/system/status", methods=["GET"])
def api_system_status():
    counts = fetch_invoice_counts()
    return jsonify({
        "database": {
            "type": "PostgreSQL (Supabase)",
            "connected": True,
            "counts": counts
        },
        "agent": {
            "framework": "LangGraph StateGraph",
            "version": 2,
            "intent_schema": "MultiRuleAgentIntent(rules=[SingleRuleIntent])",
            "guardrail_threshold": 100,
            "human_in_the_loop_staging": True
        },
        "llm": {
            "model": "gpt-4o",
            "openai_key_present": bool(openai_api_key),
            "fallback_available": True
        }
    })

# ------------------------------------------------------------------------------
# App Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5136"))
    print(f"\n=======================================================")
    print(f"🚀 Financial Accounting Invoice Portal (Version 2)")
    print(f"🌐 Running on: http://127.0.0.1:{port}")
    print(f"🛡️ LangGraph AI Agent & Human-in-the-Loop Review Active")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
