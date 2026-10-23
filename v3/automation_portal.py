"""
Invoice Policy Checker & Automation Portal with Pure LLM SQL Compiler & Human Intervention
Port 5136
"""

import os
import sys
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string, send_file
from erp_db import db_manager
from llm_policy_sql_engine import sql_engine, GENERATED_JSON_PATH, DECISION_CACHE_PATH

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = Flask(__name__)

DOCS_DIR = Path(__file__).parent / "sample_word_docs"

PRESET_FILES = {
    "getsujitsu_teigaku_torihikisaki_ichiran": {
        "filename": "getsujitsu_teigaku_torihikisaki_ichiran.docx",
        "title": "Monthly Fixed-Price Vendor Policy"
    },
    "shinkui_keiyaku_tetsuzuki": {
        "filename": "shinkui_keiyaku_tetsuzuki.docx",
        "title": "New Vendor Contract Procedure Policy"
    },
    "it_gyomu_butsuryu_shinsa": {
        "filename": "it_gyomu_butsuryu_shinsa.docx",
        "title": "IT Outsourcing & Logistics Audit Policy"
    }
}

def extract_docx_text(file_bytes) -> str:
    """Extracts raw text content from any Word .docx file without hardcoding."""
    try:
        import io
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = [node.text for node in tree.iter() if node.tag.endswith("}t") and node.text]
            return "\n".join(texts)
    except Exception as e:
        return f"Error extracting docx text: {str(e)}"

HTML_PORTAL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Invoice Policy Checker & Automation Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    body { background: #f8fafc; color: #1e293b; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }

    /* Top Navigation */
    .navbar {
      width: 100%;
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      padding: 16px 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: #2563eb;
      color: white;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      font-weight: bold;
    }
    .brand-name {
      font-size: 17px;
      font-weight: 700;
      color: #0f172a;
    }
    .brand-tag {
      font-size: 12px;
      color: #64748b;
      margin-left: 6px;
    }
    .erp-link-btn {
      color: #2563eb;
      font-size: 13px;
      text-decoration: none;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      background: #eff6ff;
      padding: 8px 16px;
      border-radius: 6px;
      transition: background 0.2s;
    }
    .erp-link-btn:hover {
      background: #dbeafe;
    }

    /* Main Container */
    .container {
      width: 100%;
      max-width: 1040px;
      padding: 32px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Common Card Styling */
    .panel-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 24px 28px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .panel-title {
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Policy Pills */
    .preset-pills {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .preset-pill {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #475569;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .preset-pill:hover {
      background: #e2e8f0;
      color: #0f172a;
    }
    .preset-pill.active {
      background: #2563eb;
      color: white;
      border-color: #2563eb;
      box-shadow: 0 2px 6px rgba(37,99,235,0.25);
    }

    .upload-row {
      display: flex;
      align-items: center;
      gap: 16px;
      background: #f8fafc;
      border: 1px dashed #94a3b8;
      border-radius: 8px;
      padding: 14px 20px;
    }
    .upload-btn {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      color: #0f172a;
      transition: all 0.2s;
    }
    .upload-btn:hover {
      background: #f1f5f9;
      border-color: #94a3b8;
    }
    .upload-info {
      font-size: 13px;
      color: #64748b;
    }
    .current-policy-badge {
      font-size: 13px;
      color: #2563eb;
      font-weight: 600;
      background: #eff6ff;
      padding: 4px 10px;
      border-radius: 6px;
    }

    /* Stats Chips */
    .stats-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .stat-chip {
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      border: 1px solid transparent;
    }
    .stat-chip.total { background: #f1f5f9; color: #334155; border-color: #cbd5e1; }
    .stat-chip.approved { background: #dcfce7; color: #166534; border-color: #86efac; }
    .stat-chip.held { background: #fef3c7; color: #92400e; border-color: #fde68a; }
    .stat-chip.discrepancy { background: #fee2e2; color: #991b1b; border-color: #fca5a5; }

    /* SQL JSON Viewer */
    .json-preview-container {
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 8px;
      padding: 14px 18px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      max-height: 240px;
      overflow-y: auto;
      white-space: pre-wrap;
      line-height: 1.4;
    }

    /* Human Intervention Gateway */
    .human-intervention-card {
      background: #fffbeb;
      border: 2px solid #f59e0b;
      border-radius: 12px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .intervention-title {
      font-size: 16px;
      font-weight: 700;
      color: #92400e;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .intervention-sub {
      font-size: 13px;
      color: #78350f;
      line-height: 1.4;
    }
    .discrepancy-item {
      background: #ffffff;
      border: 1px solid #fde68a;
      border-radius: 8px;
      padding: 14px 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .discrepancy-item-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .disc-badge {
      background: #fef2f2;
      color: #dc2626;
      border: 1px solid #fecaca;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }
    .disc-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .btn-override {
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s;
    }
    .btn-override.approve {
      background: #16a34a;
      color: white;
    }
    .btn-override.approve:hover { background: #15803d; }
    .btn-override.hold {
      background: #d97706;
      color: white;
    }
    .btn-override.hold:hover { background: #b45309; }

    .disc-comment-input {
      width: 100%;
      padding: 6px 10px;
      font-size: 12px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      background: #f8fafc;
    }

    /* Action Banner */
    .action-banner {
      background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
      border-radius: 12px;
      padding: 24px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: white;
      box-shadow: 0 4px 14px rgba(37,99,235,0.3);
    }
    .action-text-title {
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .action-text-sub {
      font-size: 13px;
      color: #bfdbfe;
      line-height: 1.4;
      max-width: 620px;
    }
    .btn-run-automation {
      background: #ffffff;
      color: #1d4ed8;
      border: none;
      padding: 14px 28px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: transform 0.15s, box-shadow 0.15s;
      white-space: nowrap;
    }
    .btn-run-automation:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }

    /* SVG Flowchart */
    .svg-container {
      width: 100%;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px;
      display: flex;
      justify-content: center;
    }
  </style>
</head>
<body>

  <!-- Top Navigation -->
  <nav class="navbar">
    <div class="brand">
      <div class="brand-icon">✓</div>
      <div>
        <span class="brand-name">Invoice Policy Checker</span>
        <span class="brand-tag">Pure LLM SQL Synthesis & Human-in-the-Loop Gateway</span>
      </div>
    </div>
    <a class="erp-link-btn" href="http://127.0.0.1:5135" target="_blank">
      <span>Open Financial Accounting System (ERP) ↗</span>
    </a>
  </nav>

  <div class="container">

    <!-- 1. Policy Document Selector & Uploader -->
    <div class="panel-card">
      <div class="panel-header">
        <div class="panel-title">
          <span>📄 1. Policy Document Input (Word .docx or Text)</span>
        </div>
        <div id="current-badge" class="current-policy-badge">
          Ready
        </div>
      </div>

      <!-- Preset Pills (Loads sample .docx files directly) -->
      <div class="preset-pills">
        <button id="pill-fixed" class="preset-pill active" onclick="choosePreset('getsujitsu_teigaku_torihikisaki_ichiran')">
          1. Monthly Fixed-Price Policy (.docx)
        </button>
        <button id="pill-contract" class="preset-pill" onclick="choosePreset('shinkui_keiyaku_tetsuzuki')">
          2. New Contract Procedure (.docx)
        </button>
        <button id="pill-it" class="preset-pill" onclick="choosePreset('it_gyomu_butsuryu_shinsa')">
          3. IT & Logistics Audit Policy (.docx)
        </button>
      </div>

      <!-- Upload Button -->
      <div class="upload-row">
        <label class="upload-btn" for="doc-upload-input">
          📁 Upload Custom Word Policy (.docx)
          <input type="file" id="doc-upload-input" accept=".docx,.txt" onchange="uploadCustomDoc(event)" style="display:none;">
        </label>
        <div class="upload-info" id="upload-status-text">
          Upload any corporate Word policy document (.docx) to synthesize PostgreSQL SQL rules dynamically via LLM.
        </div>
      </div>
    </div>

    <!-- 2. LLM Generated SQL Queries (JSON Preview) -->
    <div class="panel-card">
      <div class="panel-header">
        <div class="panel-title">
          <span>🧠 2. LLM Synthesized SQL Queries (Valid JSON File)</span>
        </div>
        <a href="/api/policy/generated_json" target="_blank" style="font-size: 12px; color: #2563eb; font-weight: 600; text-decoration: none;">
          📥 Download Generated JSON File
        </a>
      </div>
      <div style="font-size: 13px; color: #64748b;" id="policy-summary-text">
        LLM document synthesis output will appear here...
      </div>
      <div class="json-preview-container" id="json-preview-box">
        // Waiting for policy selection or document upload...
      </div>
    </div>

    <!-- 3. PostgreSQL Execution & Live Stats -->
    <div class="panel-card">
      <div class="panel-header">
        <div class="panel-title">
          <span>⚙️ 3. PostgreSQL Table Execution (`erp_invoices`)</span>
        </div>
        <button class="upload-btn" onclick="executePostgresRules()" style="padding: 6px 14px; font-size: 12px;">
          🔄 Re-run Queries on PostgreSQL
        </button>
      </div>
      <div class="stats-row">
        <div class="stat-chip total" id="chip-total">📊 Total Rows: 12</div>
        <div class="stat-chip approved" id="chip-approved">✅ Approved via SQL: 0</div>
        <div class="stat-chip held" id="chip-held">⚠️ Placed On Hold: 0</div>
        <div class="stat-chip discrepancy" id="chip-discrepancy">🔍 Discrepancies Requiring Review: 0</div>
      </div>
    </div>

    <!-- 4. Human Intervention Gateway (Shown when Discrepancies Exist) -->
    <div class="human-intervention-card" id="human-intervention-panel">
      <div class="intervention-title">
        <span>👤 4. Human Review & Intervention Gateway</span>
        <span class="disc-badge" id="disc-count-badge">Action Required</span>
      </div>
      <div class="intervention-sub">
        The following invoice rows were flagged by the SQL discrepancy query or have contract variances. Review each flagged item, adjust the audit comment if desired, and click [Approve] or [Confirm Hold] to resolve the discrepancy before triggering the ERP automation.
      </div>
      <div id="discrepancy-items-container" style="display: flex; flex-direction: column; gap: 12px;">
        <!-- Discrepancy review cards rendered dynamically -->
      </div>
    </div>

    <!-- 5. Decision Flowchart SVG Graph -->
    <div class="panel-card">
      <div class="panel-header">
        <div class="panel-title">
          <span>📊 5. Visual Decision Flowchart Graph</span>
        </div>
      </div>
      <div class="svg-container">
        <svg id="decision-svg" viewBox="0 0 940 220" style="width: 100%; max-width: 920px; height: auto;">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b" />
            </marker>
            <marker id="arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#16a34a" />
            </marker>
            <marker id="arrow-amber" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#d97706" />
            </marker>
          </defs>

          <!-- Nodes & Edges -->
          <path d="M 160 110 L 220 110" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
          <path d="M 380 110 L 440 110" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
          <path d="M 600 75 L 680 50" stroke="#16a34a" stroke-width="2" marker-end="url(#arrow-green)" />
          <path d="M 600 110 L 680 110" stroke="#d97706" stroke-width="2" marker-end="url(#arrow-amber)" />
          <path d="M 600 145 L 680 170" stroke="#d97706" stroke-width="2" marker-end="url(#arrow-amber)" />

          <!-- Node 1: Invoices in PG -->
          <rect x="20" y="80" width="140" height="60" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="2" />
          <text x="90" y="105" fill="#1e3a8a" font-size="12" font-weight="bold" text-anchor="middle">📥 PostgreSQL Table</text>
          <text x="90" y="125" fill="#64748b" font-size="10.5" text-anchor="middle">erp_invoices (12 rows)</text>

          <!-- Node 2: LLM SQL Compiler -->
          <rect x="220" y="80" width="160" height="60" rx="8" fill="#fdf4ff" stroke="#c084fc" stroke-width="2" />
          <text x="300" y="105" fill="#581c87" font-size="12" font-weight="bold" text-anchor="middle">🧠 Pure LLM Compiler</text>
          <text x="300" y="125" fill="#7e22ce" font-size="10.5" text-anchor="middle">Valid JSON SQL Queries</text>

          <!-- Node 3: Discrepancy & Human Gateway -->
          <rect x="440" y="80" width="160" height="60" rx="8" fill="#fffbeb" stroke="#f59e0b" stroke-width="2" />
          <text x="520" y="105" fill="#92400e" font-size="12" font-weight="bold" text-anchor="middle">👤 Human Gateway</text>
          <text x="520" y="125" fill="#b45309" font-size="10.5" text-anchor="middle">Review Discrepancies</text>

          <!-- Node 4: Approve -->
          <rect x="680" y="25" width="230" height="50" rx="8" fill="#f0fdf4" stroke="#16a34a" stroke-width="2" />
          <text x="795" y="47" fill="#166534" font-size="12" font-weight="bold" text-anchor="middle">✅ Approved Rows</text>
          <text x="795" y="63" fill="#15803d" font-size="10" text-anchor="middle">Matched SQL approval criteria</text>

          <!-- Node 5: Held -->
          <rect x="680" y="85" width="230" height="50" rx="8" fill="#fffaf0" stroke="#f59e0b" stroke-width="2" />
          <text x="795" y="107" fill="#92400e" font-size="12" font-weight="bold" text-anchor="middle">⚠️ On Hold Rows</text>
          <text x="795" y="123" fill="#b45309" font-size="10" text-anchor="middle">Variance, threshold or unverified</text>

          <!-- Node 6: Dispatched to ERP -->
          <rect x="680" y="145" width="230" height="50" rx="8" fill="#f8fafc" stroke="#64748b" stroke-width="2" />
          <text x="795" y="167" fill="#1e293b" font-size="12" font-weight="bold" text-anchor="middle">🚀 One-Time Token Dispatch</text>
          <text x="795" y="183" fill="#64748b" font-size="10" text-anchor="middle">RPA automated execution in ERP</text>
        </svg>
      </div>
    </div>

    <!-- 6. Launch Automation Action Banner -->
    <div class="action-banner">
      <div>
        <div class="action-text-title">
          <span>🚀 Launch Verified Automation in ERP Tab</span>
        </div>
        <div class="action-text-sub">
          Generates a single-use dispatch token and opens the ERP System (:5135) in a new tab. The automated RPA agent executes all decisions and human intervention overrides. <strong>Refreshing the ERP tab will NOT repeat the automation.</strong>
        </div>
      </div>
      <button class="btn-run-automation" onclick="dispatchAutomationToErp()">
        <span>▶️ Dispatch & Run in ERP</span>
      </button>
    </div>

  </div>

  <script>
    let currentKey = 'getsujitsu_teigaku_torihikisaki_ichiran';
    let currentExecutionState = null;

    async function choosePreset(key) {
      currentKey = key;
      document.getElementById('pill-fixed').classList.toggle('active', key === 'getsujitsu_teigaku_torihikisaki_ichiran');
      document.getElementById('pill-contract').classList.toggle('active', key === 'shinkui_keiyaku_tetsuzuki');
      document.getElementById('pill-it').classList.toggle('active', key === 'it_gyomu_butsuryu_shinsa');

      document.getElementById('json-preview-box').innerText = "// Querying LLM to synthesize PostgreSQL SQL JSON from document...";
      document.getElementById('upload-status-text').innerText = `Analyzing preset document with LLM...`;

      const res = await fetch(`/api/preset?key=${key}`);
      const data = await res.json();
      renderExecutionReport(data);
    }

    async function uploadCustomDoc(event) {
      const file = event.target.files[0];
      if (!file) return;

      const fd = new FormData();
      fd.append('file', file);

      document.getElementById('upload-status-text').innerText = `Sending ${file.name} to LLM for PostgreSQL SQL query synthesis...`;
      document.getElementById('json-preview-box').innerText = `// Uploaded ${file.name}. LLM is synthesizing PostgreSQL queries...`;

      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();

      document.getElementById('upload-status-text').innerText = `✅ LLM Analysis Completed for ${file.name}`;
      document.querySelectorAll('.preset-pill').forEach(p => p.classList.remove('active'));

      renderExecutionReport(data);
    }

    async function executePostgresRules() {
      const res = await fetch('/api/execute_sql');
      const data = await res.json();
      renderExecutionReport(data);
    }

    function renderExecutionReport(data) {
      currentExecutionState = data;
      document.getElementById('current-badge').innerText = data.policy_title;
      document.getElementById('policy-summary-text').innerText = data.summary;

      // JSON preview
      if (data.generated_sql_rules) {
        const previewObj = {
          policy_title: data.policy_title,
          summary: data.summary,
          rules: data.generated_sql_rules,
          discrepancies_found: data.discrepancy_count
        };
        document.getElementById('json-preview-box').innerText = JSON.stringify(previewObj, null, 2);
      }

      // Stats
      document.getElementById('chip-total').innerText = `📊 Total Rows: ${data.total_invoices}`;
      document.getElementById('chip-approved').innerText = `✅ Approved via SQL: ${data.approved_count}`;
      document.getElementById('chip-held').innerText = `⚠️ Placed On Hold: ${data.held_count}`;
      document.getElementById('chip-discrepancy').innerText = `🔍 Discrepancies Requiring Review: ${data.discrepancy_count}`;

      // Discrepancies & Human Intervention
      const panel = document.getElementById('human-intervention-panel');
      const container = document.getElementById('discrepancy-items-container');
      container.innerHTML = '';

      if (data.discrepancies && data.discrepancies.length > 0) {
        panel.style.display = 'flex';
        document.getElementById('disc-count-badge').innerText = `${data.discrepancies.length} Action(s) Required`;

        data.discrepancies.forEach(disc => {
          const div = document.createElement('div');
          div.className = 'discrepancy-item';
          div.id = `disc-${disc.id}`;
          div.innerHTML = `
            <div class="discrepancy-item-header">
              <div>
                <strong style="color: #0f172a; font-size: 14px;">${disc.invoice_no} — ${disc.name}</strong>
                <span style="margin-left: 10px; font-weight: bold; color: #1e3a8a;">${disc.amount}</span>
                <span style="margin-left: 6px; font-size: 11px; background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">${disc.type}</span>
              </div>
              <span class="disc-badge">⚠️ Variance / Review</span>
            </div>
            <div style="font-size: 12px; color: #92400e;">
              <strong>Discrepancy Detail:</strong> ${disc.discrepancy_detail || 'Amount variance from expected contract or special condition.'}
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <input type="text" class="disc-comment-input" id="comment-${disc.id}" value="${disc.comment}" />
              <button class="btn-override approve" onclick="submitHumanOverride('${disc.id}', 'approve')">Approve</button>
              <button class="btn-override hold" onclick="submitHumanOverride('${disc.id}', 'hold')">Confirm Hold</button>
            </div>
          `;
          container.appendChild(div);
        });
      } else {
        panel.style.display = 'flex';
        document.getElementById('disc-count-badge').innerText = 'All Clear';
        document.getElementById('disc-count-badge').style.background = '#dcfce7';
        document.getElementById('disc-count-badge').style.color = '#166534';
        document.getElementById('disc-count-badge').style.borderColor = '#86efac';
        container.innerHTML = `
          <div style="padding: 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; color: #166534; font-size: 13px;">
            ✅ <strong>No unresolved discrepancies!</strong> All 12 invoice rows match defined SQL rules and are ready for ERP automated processing.
          </div>
        `;
      }
    }

    async function submitHumanOverride(invoiceId, action) {
      const commentInput = document.getElementById(`comment-${invoiceId}`);
      const comment = commentInput ? commentInput.value.trim() : (action === 'approve' ? 'Approved by human reviewer override.' : 'Held by human reviewer confirmation.');

      const res = await fetch('/api/human_override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invoice_id: invoiceId,
          action: action,
          comment: comment
        })
      });

      const updated = await res.json();
      renderExecutionReport(updated);
    }

    async function dispatchAutomationToErp() {
      // Create secure one-time dispatch token
      const res = await fetch('/api/dispatch_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ policy_id: currentKey })
      });
      const data = await res.json();

      if (data.url) {
        window.open(data.url, '_blank');
      } else {
        alert('Failed to generate dispatch token. Please check that ERP is running.');
      }
    }

    window.onload = () => {
      choosePreset('getsujitsu_teigaku_torihikisaki_ichiran');
    };
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PORTAL)

@app.route("/api/preset", methods=["GET"])
def get_preset():
    key = request.args.get("key", "getsujitsu_teigaku_torihikisaki_ichiran")
    preset_info = PRESET_FILES.get(key, PRESET_FILES["getsujitsu_teigaku_torihikisaki_ichiran"])
    docx_path = DOCS_DIR / preset_info["filename"]
    
    if docx_path.exists():
        with open(docx_path, "rb") as f:
            content = extract_docx_text(f.read())
    else:
        content = f"{preset_info['title']}"

    # Pure LLM compilation: Zero hardcoded queries or vendor rules
    policy_json = sql_engine.generate_sql_policy_from_doc(content, preset_info["title"])
    # Execute the generated SQL queries against PostgreSQL
    report = sql_engine.execute_sql_rules_against_pg(policy_json)
    return jsonify(report)

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    content = ""
    if file.filename.endswith(".docx"):
        content = extract_docx_text(file.read())
    else:
        content = file.read().decode("utf-8", errors="replace")
    
    # Pure LLM compilation: Zero hardcoded queries or vendor rules
    policy_json = sql_engine.generate_sql_policy_from_doc(content, file.filename)
    # Execute the generated SQL queries against PostgreSQL
    report = sql_engine.execute_sql_rules_against_pg(policy_json)
    return jsonify(report)

@app.route("/api/execute_sql", methods=["GET"])
def execute_sql():
    report = sql_engine.execute_sql_rules_against_pg()
    return jsonify(report)

@app.route("/api/human_override", methods=["POST"])
def human_override():
    data = request.json or {}
    inv_id = data.get("invoice_id")
    action = data.get("action", "hold")
    comment = data.get("comment", "")
    if not inv_id:
        return jsonify({"error": "Missing invoice_id"}), 400
    updated_state = sql_engine.apply_human_override(inv_id, action, comment)
    return jsonify(updated_state)

@app.route("/api/dispatch_token", methods=["POST"])
def dispatch_token():
    data = request.json or {}
    policy_id = data.get("policy_id", "active_policy")
    token = sql_engine.create_dispatch_token(policy_id)
    return jsonify({
        "token": token,
        "url": f"http://127.0.0.1:5135/?token={token}"
    })

@app.route("/api/policy/generated_json", methods=["GET"])
def get_generated_json():
    if GENERATED_JSON_PATH.exists():
        return send_file(GENERATED_JSON_PATH, mimetype="application/json")
    return jsonify({"error": "No policy JSON compiled yet"}), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5136, debug=False)
