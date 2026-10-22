"""
ERP Financial Accounting System: Corporate Accounting Portal (English Edition)
Standalone Enterprise Web Application mimicking the production system from Dataset B screenshots.
Running on http://127.0.0.1:5135
"""

import sys
import copy
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from erp_db import db_manager, INITIAL_INVOICES
from policy_engine import get_active_policy, set_active_policy, evaluate_invoice
from llm_policy_sql_engine import sql_engine, DECISION_CACHE_PATH, GENERATED_JSON_PATH

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = Flask(__name__)

ERP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Financial Accounting System - FY2026 Corporate Accounting</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    body { background-color: #f0f2f5; color: #1e293b; font-size: 13px; line-height: 1.4; min-height: 100vh; display: flex; flex-direction: column; }

    /* Top Corporate Header */
    .top-bar {
      background-color: #ffffff;
      border-bottom: 1px solid #d9d9d9;
      height: 48px;
      padding: 0 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .system-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 15px;
      font-weight: bold;
      color: #1a365d;
    }
    .system-logo {
      background-color: #1b8ebd;
      color: white;
      width: 26px;
      height: 26px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: bold;
      letter-spacing: 0.5px;
    }
    .dept-badge {
      font-size: 12px;
      color: #4a5568;
      font-weight: normal;
      background: #edf2f7;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .user-info {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 12px;
      color: #4a5568;
    }
    .user-avatar {
      width: 26px;
      height: 26px;
      background-color: #cbd5e0;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #2d3748;
      font-weight: bold;
      font-size: 12px;
    }

    /* Main Container Layout */
    .app-container {
      display: flex;
      flex: 1;
      height: calc(100vh - 48px);
    }

    /* Left Sidebar */
    .sidebar {
      width: 250px;
      background-color: #ffffff;
      border-right: 1px solid #e2e8f0;
      display: flex;
      flex-direction: column;
      padding: 16px 0;
    }
    .sidebar-menu-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      color: #4a5568;
      font-size: 13px;
      cursor: pointer;
      border-left: 4px solid transparent;
      transition: background-color 0.1s;
    }
    .sidebar-menu-item:hover {
      background-color: #f7fafc;
      color: #1a202c;
    }
    .sidebar-menu-item.active {
      background-color: #e6f7ff;
      color: #0070f3;
      font-weight: bold;
      border-left-color: #0070f3;
    }
    .menu-icon-text {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .menu-badge {
      background-color: #f0f2f5;
      color: #718096;
      border-radius: 10px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: bold;
    }

    /* Right Main Panel */
    .content-area {
      flex: 1;
      background-color: #ffffff;
      padding: 20px 28px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    /* Breadcrumbs */
    .breadcrumbs {
      font-size: 12px;
      color: #718096;
      margin-bottom: 12px;
    }

    /* Sub Tabs */
    .subtabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 8px;
      margin-bottom: 16px;
    }
    .subtab-btn {
      background: none;
      border: 1px solid #cbd5e0;
      border-radius: 4px;
      padding: 6px 16px;
      font-size: 13px;
      cursor: pointer;
      color: #4a5568;
    }
    .subtab-btn.active {
      background-color: #1a365d;
      color: #ffffff;
      border-color: #1a365d;
      font-weight: bold;
    }

    /* Counter & Section Heading */
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .pending-summary {
      font-size: 14px;
      font-weight: bold;
      color: #2b6cb0;
    }
    .section-title {
      font-size: 14px;
      font-weight: bold;
      color: #2d3748;
      margin-bottom: 10px;
    }
    .reset-link {
      color: #718096;
      font-size: 12px;
      text-decoration: underline;
      cursor: pointer;
    }
    .reset-link:hover {
      color: #2b6cb0;
    }

    /* Table */
    .table-wrapper {
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      overflow: hidden;
    }
    table#pi-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }
    thead th {
      background-color: #f7fafc;
      color: #4a5568;
      font-weight: bold;
      padding: 10px 14px;
      border-bottom: 1px solid #e2e8f0;
    }
    tbody td {
      padding: 10px 14px;
      border-bottom: 1px solid #edf2f7;
      vertical-align: middle;
    }
    tbody tr:hover {
      background-color: #f8fafc;
    }

    .td-id {
      font-family: Consolas, monospace;
      color: #4a5568;
      font-weight: 500;
    }
    .td-vendor-id {
      color: #718096;
      font-family: Consolas, monospace;
    }
    .td-name {
      color: #1a202c;
      font-weight: 500;
    }
    .td-amount {
      text-align: right;
      font-family: Consolas, monospace;
      font-weight: 600;
      color: #2d3748;
    }
    .td-type {
      text-align: center;
      color: #4a5568;
    }
    .td-status {
      text-align: center;
    }

    /* Action Button */
    .btn-invoice-action {
      background-color: #ffffff;
      border: 1px solid #cbd5e0;
      color: #2b6cb0;
      padding: 4px 10px;
      border-radius: 3px;
      font-size: 12px;
      cursor: pointer;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-invoice-action:hover {
      background-color: #ebf8ff;
      border-color: #3182ce;
      color: #2b6cb0;
    }

    /* Status Badges */
    .badge-status {
      padding: 3px 8px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: bold;
      display: inline-block;
      text-transform: capitalize;
    }
    .badge-status.unprocessed, .badge-status.未処理 {
      background-color: #edf2f7;
      color: #718096;
      border: 1px solid #cbd5e0;
    }
    .badge-status.approved, .badge-status.登録済み, .badge-status.承認済 {
      background-color: #e6fffa;
      color: #234e52;
      border: 1px solid #81e6d9;
    }
    .badge-status.on-hold, .badge-status.hold, .badge-status.保留 {
      background-color: #fffaf0;
      color: #744210;
      border: 1px solid #fbd38d;
    }

    /* Modal Dialog */
    .modal-backdrop {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.4);
      z-index: 1000;
      justify-content: center;
      align-items: center;
    }
    .modal-backdrop.active {
      display: flex;
    }
    .modal-container {
      background: #ffffff;
      width: 650px;
      border-radius: 6px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      border: 1px solid #cbd5e0;
      overflow: hidden;
    }
    .modal-header-bar {
      background-color: #f7fafc;
      padding: 12px 20px;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header-title {
      font-size: 14px;
      font-weight: bold;
      color: #1a202c;
    }
    .modal-close-icon {
      background: none;
      border: none;
      font-size: 18px;
      color: #a0aec0;
      cursor: pointer;
    }
    .modal-close-icon:hover {
      color: #2d3748;
    }

    .modal-content-grid {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .field-row {
      display: flex;
      align-items: center;
      padding: 6px 0;
      border-bottom: 1px solid #f7fafc;
    }
    .field-label {
      width: 140px;
      color: #718096;
      font-size: 13px;
    }
    .field-value {
      flex: 1;
      color: #2d3748;
      font-weight: 500;
      font-size: 13px;
    }
    .field-value.amount-large {
      color: #1a365d;
      font-size: 16px;
      font-weight: bold;
      font-family: Consolas, monospace;
    }
    .field-ref-text {
      color: #718096;
      font-size: 12px;
      background: #f7fafc;
      padding: 6px 10px;
      border-radius: 4px;
      border: 1px solid #edf2f7;
    }

    /* Comment Area */
    .comment-container {
      margin-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .comment-heading {
      font-weight: bold;
      color: #2d3748;
      font-size: 13px;
    }
    textarea#modal-comment-input {
      width: 100%;
      height: 80px;
      padding: 8px 12px;
      border: 1px solid #cbd5e0;
      border-radius: 4px;
      font-size: 13px;
      resize: none;
      outline: none;
    }
    textarea#modal-comment-input:focus {
      border-color: #3182ce;
      box-shadow: 0 0 0 2px rgba(49, 130, 206, 0.2);
    }

    /* Modal Action Buttons */
    .modal-button-bar {
      padding: 12px 20px;
      background-color: #f7fafc;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
    .btn-dialog {
      padding: 6px 18px;
      border-radius: 4px;
      font-size: 13px;
      font-weight: bold;
      cursor: pointer;
      border: 1px solid transparent;
    }
    .btn-dialog.btn-submit-ok {
      background-color: #2b6cb0;
      color: #ffffff;
      border-color: #2b6cb0;
    }
    .btn-dialog.btn-submit-ok:hover {
      background-color: #2c5282;
    }
    .btn-dialog.btn-submit-hold {
      background-color: #d69e2e;
      color: #ffffff;
      border-color: #d69e2e;
    }
    .btn-dialog.btn-submit-hold:hover {
      background-color: #b7791f;
    }
    .btn-dialog.btn-cancel {
      background-color: #ffffff;
      color: #4a5568;
      border-color: #cbd5e0;
    }
    .btn-dialog.btn-cancel:hover {
      background-color: #edf2f7;
    }
  </style>
</head>
<body>

  <!-- Top Corporate Bar -->
  <div class="top-bar">
    <div class="system-title">
      <div class="system-logo">FA</div>
      <span>Financial Accounting System</span>
      <span class="dept-badge">FY2026 · Corporate Accounting Division</span>
    </div>
    <div class="user-info">
      <span id="current-timestamp">2026/07/01 22:14:44</span>
      <span>Naoki Sato · Accounting Manager</span>
      <div class="user-avatar">NS</div>
    </div>
  </div>

  <div class="app-container">
    <!-- Left Navigation Sidebar -->
    <div class="sidebar">
      <div class="sidebar-menu-item">
        <div class="menu-icon-text">
          <span>📊</span>
          <span>Dashboard</span>
        </div>
      </div>
      <div class="sidebar-menu-item active">
        <div class="menu-icon-text">
          <span>📄</span>
          <span>Invoice Approval & Expense</span>
        </div>
        <span class="menu-badge" id="side-badge">12</span>
      </div>
      <div class="sidebar-menu-item">
        <div class="menu-icon-text">
          <span>👤</span>
          <span>Expense Approval (Manager)</span>
        </div>
        <span class="menu-badge">12</span>
      </div>
      <div class="sidebar-menu-item">
        <div class="menu-icon-text">
          <span>💳</span>
          <span>Payment Processing</span>
        </div>
        <span class="menu-badge">12</span>
      </div>
      <div class="sidebar-menu-item">
        <div class="menu-icon-text">
          <span>📈</span>
          <span>Budget Variance Analysis</span>
        </div>
        <span class="menu-badge">12</span>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="content-area">
      <!-- Breadcrumb Navigation -->
      <div class="breadcrumbs">
        Dashboard / Invoice Approval & Expense Settlement
      </div>

      <!-- Sub Tabs -->
      <div class="subtabs">
        <button class="subtab-btn active">Invoice Approval</button>
        <button class="subtab-btn">Expense Settlement</button>
      </div>

      <!-- Section Header -->
      <div class="section-header">
        <div class="pending-summary" id="top-pending-badge">
          12 items · 12 unprocessed
        </div>
        <span class="reset-link" onclick="resetTable()">Reset Queue to Initial State</span>
      </div>

      <div class="section-title">
        Pending Processing Queue
      </div>

      <!-- Invoice Table -->
      <div class="table-wrapper">
        <table id="pi-table">
          <thead>
            <tr>
              <th style="width: 170px;">Voucher ID</th>
              <th style="width: 100px;">Vendor ID</th>
              <th>Vendor Name</th>
              <th style="width: 230px;">Action / Invoice No.</th>
              <th style="width: 140px; text-align: right;">Amount</th>
              <th style="width: 100px; text-align: center;">Category</th>
              <th style="width: 110px; text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody id="invoice-rows">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Detail Modal Dialog -->
  <div class="modal-backdrop" id="detail-modal">
    <div class="modal-container">
      <div class="modal-header-bar">
        <span class="modal-header-title" id="modal-title">Invoice Details — P6-07010448-001 - Global Tech LLC</span>
        <button class="modal-close-icon" onclick="closeDetailModal()">×</button>
      </div>

      <div class="modal-content-grid">
        <div class="field-row">
          <span class="field-label">Voucher ID</span>
          <span class="field-value" id="modal-id">P6-07010448-001</span>
        </div>
        <div class="field-row">
          <span class="field-label">Vendor ID</span>
          <span class="field-value" id="modal-employee-id">V3005</span>
        </div>
        <div class="field-row">
          <span class="field-label">Action</span>
          <span class="field-value" id="modal-action-text">Invoice Approval INV-2026-7344</span>
        </div>
        <div class="field-row">
          <span class="field-label">Category</span>
          <span class="field-value" id="modal-type">Routine</span>
        </div>
        <div class="field-row">
          <span class="field-label">Amount</span>
          <span class="field-value amount-large" id="modal-amount">¥716,232</span>
        </div>
        <div class="field-row">
          <span class="field-label">Status</span>
          <span class="field-value" id="modal-status-text">Unprocessed</span>
        </div>
        <div class="field-ref-text" id="modal-ref-order">
          Reference: Order Cross-Check : INV-2026-7344
        </div>

        <div class="comment-container">
          <div class="comment-heading">Audit & Verification Comment</div>
          <textarea id="modal-comment-input" placeholder="Enter verification notes, policy match comments, or hold rationale..."></textarea>
        </div>
      </div>

      <div class="modal-button-bar">
        <button class="btn-dialog btn-cancel" id="btn-pi-cancel" onclick="closeDetailModal()">Cancel</button>
        <button class="btn-dialog btn-submit-hold" id="btn-pi-hold" onclick="handleManualAction('hold')">Put On Hold</button>
        <button class="btn-dialog btn-submit-ok" id="btn-pi-ok" onclick="handleManualAction('approve')">Approve</button>
      </div>
    </div>
  </div>

  <script>
    let activeId = null;

    function getBadgeClass(status) {
      const s = (status || '').toLowerCase().replace(/\\s+/g, '-');
      if (s === 'unprocessed' || s === '未処理') return 'unprocessed';
      if (s === 'approved' || s === '登録済み' || s === '承認済') return 'approved';
      if (s === 'on-hold' || s === 'hold' || s === '保留') return 'on-hold';
      return 'unprocessed';
    }

    async function loadTable() {
      const res = await fetch('/api/invoices');
      const data = await res.json();
      render(data.invoices, data.total, data.pending);
    }

    function render(invoices, total, pending) {
      const tbody = document.getElementById('invoice-rows');
      tbody.innerHTML = '';

      invoices.forEach(inv => {
        const tr = document.createElement('tr');
        tr.id = 'row-' + inv.id;
        tr.setAttribute('data-id', inv.id);
        tr.setAttribute('data-status', inv.status);
        tr.setAttribute('data-vendor-name', inv.name);
        tr.setAttribute('data-raw-amount', inv.raw_amount);
        tr.setAttribute('data-invoice-no', inv.invoice_no);
        tr.setAttribute('data-type', inv.type);

        const badgeCls = getBadgeClass(inv.status);

        tr.innerHTML = `
          <td class="td-id">${inv.id}</td>
          <td class="td-vendor-id">${inv.employee_id}</td>
          <td class="td-name">${inv.name}</td>
          <td>
            <button class="btn-invoice-action" onclick="openDetailModal('${inv.id}')">
              <span>📄</span>
              <span>Invoice Approval ${inv.invoice_no}</span>
            </button>
          </td>
          <td class="td-amount">${inv.amount}</td>
          <td class="td-type">${inv.type}</td>
          <td class="td-status">
            <span class="badge-status ${badgeCls}" data-status="${inv.status}">${inv.status}</span>
          </td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById('top-pending-badge').innerText = `${total} items · ${pending} unprocessed`;
      document.getElementById('side-badge').innerText = pending;
    }

    function openDetailModal(id) {
      activeId = id;
      fetch(`/api/invoices/${id}`)
        .then(res => res.json())
        .then(inv => {
          document.getElementById('modal-title').innerText = `Invoice Details — ${inv.id} · ${inv.name}`;
          document.getElementById('modal-id').innerText = inv.id;
          document.getElementById('modal-employee-id').innerText = inv.employee_id;
          document.getElementById('modal-action-text').innerText = `Invoice Approval ${inv.invoice_no}`;
          document.getElementById('modal-type').innerText = inv.type;
          document.getElementById('modal-amount').innerText = inv.amount;
          document.getElementById('modal-status-text').innerText = inv.status;
          document.getElementById('modal-ref-order').innerText = inv.ref;
          document.getElementById('modal-comment-input').value = inv.comment || '';

          document.getElementById('detail-modal').classList.add('active');
        });
    }

    function closeDetailModal() {
      document.getElementById('detail-modal').classList.remove('active');
      activeId = null;
    }

    async function handleManualAction(action) {
      if (!activeId) return;
      const comment = document.getElementById('modal-comment-input').value.trim();

      if (action === 'approve' && !comment) {
        alert('Please enter an audit verification comment before approving.');
        return;
      }

      await fetch(`/api/invoices/${activeId}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          comment: comment
        })
      });

      closeDetailModal();
      await loadTable();
    }

    async function resetTable() {
      if (confirm('Reset the pending queue to the initial state (12 Unprocessed invoices)?')) {
        await fetch('/api/reset', { method: 'POST' });
        await loadTable();
      }
    }

    // Autopilot external RPA runner
    function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

    function isRowPending(r) {
      const attrStatus = (r.getAttribute('data-status') || '').toLowerCase();
      if (attrStatus === 'unprocessed' || attrStatus === '未処理') return true;
      if (attrStatus === 'approved' || attrStatus === 'on hold' || attrStatus === '登録済み' || attrStatus === '保留') return false;
      const st = r.querySelector('.badge-status');
      if (!st) return false;
      const bAttr = (st.getAttribute('data-status') || '').toLowerCase();
      if (bAttr === 'unprocessed' || bAttr === '未処理') return true;
      if (st.classList.contains('unprocessed') || st.classList.contains('未処理')) return true;
      const txt = st.innerText.trim().toLowerCase();
      return txt === 'unprocessed' || txt === '未処理' || txt.includes('unproc');
    }

    /*
     * STRICT TOKEN DISPATCH CHECK
     * Prevents ERP page refresh from restarting automation automatically!
     * Only triggers when a valid, unconsumed dispatch token is passed.
     */
    async function checkAutopilotTrigger() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      
      // If no token, do not run automation at all!
      if (!token) {
        return;
      }

      // Immediately clean the URL so browser refresh (F5) will NEVER restart the automation!
      window.history.replaceState({}, document.title, window.location.pathname);

      // Verify and consume token with server
      try {
        const resp = await fetch(`/api/automation/verify_token?token=${encodeURIComponent(token)}`);
        const data = await resp.json();
        if (!data.valid) {
          console.log('Automation token invalid or already consumed.');
          return;
        }
      } catch (err) {
        console.warn('Token verification error:', err);
        return;
      }

      let retries = 0;
      while (document.querySelectorAll('#invoice-rows tr').length === 0 && retries < 25) {
        await sleep(200);
        retries++;
      }
      setTimeout(() => runExternalRPA(), 800);
    }

    async function runExternalRPA() {
      let hud = document.getElementById('autopilot-hud');
      if (!hud) {
        hud = document.createElement('div');
        hud.id = 'autopilot-hud';
        hud.style.cssText = `
          position: fixed; bottom: 24px; right: 24px; z-index: 9999;
          background: #ffffff; border: 2px solid #2563eb; border-radius: 10px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.22); padding: 18px 22px;
          max-width: 480px; font-size: 13px; color: #1e293b;
          display: flex; flex-direction: column; gap: 10px;
        `;
        document.body.appendChild(hud);
      }

      const rows = Array.from(document.querySelectorAll('#invoice-rows tr'));
      const pendingRows = rows.filter(isRowPending);

      if (pendingRows.length === 0) {
        hud.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#d97706; font-size:14px;">ℹ️ All Invoices Processed (0 Pending)</strong>
          </div>
          <div style="color:#475569; line-height:1.4;">
            All 12 invoices are already processed in the database.<br>To run another policy check, dispatch from the Automation Portal (:5136).
          </div>
          <button onclick="document.getElementById('autopilot-hud').remove()" style="margin-top:6px; padding:6px 14px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; cursor:pointer;">Close</button>
        `;
        return;
      }

      hud.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#1d4ed8; font-size:14px;">🤖 External AI UI Automation (RPA) Running</strong>
          <span style="background:#eff6ff; color:#1d4ed8; font-size:11px; padding:2px 8px; border-radius:12px; font-weight:bold;">SQL Rule Dispatched</span>
        </div>
        <div id="hud-status" style="color:#475569; line-height:1.4;">📄 Executing SQL-verified decisions and human intervention overrides...</div>
        <div style="height:5px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
          <div id="hud-progress" style="width:0%; height:100%; background:#2563eb; transition:width 0.3s;"></div>
        </div>
      `;

      let processed = 0;
      const total = rows.length;

      for (let i = 0; i < total; i++) {
        const row = rows[i];
        if (!isRowPending(row)) {
          processed++;
          continue;
        }

        const invId = row.getAttribute('data-id') || row.id.replace('row-', '');
        const name = row.getAttribute('data-vendor-name') || (row.querySelector('td.td-name') ? row.querySelector('td.td-name').innerText.trim() : '');
        const rawAmount = parseInt(row.getAttribute('data-raw-amount')) || (row.querySelector('td.td-amount') ? parseInt(row.querySelector('td.td-amount').innerText.replace(/[^0-9]/g, '')) : 0);
        const invNo = row.getAttribute('data-invoice-no') || '';

        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.style.transition = 'all 0.3s';
        row.style.background = '#eef6ff';
        row.style.outline = '2px solid #2563eb';

        const hudStatus = document.getElementById('hud-status');
        hudStatus.innerHTML = `🔍 <strong>[${i+1}/${total}] ${invNo}</strong> (${name})<br>Amount: ¥${rawAmount.toLocaleString()}`;

        await sleep(550);

        // Click invoice action button
        const actionBtn = row.querySelector('.btn-invoice-action') || row.querySelector('button');
        if (actionBtn) {
          actionBtn.style.outline = '2px solid #dc2626';
          actionBtn.click();
        }

        // Wait for modal to open
        let modalWait = 0;
        while (!document.getElementById('detail-modal').classList.contains('active') && modalWait < 20) {
          await sleep(100);
          modalWait++;
        }

        // Authoritative Policy Evaluation from Server (incorporating SQL query result & human overrides)
        let decision = 'On Hold';
        let comment = '';
        let reason = '';

        try {
          const evalResp = await fetch(`/api/invoices/${invId}/evaluate`);
          if (evalResp.ok) {
            const evalData = await evalResp.json();
            decision = evalData.decision;
            comment = evalData.comment;
            reason = evalData.reason;
          }
        } catch (err) {
          console.error('Error fetching evaluation:', err);
          decision = 'On Hold';
          comment = 'On hold for verification.';
          reason = 'Fallback verification';
        }

        hudStatus.innerHTML = `✍️ <strong>[${decision}]</strong> Typing audit comment...<br><span style="font-size:11px; color:#64748b;">${reason}</span>`;
        const commentInput = document.getElementById('modal-comment-input');
        if (commentInput) {
          commentInput.value = '';
          commentInput.focus();
          for (let char of comment) {
            commentInput.value += char;
            commentInput.dispatchEvent(new Event('input', { bubbles: true }));
            await sleep(6);
          }
        }

        await sleep(250);

        if (decision === 'Approved') {
          const okBtn = document.getElementById('btn-pi-ok');
          okBtn.style.boxShadow = '0 0 12px #16a34a';
          hudStatus.innerHTML = `✅ Clicking <strong>[Approve]</strong> button to commit to Supabase...`;
          await sleep(300);
          okBtn.click();
        } else {
          const holdBtn = document.getElementById('btn-pi-hold');
          holdBtn.style.boxShadow = '0 0 12px #ea580c';
          hudStatus.innerHTML = `⚠️ Clicking <strong>[Put On Hold]</strong> button to commit to Supabase...`;
          await sleep(300);
          holdBtn.click();
        }

        // Wait for modal to close
        let closeWait = 0;
        while (document.getElementById('detail-modal').classList.contains('active') && closeWait < 20) {
          await sleep(100);
          closeWait++;
        }

        row.style.background = '';
        row.style.outline = '';

        processed++;
        const prog = document.getElementById('hud-progress');
        if (prog) prog.style.width = `${Math.round((processed / total) * 100)}%`;

        await sleep(350);
      }

      hud.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#16a34a; font-size:14px;">🎉 Automation Completed</strong>
          <span style="background:#dcfce7; color:#166534; font-size:11px; padding:2px 8px; border-radius:12px; font-weight:bold;">12 of 12 Invoices</span>
        </div>
        <div style="color:#334155; line-height:1.4;">
          All unprocessed invoices have been evaluated via PostgreSQL SQL rules & human interventions, and committed directly to Supabase PostgreSQL!
        </div>
        <button onclick="document.getElementById('autopilot-hud').remove()" style="margin-top:6px; padding:6px 14px; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; cursor:pointer;">Close</button>
      `;
    }

    window.onload = async () => {
      await loadTable();
      checkAutopilotTrigger();
    };
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(ERP_HTML)

@app.route("/api/db-status", methods=["GET"])
def get_db_status():
    return jsonify(db_manager.get_status())

@app.route("/api/invoices", methods=["GET"])
def get_invoices():
    invoices = db_manager.fetch_all()
    pending_count = sum(1 for inv in invoices if inv["status"] in ["Unprocessed", "未処理"])
    return jsonify({
        "total": len(invoices),
        "pending": pending_count,
        "db": db_manager.get_status(),
        "invoices": invoices
    })

@app.route("/api/invoices/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    inv = db_manager.fetch_one(invoice_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify(inv)

@app.route("/api/automation/verify_token", methods=["GET"])
def verify_token():
    token = request.args.get("token", "").strip()
    consumed_data = sql_engine.verify_and_consume_token(token)
    if consumed_data:
        return jsonify({"valid": True, "token_data": consumed_data})
    return jsonify({"valid": False, "error": "Invalid or expired token"}), 400

@app.route("/api/invoices/<invoice_id>/evaluate", methods=["GET"])
def api_evaluate_invoice(invoice_id):
    # Ensure SQL decisions cache is populated from LLM SQL execution against PostgreSQL
    if not DECISION_CACHE_PATH.exists() and GENERATED_JSON_PATH.exists():
        try:
            sql_engine.execute_sql_rules_against_pg()
        except Exception:
            pass

    if DECISION_CACHE_PATH.exists():
        try:
            with open(DECISION_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            ev = cache.get("evaluated_invoices", {})
            if invoice_id in ev:
                item = ev[invoice_id]
                return jsonify({
                    "invoice_id": invoice_id,
                    "decision": item["decision"],
                    "comment": item["comment"],
                    "reason": item.get("discrepancy_detail") or (", ".join(item.get("matched_rules", [])) if item.get("matched_rules") else "SQL Rule Match")
                })
        except Exception as e:
            pass

    inv = db_manager.fetch_one(invoice_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({
        "invoice_id": invoice_id,
        "decision": "On Hold",
        "comment": "Pending LLM SQL policy verification.",
        "reason": "Unprocessed in PostgreSQL"
    })

@app.route("/api/policy", methods=["GET", "POST"])
def handle_policy():
    if request.method == "POST":
        data = request.json or {}
        set_active_policy(data)
        return jsonify({"status": "saved", "policy": get_active_policy()})
    return jsonify(get_active_policy())

@app.route("/api/invoices/<invoice_id>/process", methods=["POST"])
def process_invoice(invoice_id):
    data = request.json or {}
    action = data.get("action", "").lower()
    comment = data.get("comment", "").strip()

    updated = db_manager.update_invoice(invoice_id, action, comment)
    if not updated:
        return jsonify({"error": "Invoice not found"}), 404

    return jsonify({"status": "success", "invoice": updated})

@app.route("/api/reset", methods=["POST"])
def reset_invoices():
    db_manager.reset()
    invoices = db_manager.fetch_all()
    # Refresh SQL decision cache
    sql_engine.execute_sql_rules_against_pg()
    return jsonify({"status": "reset_successful", "total": len(invoices), "db": db_manager.get_status()})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5135, debug=False)
