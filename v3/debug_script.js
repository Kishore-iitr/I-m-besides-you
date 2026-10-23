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

    const INVOICE_PRESET = `月次定額保守取引先契約一覧 (2026年度 財務会計部門)
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
- 区分が 'Adjustment' である伝票は、全件経理担当者による精査(Hold)を要する。`;
    const PAYROLL_PRESET = `精算確認メモ (2026年7月度 人事給与控除・経費整備)
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
- 人事給与マスタ未定義の手当コード（例: 未登録手当）は全件保留とする。`;

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

      const lines = text.split('
').filter(l => l.trim().length > 0);
      parsedBulkData = [];

      lines.forEach((line, idx) => {
        const parts = line.includes('	') ? line.split('	') : line.split(',');
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