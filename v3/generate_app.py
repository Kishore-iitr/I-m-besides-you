"""
Builder script for unified_copilot_erp_app.py
Ensures valid JavaScript syntax, removes clutter, cleans headings, provides Excel Import.
"""

import subprocess
import os

HTML_CONTENT = r'''<!DOCTYPE html>
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
      top: 34px;
      z-index: 4;
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
</head>
<body>

  <!-- Top Corporate Header -->
  <header class="erp-header">
    <div class="header-brand">
      <div class="erp-logo-icon">ERP</div>
      <div class="header-title-box">
        <span class="header-title">基幹統合業務システム <span id="app-version-badge" style="background: #10b981; color: white; padding: 2px 7px; border-radius: 9999px; font-size: 10px; font-weight: 700; vertical-align: middle;">v2.7 LIVE</span></span>
        <span class="header-subtitle">企業会計・人事給与 自動照合管理</span>
      </div>
    </div>

    <!-- Dual Suite Navigator (Clean Single Name) -->
    <div class="suite-nav-tabs">
      <button class="nav-tab-btn active" id="tab-invoice" onclick="switchSuite('invoice')">
        🏛️ 財務会計
      </button>
      <button class="nav-tab-btn" id="tab-payroll" onclick="switchSuite('payroll')">
        👥 人事給与
      </button>
    </div>

    <!-- Header Actions -->
    <div class="header-actions">
      <button class="btn-copilot-toggle active" id="btn-toggle-copilot" onclick="toggleCopilotPanel()" title="AI Co-Pilot パネルの表示・非表示切替">
        🤖 AI Co-Pilot
      </button>

      <div class="status-pill llm" onclick="openLlmModal()" title="LLM接続設定">
        <span class="dot" id="llm-dot"></span>
        <span id="llm-pill-text">LLM: Puter (gpt-4o-mini)</span>
      </div>

      <div class="status-pill db" onclick="openDbModal()" title="データベース設定">
        <span class="dot"></span>
        <span id="db-pill-text">DB: PostgreSQL Active</span>
      </div>

      <button class="btn-header" onclick="resetDatabaseBenchmark()" title="初期ベンチマークデータに戻す">
        ↺ データ初期化
      </button>
    </div>
  </header>

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
          <button class="btn-secondary" style="color: #15803d; border-color: #86efac;" onclick="openExcelImportModal()">
            📊 Excel一括取込
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
            <button class="ws-tab-btn active" id="ws-btn-notepad" onclick="switchWsTab('notepad')">
              📋 規程・メモ入力
            </button>
            <button class="ws-tab-btn" id="ws-btn-excel" onclick="switchWsTab('excel')">
              📊 規程マスタ (編集可能)
            </button>
          </div>
        </div>
        <div style="display: flex; gap: 5px; align-items: center; flex-shrink: 0;">
          <button class="btn-secondary" style="padding: 2px 7px; font-size: 10px;" onclick="loadPresetDocument()" title="デフォルト規定メモを再読込">
            規定メモ読込
          </button>
          <button class="btn-secondary" style="padding: 2px 7px; font-size: 11px; font-weight: bold;" onclick="toggleCopilotPanel()" title="Co-Pilotパネルを閉じる">
            ✕
          </button>
        </div>
      </div>

      <!-- Tab 1: Policy / Memo Clean Editor with Small Upload Button -->
      <div id="ws-tab-notepad" class="policy-editor-box">
        <div class="editor-toolbar">
          <span id="notepad-filename" style="max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">月次定額保守取引先一覧.txt (参照規程)</span>
          <div style="display: flex; gap: 4px; align-items: center;">
            <button class="btn-secondary" style="padding: 2px 7px; font-size: 10px; display: inline-flex; align-items: center; gap: 3px;" onclick="document.getElementById('policy-file-input').click()" title="Word文書 (.docx) または テキスト (.txt) を読込">
              📁 規程ファイル選択
            </button>
            <input type="file" id="policy-file-input" accept=".docx,.txt" style="display: none;" onchange="handlePolicyFileUpload(event)">
            <button class="btn-primary" id="btn-analyze" style="padding: 2px 9px; font-size: 10px; background: #0284c7; display: flex; align-items: center; gap: 3px;" onclick="runPolicyAnalysis()" title="LLM analyzes the prompt/policy and extracts condition rules">
              🔍 Analyze
            </button>
            <button class="btn-secondary" style="padding: 2px 5px; font-size: 10px;" onclick="document.getElementById('doc-text').value='';">クリア</button>
            <button class="btn-secondary" style="padding: 2px 5px; font-size: 10px;" onclick="loadPresetDocument()">再読込</button>
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

      <!-- Extracted Active Rules Container (Collapsible & Fully Editable) -->
      <div class="extracted-rules-box" id="extracted-rules-box">
        <div class="rules-header" onclick="toggleLlmOutputCollapse()">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; display: flex; align-items: center; gap: 6px;">
            <span id="llm-collapse-icon" style="transition: transform 0.2s; font-size: 12px;">▼</span>
            <span>🤖 LLM Extracted Rules & Policy Conditions</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="rules-count-badge" id="rules-count-badge">6 Rules Active</span>
            <span style="font-size: 10px; color: #64748b;" id="llm-toggle-text">[ Click to Collapse ]</span>
          </div>
        </div>

        <div class="rules-content-body" id="llm-rules-content">
          <div style="font-size: 11px; color: #475569; margin-bottom: 8px; line-height: 1.4;">
            <strong>Rule SQL Predicate Verification:</strong> SQL conditions below directly evaluate against database columns (<code>raw_amount</code>, <code>type</code>, <code>employee_id</code>). You can verify or edit any SQL command (<code>=</code>, <code>!=</code>, <code>&gt;</code>, <code>IN (...)</code>, <code>NOT IN (...)</code>) or approval/hold action.
          </div>
          <table class="rules-table">
            <thead>
              <tr>
                <th style="width: 28px; text-align: center;">#</th>
                <th style="width: 85px;">Rule ID</th>
                <th style="width: 140px;">Target / Entity</th>
                <th style="min-width: 260px;">SQL Condition / Predicate (Checked vs DB)</th>
                <th style="width: 90px; text-align: center;">Action</th>
                <th style="min-width: 160px;">English Explanation</th>
                <th style="width: 28px; text-align: center;"></th>
              </tr>
            </thead>
            <tbody id="rules-table-body">
              <!-- Fully editable extracted rules -->
            </tbody>
          </table>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 6px; border-top: 1px solid #e2e8f0;">
            <button class="btn-secondary" style="font-size: 10px; padding: 3px 8px;" onclick="addNewExtractedRule()">+ Add Condition Rule</button>
            <button class="btn-primary" id="btn-continue-eval" style="background: var(--success); font-size: 12px; font-weight: 700; padding: 6px 14px; display: flex; align-items: center; gap: 6px;" onclick="continueAndEvaluateDatabase()">
              ▶ Continue & Evaluate Database
            </button>
          </div>
        </div>
      </div>

      <!-- LangGraph Pipeline Visualizer (Retractable) -->
      <div class="graph-tracker-box" id="graph-tracker-box">
        <div class="graph-header" onclick="toggleGraphTrackerCollapse()">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; display: flex; align-items: center; gap: 6px;">
            <span id="graph-collapse-icon" style="transition: transform 0.2s; font-size: 12px;">▼</span>
            <span>⚡ LangGraph 4-Node 実行パイプライン</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span id="graph-overall-badge" style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #e2e8f0; font-weight: 700;">READY</span>
            <span style="font-size: 10px; color: #64748b;" id="graph-toggle-text">[ Click to Collapse ]</span>
          </div>
        </div>

        <div class="graph-content-body" id="graph-content-body">
          <div class="mini-pipeline-container">
            <div class="mini-node node-pending" id="node-1" title="Node 1: parse_document_to_schema_json">
              <span class="mini-node-num">1</span>
              <span class="mini-node-label">Parse</span>
              <span class="mini-node-time" id="time-node-1">-</span>
            </div>
            <span class="mini-pipeline-arrow">➔</span>
            <div class="mini-node node-pending" id="node-2" title="Node 2: compare_features_and_decide">
              <span class="mini-node-num">2</span>
              <span class="mini-node-label">Decide</span>
              <span class="mini-node-time" id="time-node-2">-</span>
            </div>
            <span class="mini-pipeline-arrow">➔</span>
            <div class="mini-node node-pending" id="node-3" title="Node 3: commit_database_updates">
              <span class="mini-node-num">3</span>
              <span class="mini-node-label">Commit</span>
              <span class="mini-node-time" id="time-node-3">-</span>
            </div>
            <span class="mini-pipeline-arrow">➔</span>
            <div class="mini-node node-pending" id="node-4" title="Node 4: human_in_the_loop_audit">
              <span class="mini-node-num">4</span>
              <span class="mini-node-label">Audit</span>
              <span class="mini-node-time" id="time-node-4">-</span>
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
      </div>
    </aside>
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

  <!-- Modal 4: Excel / CSV Bulk Import Dialog -->
  <div class="modal-overlay" id="excel-import-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>📊 Excel / CSV 一括取込 (Bulk Import)</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeExcelImportModal()">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 11px; color: #475569; margin-bottom: 8px;">
          Excelスプレッドシートの行をコピーして貼り付けるか、CSVファイルを選択して複数伝票を一括登録できます。
        </p>
        <div class="form-group">
          <label>Excelから貼り付け (タブ区切り / カンマ区切り):</label>
          <textarea id="bulk-paste-text" class="form-control" rows="6" placeholder="P6-07010448-106&#9;V3005&#9;Global Tech LLC&#9;¥716,232&#9;Routine&#10;P6-07010448-107&#9;V3006&#9;Hokuriku Parts&#9;¥455,128&#9;Routine"></textarea>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
          <button class="btn-secondary" style="font-size: 11px;" onclick="previewBulkSpreadsheet()">📋 解析プレビュー</button>
          <input type="file" id="bulk-file-input" accept=".csv,.tsv,.txt" style="display: none;" onchange="handleBulkFileSelect(event)">
          <button class="btn-secondary" style="font-size: 11px;" onclick="document.getElementById('bulk-file-input').click()">📁 CSVファイル選択</button>
        </div>
        <div id="bulk-preview-summary" style="font-size: 11px; color: #1e3a8a; font-weight: 700; margin-bottom: 6px;"></div>
        <div id="bulk-preview-container" style="max-height: 150px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 4px; display: none;">
          <table class="erp-table" style="font-size: 10px;">
            <thead id="bulk-preview-head"></thead>
            <tbody id="bulk-preview-body"></tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeExcelImportModal()">キャンセル</button>
        <button class="btn-primary" style="background: var(--success);" onclick="submitBulkImport()">一括登録を実行 (Import to DB)</button>
      </div>
    </div>
  </div>

  <!-- Modal 5: LLM Configuration Dialog -->
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
        <button class="btn-secondary" onclick="testLlmConnection()">⚡ 接続テスト</button>
        <button class="btn-primary" onclick="saveLlmSettings()">設定を保存</button>
      </div>
    </div>
  </div>

  <!-- Modal 6: Database Connection Dialog (Remote Postgres & Local SQLite) -->
  <div class="modal-overlay" id="db-modal">
    <div class="modal-card">
      <div class="modal-header">
        <span>🗄️ データベース接続設定</span>
        <button class="btn-secondary" style="padding: 2px 6px;" onclick="closeDbModal()">✕</button>
      </div>
      <div class="modal-body">
        <div style="font-size: 12px; color: #475569; margin-bottom: 12px;">
          現在の接続先: <strong id="modal-db-current" style="color: var(--primary);">PostgreSQL</strong>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-bottom: 14px;">
          <div style="font-weight: 700; font-size: 12px; color: #1e3a8a; margin-bottom: 6px;">1. リモート PostgreSQL / Supabase 接続</div>
          <div class="form-group" style="margin-bottom: 8px;">
            <label>PostgreSQL 接続URI:</label>
            <input type="text" id="db-uri-input" class="form-control" placeholder="postgresql://postgres:password@host:5432/postgres">
          </div>
          <button class="btn-primary" style="font-size: 11px;" onclick="connectCustomDb()">PostgreSQL へ接続</button>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;">
          <div style="font-weight: 700; font-size: 12px; color: #15803d; margin-bottom: 6px;">2. ローカル SQLite データベース (ファイルパス指定)</div>
          <div class="form-group" style="margin-bottom: 8px;">
            <label>ローカル DB ファイルパス:</label>
            <input type="text" id="db-local-path-input" class="form-control" placeholder="C:/Users/.../erp_local.db または ./erp_unified.db">
            <small style="color: #64748b; font-size: 11px;">※ 指定したパスにファイルが存在しない場合は自動初期化されます</small>
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

    /* --- Core Staged Evaluation, Human Intervention & Modal Logic (Hoisted Globally) --- */
    function renderInterventions(discrepancies) {
      try {
        const container = document.getElementById('interventions-container');
        const list = document.getElementById('interventions-list');
        if (!container || !list) return;

        if (!discrepancies || discrepancies.length === 0) {
          container.style.display = 'none';
          list.innerHTML = '';
          return;
        }

        container.style.display = 'block';
        list.innerHTML = discrepancies.map(function(d) {
          const reasonText = (d.reasons && d.reasons.length > 0) ? d.reasons[0] : (d.rule_summary || '要確認・監査精査');
          return '<div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px; font-size: 11px;">' +
            '<div style="display: flex; justify-content: space-between; align-items: center;">' +
              '<strong style="color: #92400e;">⚠️ ' + (d.id || '-') + ' (' + (d.name || '-') + ')</strong>' +
              '<span style="color: #b45309; font-weight: 700;">' + (d.amount || '-') + '</span>' +
            '</div>' +
            '<div style="color: #78350f; margin-top: 3px; font-size: 11px;">' + reasonText + '</div>' +
          '</div>';
        }).join('');
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

      const tabInv = document.getElementById('tab-invoice');
      const tabPay = document.getElementById('tab-payroll');

      if (suite === 'invoice') {
        tabInv.classList.add('active');
        tabPay.classList.remove('active');

        document.getElementById('table-suite-title').innerText = '財務会計 - 請求書一覧';
        document.getElementById('metric-label-approved').innerText = '自動承認済';
        document.getElementById('notepad-filename').innerText = '月次定額保守取引先一覧.txt (参照規程)';
        document.getElementById('doc-text').value = INVOICE_PRESET;
        document.getElementById('excel-master-title').innerText = '📊 月次定額取引先契約マスタ (編集可能)';
      } else {
        tabPay.classList.add('active');
        tabInv.classList.remove('active');

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

    /* --- Status Check & Refresh --- */
    async function updateSystemStatus() {
      try {
        const dbRes = await fetch('/api/database/status').then(function(r) { return r.json(); });
        const pillText = document.getElementById('db-pill-text');
        pillText.innerText = 'DB: ' + dbRes.display_target;
        document.getElementById('modal-db-current').innerText = dbRes.display_target;
        if (dbRes.sqlite_path) {
          document.getElementById('db-local-path-input').value = dbRes.sqlite_path;
        }

        const llmRes = await fetch('/api/llm/status').then(function(r) { return r.json(); });
        document.getElementById('llm-pill-text').innerText = 'LLM: ' + llmRes.display;
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
          '<td>' + (r.employee_id || '-') + '</td>' +
          '<td>' + r.name + '</td>' +
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
      isGraphTrackerCollapsed = !isGraphTrackerCollapsed;
      const content = document.getElementById('graph-content-body');
      const icon = document.getElementById('graph-collapse-icon');
      const text = document.getElementById('graph-toggle-text');
      if (isGraphTrackerCollapsed) {
        content.classList.add('collapsed');
        icon.innerText = '►';
        text.innerText = '[ Click to Expand ]';
      } else {
        content.classList.remove('collapsed');
        icon.innerText = '▼';
        text.innerText = '[ Click to Collapse ]';
      }
    }

    /* --- Row Quick Action: Approve or Disapprove (Hold) --- */
    async function quickApproveRow(rowId) {
      const targetStatus = (currentSuite === 'invoice') ? 'Approved' : 'Confirmed';
      const defaultComment = (currentSuite === 'invoice') 
        ? '月次定額取引先一覧照合完了・請求金額及び消費税額整合確認済 (Approved)'
        : '業務委託経費規程適合確認済・経費精算確定 (Confirmed)';

      const records = (currentSuite === 'invoice') ? invoiceRecords : payrollRecords;
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
      const records = (currentSuite === 'invoice') ? invoiceRecords : payrollRecords;
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
      if (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected') {
        return num ? ('raw_amount > ' + num) : 'status = \'Hold\'';
      } else {
        return num ? ('type = \'Routine\' AND raw_amount = ' + num) : 'type = \'Routine\'';
      }
    }

    function renderInitialExtractedRules() {
      if (currentSuite === 'invoice') {
        activeExtractedRules = [
          { rule_id: 'RULE-INV-01', match_value: 'Global Tech LLC (V3005)', condition: "type = 'Routine' AND raw_amount = 716232 AND employee_id = 'V3005'", sql_condition: "type = 'Routine' AND raw_amount = 716232 AND employee_id = 'V3005'", action_on_match: 'Approved', description: 'Recurring SaaS contract rate matched' },
          { rule_id: 'RULE-INV-02', match_value: 'Hokuriku Parts (V3006)', condition: "type = 'Routine' AND raw_amount IN (455128, 452219) AND employee_id = 'V3006'", sql_condition: "type = 'Routine' AND raw_amount IN (455128, 452219) AND employee_id = 'V3006'", action_on_match: 'Approved', description: 'Routine parts maintenance contract matched' },
          { rule_id: 'RULE-INV-03', match_value: 'Yamato Shoji (V3002)', condition: "type = 'Routine' AND raw_amount IN (1237439, 1218687) AND employee_id = 'V3002'", sql_condition: "type = 'Routine' AND raw_amount IN (1237439, 1218687) AND employee_id = 'V3002'", action_on_match: 'Approved', description: 'Business outsourcing contract verified' },
          { rule_id: 'RULE-INV-04', match_value: 'Fukuoka System (V3007)', condition: "type = 'Routine' AND raw_amount IN (1832962, 1993825, 1685384) AND employee_id = 'V3007'", sql_condition: "type = 'Routine' AND raw_amount IN (1832962, 1993825, 1685384) AND employee_id = 'V3007'", action_on_match: 'Approved', description: 'IT infrastructure maintenance contract matched' },
          { rule_id: 'RULE-INV-05', match_value: 'Hokuriku Parts (V3006) Adjustment', condition: "employee_id = 'V3006' AND type = 'Adjustment'", sql_condition: "employee_id = 'V3006' AND type = 'Adjustment'", action_on_match: 'Hold', description: 'Emergency air freight surcharge inspection per policy' },
          { rule_id: 'RULE-INV-ADJ', match_value: 'Okinawa Logistics (V3008)', condition: "employee_id = 'V3008' AND type = 'Adjustment'", sql_condition: "employee_id = 'V3008' AND type = 'Adjustment'", action_on_match: 'Hold', description: 'Logistics delivery receipt and manager review required' },
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
        const data = await res.json();
        if (data.success && data.rules && data.rules.length > 0) {
          activeExtractedRules = data.rules;
          renderExtractedRulesTable();
          setNodeDone('node-1', '0.18s');
          if (isLlmOutputCollapsed) toggleLlmOutputCollapse();
          alert('LLM Analysis complete: ' + activeExtractedRules.length + ' rules extracted. You can edit conditions, actions, or descriptions before continuing.');
        } else {
          setNodeDone('node-1', '0.12s');
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

    async function continueAndEvaluateDatabase() {
      const docText = document.getElementById('doc-text').value.trim();
      if (isGraphTrackerCollapsed) {
        toggleGraphTrackerCollapse();
      }
      resetGraphUi();
      setNodeDone('node-1', '0.15s');
      setNodeActive('node-2');

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
          setNodeDone('node-2', '0.22s');
          setNodeDone('node-3', 'Ready');
          stagedDecisionsData = result.staged_decisions || [];
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

    function loadPresetDocument() {
      document.getElementById('doc-text').value = (currentSuite === 'invoice') ? INVOICE_PRESET : PAYROLL_PRESET;
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
          alert('規程ファイル (' + data.filename + ') を読み込みました。');
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

    /* --- Excel / CSV Bulk Import Modal --- */
    function openExcelImportModal() {
      parsedBulkData = [];
      document.getElementById('bulk-preview-container').style.display = 'none';
      document.getElementById('bulk-preview-summary').innerText = '';
      document.getElementById('excel-import-modal').style.display = 'flex';
    }

    function closeExcelImportModal() {
      document.getElementById('excel-import-modal').style.display = 'none';
    }

    function previewBulkSpreadsheet() {
      const text = document.getElementById('bulk-paste-text').value.trim();
      if (!text) {
        alert('貼り付けデータがありません。Excelからデータをコピーしてください。');
        return;
      }

      const lines = text.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
      parsedBulkData = [];

      lines.forEach(function(line, idx) {
        const parts = line.indexOf('\t') !== -1 ? line.split('\t') : line.split(',');
        if (parts.length >= 3) {
          if (currentSuite === 'invoice') {
            const id = parts[0].trim() || ('P6-07010448-' + (invoiceRecords.length + idx + 1).toString().padStart(3, '0'));
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
            const id = parts[0].trim() || ('P4-07089771-' + (payrollRecords.length + idx + 1).toString().padStart(3, '0'));
            const code = parts[1].trim() || 'EMP-001';
            const name = parts[2].trim() || '新規従業員';
            const cat = parts[3] ? parts[3].trim() : '経費精算';
            const rawAmt = parseInt(parts[4] ? parts[4].replace(/[¥,]/g, '').trim() : '0', 10) || 50000;
            const type = parts[5] ? parts[5].trim() : (cat.indexOf('控除') !== -1 ? 'Deduction' : 'Addition');

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

      summary.innerText = '解析完了: ' + parsedBulkData.length + ' 件の伝票データを抽出';
      container.style.display = 'block';

      if (currentSuite === 'invoice') {
        tableHead.innerHTML = '<tr><th>ID</th><th>コード</th><th>企業名</th><th>金額</th><th>区分</th></tr>';
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
          return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.name + '</td><td>' + r.amount + '</td><td>' + r.type + '</td></tr>';
        }).join('') + (parsedBulkData.length > 15 ? '<tr><td colspan="5" style="text-align:center;">... 他 ' + (parsedBulkData.length - 15) + ' 件 ...</td></tr>' : '');
      } else {
        tableHead.innerHTML = '<tr><th>ID</th><th>社員ID</th><th>氏名</th><th>項目</th><th>区分</th><th>金額</th></tr>';
        tableBody.innerHTML = parsedBulkData.slice(0, 15).map(function(r) {
          return '<tr><td>' + r.id + '</td><td>' + r.employee_id + '</td><td>' + r.employee_name + '</td><td>' + r.item_category + '</td><td>' + r.item_type + '</td><td>' + r.amount + '</td></tr>';
        }).join('') + (parsedBulkData.length > 15 ? '<tr><td colspan="6" style="text-align:center;">... 他 ' + (parsedBulkData.length - 15) + ' 件 ...</td></tr>' : '');
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

    async function submitBulkImport() {
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
          alert('一括取込完了: ' + d.count + ' 件の伝票データをデータベースへ登録しました。');
          closeExcelImportModal();
          loadTableData();
        } else {
          alert('一括取込に失敗しました。');
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
      for (let i = 1; i <= 4; i++) {
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
</body>
</html>
'''

# Write test script to verify JS with node
with open("test_rendered.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)

import re
m = re.search(r'<script[\s\S]*?</script>', HTML_CONTENT)
if m:
    clean_js = m.group(0).replace('<script>', '').replace('</script>', '')
    with open("test_script.js", "w", encoding="utf-8") as f:
        f.write(clean_js)

print("Generated test files, testing syntax with Node.js...")
res = subprocess.run(["node", "-c", "test_script.js"], capture_output=True, text=True)
print("Node -c returncode:", res.returncode)
if res.returncode != 0:
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
else:
    print("JAVASCRIPT SYNTAX IS 100% VALID!")
