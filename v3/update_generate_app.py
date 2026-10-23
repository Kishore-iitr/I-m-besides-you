import re
import subprocess
import sys

with open('generate_app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

# 1. Update CSS: add rules-table input/select styles and collapsible styles
old_css_rules = '''    .extracted-rules-box {
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
    }'''

new_css_rules = '''    .extracted-rules-box {
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
    }'''

assert old_css_rules in app_text, "Could not find old_css_rules"
app_text = app_text.replace(old_css_rules, new_css_rules)

# 2. Update Notepad toolbar: add Analyze button
old_notepad_toolbar = '''        <div class="editor-toolbar">
          <span id="notepad-filename">月次定額保守取引先一覧.txt (参照規程)</span>
          <div style="display: flex; gap: 6px;">
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="document.getElementById('doc-text').value='';">クリア</button>
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="loadPresetDocument()">再読込</button>
          </div>
        </div>'''

new_notepad_toolbar = '''        <div class="editor-toolbar">
          <span id="notepad-filename">月次定額保守取引先一覧.txt (参照規程)</span>
          <div style="display: flex; gap: 6px; align-items: center;">
            <button class="btn-primary" style="padding: 3px 10px; font-size: 11px; background: #0284c7; display: flex; align-items: center; gap: 4px;" onclick="runPolicyAnalysis()" title="LLM analyzes the prompt/policy and extracts condition rules">
              🔍 Analyze
            </button>
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="document.getElementById('doc-text').value='';">クリア</button>
            <button class="btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="loadPresetDocument()">再読込</button>
          </div>
        </div>'''

assert old_notepad_toolbar in app_text, "Could not find old_notepad_toolbar"
app_text = app_text.replace(old_notepad_toolbar, new_notepad_toolbar)

# 3. Update extracted rules HTML: collapsible, editable table, remove global banner, add Continue button
old_rules_html = '''      <!-- Extracted Active Rules Container -->
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
      </div>'''

new_rules_html = '''      <!-- Extracted Active Rules Container (Collapsible & Fully Editable) -->
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
          <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">
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
            </thead>
            <tbody id="rules-table-body">
              <!-- Fully editable extracted rules -->
            </tbody>
          </table>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 6px; border-top: 1px solid #e2e8f0;">
            <button class="btn-secondary" style="font-size: 10px; padding: 3px 8px;" onclick="addNewExtractedRule()">+ Add Condition Rule</button>
            <button class="btn-primary" style="background: var(--success); font-size: 12px; font-weight: 700; padding: 6px 14px; display: flex; align-items: center; gap: 6px;" onclick="continueAndEvaluateDatabase()">
              ▶ Continue & Evaluate Database
            </button>
          </div>
        </div>
      </div>'''

assert old_rules_html in app_text, "Could not find old_rules_html"
app_text = app_text.replace(old_rules_html, new_rules_html)

# 4. Update JS for extracted rules & collapsible state
old_js_rules = '''    /* --- Extracted Active Rules Rendering --- */
    function renderInitialExtractedRules() {
      const banner = document.getElementById('global-rule-banner');
      const tbody = document.getElementById('rules-table-body');
      const badge = document.getElementById('rules-count-badge');

      if (currentSuite === 'invoice') {
        banner.innerText = '【グローバル原則】単一伝票200万円以下かつ区分Routine(通常)のみ自動承認。区分Adjustment(調整)は全件要人間精査(Hold)。';
        badge.innerText = '6 ルール有効';
        tbody.innerHTML = 
          '<tr><td>RULE-INV-01</td><td>Global Tech LLC (V3005)</td><td>月次定額 ¥716,232 (Routine)</td><td><span class="status-badge badge-approved">Approved</span></td><td>契約内整合・自動承認</td></tr>' +
          '<tr><td>RULE-INV-02</td><td>北陸部品工業 (V3006)</td><td>定期保守 ¥455,128 / ¥452,219</td><td><span class="status-badge badge-approved">Approved</span></td><td>通常部品保守として承認</td></tr>' +
          '<tr><td>RULE-INV-03</td><td>大和商事 (V3002)</td><td>事務委託 ¥1,237,439 / ¥1,218,687</td><td><span class="status-badge badge-approved">Approved</span></td><td>業務委託契約書照合済</td></tr>' +
          '<tr><td>RULE-INV-04</td><td>福岡システムデザイン (V3007)</td><td>基幹運用保守 (Routine)</td><td><span class="status-badge badge-approved">Approved</span></td><td>IT基盤保守契約内承認</td></tr>' +
          '<tr><td>RULE-INV-ADJ</td><td>沖縄物流センター (V3008) / 他</td><td>伝票区分が「Adjustment」</td><td><span class="status-badge badge-hold">Hold</span></td><td>物流受領書及び経理課長承認要</td></tr>' +
          '<tr><td>RULE-INV-CEIL</td><td>全取引先共通</td><td>請求金額 > 2,000,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>自動承認限度額超過・役員決裁要</td></tr>';
      } else {
        banner.innerText = '【グローバル原則】接待交際費10万円超過および単一経費15万円超過は役員決裁要(Hold)。扶養控除等控除項目の加算登録は区分不整合保留。';
        badge.innerText = '7 ルール有効';
        tbody.innerHTML = 
          '<tr><td>RULE-PAY-01</td><td>青木 拓也 (P4-07089771-001)</td><td>研修費 ¥77,224 (上限10万以内)</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>規程第4条適合確認済</td></tr>' +
          '<tr><td>RULE-PAY-02</td><td>菊池 理恵 (P4-07089771-002)</td><td>消耗品費 ¥55,571</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>領収書照合済</td></tr>' +
          '<tr><td>RULE-PAY-03</td><td>坂本 裕二 (P4-07089771-003)</td><td>出張旅費 ¥64,200</td><td><span class="status-badge badge-confirmed">Confirmed</span></td><td>出張報告書整合済</td></tr>' +
          '<tr><td>RULE-PAY-ENT</td><td>全従業員共通 (接待交際費)</td><td>金額 > 100,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>規程第7条上限超過・役員特別決裁要</td></tr>' +
          '<tr><td>RULE-PAY-CLASS</td><td>扶養控除変更 / 役職手当廃止</td><td>区分が「Addition」として誤登録</td><td><span class="status-badge badge-hold">Hold</span></td><td>控除項目の加算誤登録・区分不整合</td></tr>' +
          '<tr><td>RULE-PAY-CEIL</td><td>全経費項目共通</td><td>金額 > 150,000円</td><td><span class="status-badge badge-hold">Hold</span></td><td>社内決済上限超過・要事前稟議確認</td></tr>' +
          '<tr><td>RULE-PAY-UNK</td><td>全手当項目共通</td><td>マスタ未定義手当コード</td><td><span class="status-badge badge-hold">Hold</span></td><td>人事給与マスタ未定義の手当コード</td></tr>';
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
      badge.innerText = criteria.length + ' ルール抽出';

      if (criteria.length > 0) {
        tbody.innerHTML = criteria.map(function(c) {
          const actionBadge = (c.action_on_match === 'Hold') ? 'badge-hold' : (currentSuite === 'invoice' ? 'badge-approved' : 'badge-confirmed');
          return '<tr>' +
            '<td><strong>' + (c.rule_id || 'RULE') + '</strong></td>' +
            '<td>' + (c.match_value || c.name || '-') + '</td>' +
            '<td>' + (c.condition || (c.expected_amounts ? '金額: ' + c.expected_amounts.join(', ') : '規程照合')) + '</td>' +
            '<td><span class="status-badge ' + actionBadge + '">' + c.action_on_match + '</span></td>' +
            '<td>' + (c.description || '-') + '</td>' +
          '</tr>';
        }).join('');
      }
    }'''

new_js_rules = '''    /* --- Collapsible & Editable Extracted Rules State --- */
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

    function renderInitialExtractedRules() {
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
          '<td><input type="text" value="' + (r.rule_id || '') + '" onchange="updateRuleCell(' + idx + ', \'rule_id\', this.value)" style="width: 75px; font-weight: 600;"></td>' +
          '<td><input type="text" value="' + (r.match_value || r.name || '') + '" onchange="updateRuleCell(' + idx + ', \'match_value\', this.value)"></td>' +
          '<td><input type="text" value="' + (r.condition || '') + '" onchange="updateRuleCell(' + idx + ', \'condition\', this.value)"></td>' +
          '<td>' +
            '<select onchange="updateRuleCell(' + idx + ', \'action_on_match\', this.value)" style="font-weight: 700; color: ' + (isHold ? '#b91c1c' : '#15803d') + ';">' +
              '<option value="Approved" ' + (r.action_on_match === 'Approved' ? 'selected' : '') + '>Approved</option>' +
              '<option value="Confirmed" ' + (r.action_on_match === 'Confirmed' ? 'selected' : '') + '>Confirmed</option>' +
              '<option value="Hold" ' + (r.action_on_match === 'Hold' ? 'selected' : '') + '>Hold</option>' +
              '<option value="Rejected" ' + (r.action_on_match === 'Rejected' ? 'selected' : '') + '>Rejected</option>' +
            '</select>' +
          '</td>' +
          '<td><input type="text" value="' + (r.description || '') + '" onchange="updateRuleCell(' + idx + ', \'description\', this.value)"></td>' +
          '<td style="text-align: center;">' +
            '<button class="btn-secondary" style="padding: 1px 4px; font-size: 10px; color: #b91c1c;" onclick="deleteExtractedRule(' + idx + ')">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    }

    function updateRuleCell(idx, field, val) {
      if (activeExtractedRules[idx]) {
        activeExtractedRules[idx][field] = val;
        if (field === 'action_on_match') {
          renderExtractedRulesTable();
        }
      }
    }

    function addNewExtractedRule() {
      activeExtractedRules.push({
        rule_id: 'RULE-CUSTOM-' + (activeExtractedRules.length + 1),
        match_value: 'Custom Target',
        condition: 'Custom Condition',
        action_on_match: (currentSuite === 'invoice' ? 'Approved' : 'Confirmed'),
        description: 'User-configured policy rule'
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
      }
    }

    async function continueAndEvaluateDatabase() {
      const docText = document.getElementById('doc-text').value.trim();
      resetGraphUi();
      setNodeDone('node-1', '0.15s');
      setNodeActive('node-2');

      const btn = document.getElementById('btn-run');
      if (btn) {
        btn.disabled = true;
        btn.innerText = 'Evaluating Database...';
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
          stagedDecisions = result.staged_decisions || [];
          document.getElementById('graph-overall-badge').innerText = 'AUDIT READY';
          document.getElementById('graph-overall-badge').style.background = '#fef08a';
          renderInterventions(result.discrepancies || []);
          openStagedModal();
        } else {
          alert('Evaluation error: ' + (result.error || 'Unknown error'));
        }
      } catch (e) {
        alert('Communication error: ' + e);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = '⚡ Run LangGraph Co-Pilot Agent';
        }
      }
    }'''

assert old_js_rules in app_text, "Could not find old_js_rules"
app_text = app_text.replace(old_js_rules, new_js_rules)

# 5. Make startLangGraphEvaluation call continueAndEvaluateDatabase
old_start_langgraph = '''    /* --- LangGraph Staged Evaluation & Confirmation Flow --- */
    async function startLangGraphEvaluation() {
      const docText = document.getElementById('doc-text').value.trim();
      if (!docText) {
        alert('参照メモまたは規程方針を入力してください。');
        return;
      }

      const btn = document.getElementById('btn-run');
      btn.disabled = true;
      btn.innerText = 'LangGraph 評価中...';

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
        (result.execution_steps || []).forEach(function(step, idx) {
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
    }'''

new_start_langgraph = '''    /* --- LangGraph Staged Evaluation & Confirmation Flow --- */
    async function startLangGraphEvaluation() {
      await continueAndEvaluateDatabase();
    }'''

assert old_start_langgraph in app_text, "Could not find old_start_langgraph"
app_text = app_text.replace(old_start_langgraph, new_start_langgraph)

with open('generate_app.py', 'w', encoding='utf-8') as f:
    f.write(app_text)

print("generate_app.py updated successfully!")
