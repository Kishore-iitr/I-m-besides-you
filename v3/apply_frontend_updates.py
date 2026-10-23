import re
import subprocess
import sys

with open("generate_app.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("\r\n", "\n")

# 1. Update body & html CSS
old_body_css = """    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    body { background-color: #f1f5f9; color: var(--text-main); font-size: 13px; line-height: 1.45; min-height: 100vh; display: flex; flex-direction: column; }"""

new_body_css = """    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    html, body { height: 100%; overflow: hidden; }
    body { background-color: #f1f5f9; color: var(--text-main); font-size: 13px; line-height: 1.45; display: flex; flex-direction: column; }"""

assert old_body_css in code, "old_body_css not found"
code = code.replace(old_body_css, new_body_css)

# 2. Update .main-layout & .workspace-panel CSS
old_layout_css = """    /* Main Resizable Layout */
    .main-layout {
      display: flex;
      flex-direction: row;
      gap: 0;
      padding: 12px 18px;
      flex: 1;
      align-items: stretch;
      min-height: calc(100vh - 75px);
      position: relative;
    }

    /* Side Workspace Panel (Resizable Width) */
    .workspace-panel {
      width: 480px;
      min-width: 320px;
      max-width: 850px;
      flex-shrink: 0;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      height: auto;
      align-self: stretch;
    }"""

new_layout_css = """    /* Main Resizable Layout - Constant Viewport Height */
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
      max-width: 850px;
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
    }"""

assert old_layout_css in code, "old_layout_css not found"
code = code.replace(old_layout_css, new_layout_css)

# 3. Update LangGraph CSS to ultra-compact horizontal pipeline
old_graph_css = """    .graph-steps-container {
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
    }"""

new_graph_css = """    /* Ultra-Compact Horizontal LangGraph Pipeline with Execution Timers */
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
    }"""

assert old_graph_css in code, "old_graph_css not found"
code = code.replace(old_graph_css, new_graph_css)

# 4. Update .erp-content and .table-scroll-container CSS
old_erp_css = """    /* Right: ERP Table Section */
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
      height: auto;
      align-self: stretch;
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
      min-height: 520px;
      max-height: none;
      overflow-y: auto;
    }"""

new_erp_css = """    /* Left: ERP Table Section (Constant Height with Scrollable List) */
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
    }"""

assert old_erp_css in code, "old_erp_css not found"
code = code.replace(old_erp_css, new_erp_css)

# 5. Update HTML LangGraph pipeline visualizer
old_html_graph = """          <div class="graph-steps-container">
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
          </div>"""

new_html_graph = """          <div class="mini-pipeline-container">
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
          </div>"""

assert old_html_graph in code, "old_html_graph not found"
code = code.replace(old_html_graph, new_html_graph)

# 6. Update Extracted Rules Header & Description
old_rules_header = """          <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">
            Review or edit any condition, vendor target, or approval/hold action below. Click <strong>Continue & Evaluate Database</strong> to verify against database rows.
          </div>
          <table class="rules-table">
            <thead>
              <tr>
                <th style="width: 25px;">#</th>
                <th style="width: 85px;">Rule ID</th>
                <th style="width: 125px;">Target / Entity</th>
                <th>Condition / Threshold</th>
                <th style="width: 95px;">Action</th>
                <th>English Explanation</th>
                <th style="width: 25px;"></th>
              </tr>
            </thead>"""

new_rules_header = """          <div style="font-size: 11px; color: #475569; margin-bottom: 8px; line-height: 1.4;">
            <strong>Rule Logic Verification:</strong> Conditions below explicitly evaluate table columns (<code>raw_amount</code>, <code>type</code>, <code>employee_id</code>). You can verify or edit any formula, threshold (<code>==</code>, <code>&lt;=</code>, <code>&gt;</code>, <code>!=</code>), or approval/hold action.
          </div>
          <table class="rules-table">
            <thead>
              <tr>
                <th style="width: 25px;">#</th>
                <th style="width: 80px;">Rule ID</th>
                <th style="width: 125px;">Target / Entity</th>
                <th style="min-width: 190px;">Condition / Threshold (Checked vs DB)</th>
                <th style="width: 95px;">Action</th>
                <th>English Explanation</th>
                <th style="width: 25px;"></th>
              </tr>
            </thead>"""

assert old_rules_header in code, "old_rules_header not found"
code = code.replace(old_rules_header, new_rules_header)

# 7. Update renderInitialExtractedRules and renderExtractedRulesTable
old_render_rules = """    function renderInitialExtractedRules() {
      if (currentSuite === 'invoice') {
        activeExtractedRules = [
          { rule_id: 'RULE-INV-01', match_value: 'Global Tech LLC (V3005)', condition: 'Monthly fee ¥716,232 (Routine)', action_on_match: 'Approved', description: 'Recurring SaaS contract rate matched' },
          { rule_id: 'RULE-INV-02', match_value: 'Hokuriku Parts (V3006)', condition: 'Fixed fee ¥455,128 / ¥452,219', action_on_match: 'Approved', description: 'Routine parts maintenance contract matched' },
          { rule_id: 'RULE-INV-03', match_value: 'Yamato Shoji (V3002)', condition: 'Fixed fee ¥1,237,439 / ¥1,218,687', action_on_match: 'Approved', description: 'Business outsourcing contract verified' },
          { rule_id: 'RULE-INV-04', match_value: 'Fukuoka System (V3007)', condition: 'IT infrastructure support (Routine)', action_on_match: 'Approved', description: 'Core IT systems operational contract' },
          { rule_id: 'RULE-INV-ADJ', match_value: 'Okinawa Logistics (V3008)', condition: 'Voucher category is Adjustment', action_on_match: 'Hold', description: 'Logistics delivery receipt and manager review required' },
          { rule_id: 'RULE-INV-CEIL', match_value: 'All Vendors', condition: 'Billing Amount > ¥2,000,000', action_on_match: 'Hold', description: 'Exceeds auto-approval limit, board director authorization required' }
        ];
      } else {
        activeExtractedRules = [
          { rule_id: 'RULE-PAY-01', match_value: 'Takuya Aoki (P4-07089771-001)', condition: 'Training fee ¥77,224 (under ¥100k)', action_on_match: 'Confirmed', description: 'Article 4 technical training regulation compliant' },
          { rule_id: 'RULE-PAY-02', match_value: 'Rie Kikuchi (P4-07089771-002)', condition: 'Consumables ¥55,571 (under ¥100k)', action_on_match: 'Confirmed', description: 'Development consumables receipt verified' },
          { rule_id: 'RULE-PAY-03', match_value: 'Yuji Sakamoto (P4-07089771-003)', condition: 'Travel expense ¥64,200', action_on_match: 'Confirmed', description: 'Osaka branch technical trip report matched' },
          { rule_id: 'RULE-PAY-ENT', match_value: 'All Staff (Entertainment)', condition: 'Amount > ¥100,000', action_on_match: 'Hold', description: 'Article 7 limit exceeded, executive special sanction required' },
          { rule_id: 'RULE-PAY-CLASS', match_value: 'Dependent Deduction / Position Abolition', condition: 'Registered as Addition', action_on_match: 'Hold', description: 'Classification error (Deduction registered as Addition)' },
          { rule_id: 'RULE-PAY-CEIL', match_value: 'All Expense Items', condition: 'Single Amount > ¥150,000', action_on_match: 'Hold', description: 'Exceeds standard single ceiling, prior approval memo required' },
          { rule_id: 'RULE-PAY-UNK', match_value: 'All Allowance Items', condition: 'Undefined in HR master', action_on_match: 'Hold', description: 'Unregistered allowance code requires HR authorization' }
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
        return '<tr>' +
          '<td style="text-align: center; color: #64748b;">' + (idx + 1) + '</td>' +
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', &quot;rule_id&quot;, this.value)" style="width: 75px; font-weight: 600;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', &quot;match_value&quot;, this.value)"></td>' +
          '<td><input type="text" value="' + (r.condition || '') + '" onchange="updateRuleCell(' + idx + ', &quot;condition&quot;, this.value)"></td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', &quot;action_on_match&quot;, this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + ';">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', &quot;description&quot;, this.value)"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    }"""

new_render_rules = """    function formatConditionDisplay(r) {
      let c = (r.condition || '').trim();
      if (!c || /^\\d+$/.test(c)) {
        const num = c ? parseInt(c, 10) : (r.expected_amount || r.threshold_amount || 0);
        if (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected') {
          c = 'Amount > ¥' + Number(num).toLocaleString() + ' (Ceiling Limit -> Hold)';
        } else {
          c = 'Category == \\'Routine\\' && Amount == ¥' + Number(num).toLocaleString() + ' (Fixed Rate)';
        }
      }
      return c;
    }

    function renderInitialExtractedRules() {
      if (currentSuite === 'invoice') {
        activeExtractedRules = [
          { rule_id: 'RULE-INV-01', match_value: 'Global Tech LLC (V3005)', condition: "Category == 'Routine' && Amount == ¥716,232 (Fixed Rate)", action_on_match: 'Approved', description: 'Recurring SaaS contract rate matched' },
          { rule_id: 'RULE-INV-02', match_value: 'Hokuriku Parts (V3006)', condition: "Category == 'Routine' && Amount in [¥455,128, ¥452,219] (Contract Range)", action_on_match: 'Approved', description: 'Routine parts maintenance contract matched' },
          { rule_id: 'RULE-INV-03', match_value: 'Yamato Shoji (V3002)', condition: "Category == 'Routine' && Amount in [¥1,237,439, ¥1,218,687] (Contract Range)", action_on_match: 'Approved', description: 'Business outsourcing contract verified' },
          { rule_id: 'RULE-INV-04', match_value: 'Fukuoka System (V3007)', condition: "Category == 'Routine' (Standard Maintenance)", action_on_match: 'Approved', description: 'Core IT systems operational contract' },
          { rule_id: 'RULE-INV-ADJ', match_value: 'Okinawa Logistics (V3008)', condition: "Category == 'Adjustment' (Requires Manager Audit -> Hold)", action_on_match: 'Hold', description: 'Logistics delivery receipt and manager review required' },
          { rule_id: 'RULE-INV-CEIL', match_value: 'All Vendors', condition: "Amount > ¥2,000,000 (Exceeds Executive Limit -> Hold)", action_on_match: 'Hold', description: 'Exceeds auto-approval limit, board director authorization required' }
        ];
      } else {
        activeExtractedRules = [
          { rule_id: 'RULE-PAY-01', match_value: 'Takuya Aoki (P4-07089771-001)', condition: "Voucher == 'P4-07089771-001' && Amount <= ¥100,000 (Training)", action_on_match: 'Confirmed', description: 'Article 4 technical training regulation compliant' },
          { rule_id: 'RULE-PAY-02', match_value: 'Rie Kikuchi (P4-07089771-002)', condition: "Voucher == 'P4-07089771-002' && Amount <= ¥100,000 (Consumables)", action_on_match: 'Confirmed', description: 'Development consumables receipt verified' },
          { rule_id: 'RULE-PAY-03', match_value: 'Yuji Sakamoto (P4-07089771-003)', condition: "Voucher == 'P4-07089771-003' && Amount <= ¥100,000 (Travel)", action_on_match: 'Confirmed', description: 'Osaka branch technical trip report matched' },
          { rule_id: 'RULE-PAY-ENT', match_value: 'All Staff (Entertainment)', condition: "Category == 'Entertainment' && Amount > ¥100,000 -> Hold", action_on_match: 'Hold', description: 'Article 7 limit exceeded, executive special sanction required' },
          { rule_id: 'RULE-PAY-CLASS', match_value: 'Dependent Deduction / Position Abolition', condition: "Classification == 'Addition' for Dependent/Position -> Hold", action_on_match: 'Hold', description: 'Classification error (Deduction registered as Addition)' },
          { rule_id: 'RULE-PAY-CEIL', match_value: 'All Expense Items', condition: "Single Amount > ¥150,000 -> Hold", action_on_match: 'Hold', description: 'Exceeds standard single ceiling, prior approval memo required' },
          { rule_id: 'RULE-PAY-UNK', match_value: 'All Allowance Items', condition: "Allowance Code NOT in HR Master -> Hold", action_on_match: 'Hold', description: 'Unregistered allowance code requires HR authorization' }
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
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', &quot;rule_id&quot;, this.value)" style="width: 75px; font-weight: 600;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', &quot;match_value&quot;, this.value)"></td>' +
          '<td>' +
            '<input type="text" value="' + condVal.replace(/"/g, '&quot;') + '" onchange="updateRuleCell(' + idx + ', &quot;condition&quot;, this.value)" style="width: 100%; font-family: Consolas, monospace; font-size: 11px;">' +
            '<div style="font-size: 10px; color: ' + (isHold ? '#b91c1c' : '#15803d') + '; margin-top: 2px; font-weight: 600;">' +
              (isHold ? '⚡ Hold Trigger (Checked against DB fields)' : '✓ Auto-Approval Rule (Checked against DB fields)') +
            '</div>' +
          '</td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', &quot;action_on_match&quot;, this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + ';">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', &quot;description&quot;, this.value)"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    }"""

assert old_render_rules in code, "old_render_rules not found"
code = code.replace(old_render_rules, new_render_rules)

# 8. Update graph helper functions
old_graph_helpers = """    /* --- Visual Graph Helper Functions --- */
    function resetGraphUi() {
      for (let i = 1; i <= 4; i++) {
        const n = document.getElementById('node-' + i);
        if (n) {
          n.className = 'graph-node node-pending';
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
    }"""

new_graph_helpers = """    /* --- Visual Graph Helper Functions (Ultra-Compact Pipeline) --- */
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
    }"""

assert old_graph_helpers in code, "old_graph_helpers not found"
code = code.replace(old_graph_helpers, new_graph_helpers)

with open("generate_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("generate_app.py updated successfully!")
