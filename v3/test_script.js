
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
          if (newWidth < 300) newWidth = 300;
          if (newWidth > 850) newWidth = 850;
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
      let c = (r.condition || '').trim();
      if (!c || /^\d+$/.test(c)) {
        const num = c ? parseInt(c, 10) : (r.expected_amount || r.threshold_amount || 0);
        if (r.action_on_match === 'Hold' || r.action_on_match === 'Rejected') {
          c = 'Amount > ¥' + Number(num).toLocaleString() + ' (Ceiling Limit -> Hold)';
        } else {
          c = 'Category == \'Routine\' && Amount == ¥' + Number(num).toLocaleString() + ' (Fixed Rate)';
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
  