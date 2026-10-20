import { Burst, GroundedBurst, Activity, TaskThreadRoot } from '../types.js';

export class DeterministicMockLlm {
  public groundBurst(burst: Burst): { semantic_action: string; ui_target: string; intent: string } {
    const app = burst.app_name.toLowerCase();
    const title = burst.clean_title;
    const text = burst.extracted_text || '';
    const caseId = burst.case_ids[0] || '';

    let semantic_action = '';
    let ui_target = '';
    let intent = '';

    if (title.includes('財務会計') || text.includes('財務会計') || caseId.startsWith('INV-')) {
      semantic_action = caseId ? `Process invoice for case ${caseId}` : `Review invoice batch in 財務会計システム`;
      ui_target = '財務会計システム (Invoice Management)';
      intent = 'Verify invoice amount, vendor details and approve payment';
    } else if (title.includes('受発注') || text.includes('受発注') || caseId.startsWith('ORD-') || caseId.startsWith('STK-')) {
      semantic_action = caseId ? `Update order / stock adjustment ${caseId}` : `Inspect inventory orders in 受発注在庫管理システム`;
      ui_target = '受発注在庫管理システム (Inventory & Orders)';
      intent = 'Check stock allocation and update order status';
    } else if (title.includes('人事') || text.includes('人事') || caseId.startsWith('LA-') || caseId.startsWith('OB-') || caseId.startsWith('SI-') || caseId.startsWith('RT-')) {
      semantic_action = caseId ? `Handle employee leave / onboarding case ${caseId}` : `Manage employee requests in HR人事給与システム`;
      ui_target = 'HR人事給与システム (HR & Payroll)';
      intent = 'Validate employee request against HR compliance policies';
    } else if (app.includes('excel')) {
      semantic_action = caseId ? `Cross-reference case ${caseId} against master lookup` : `Lookup reference records in Excel spreadsheet`;
      ui_target = 'm1_reference.xlsx';
      intent = 'Find master code and verify client/employee identity';
    } else if (app.includes('notepad')) {
      semantic_action = caseId ? `Record case processing notes for ${caseId}` : `Log workflow notes into Notepad document`;
      ui_target = 'Notepad scratchpad';
      intent = 'Keep audit log of case adjustments and comments';
    } else if (app.includes('powerpnt') || text.includes('Budget_Report')) {
      semantic_action = 'Review budget report variance in PowerPoint';
      ui_target = 'Budget_Report.pptx';
      intent = 'Analyze quarterly budget variances across departments';
    } else {
      semantic_action = `Perform administrative operations in ${burst.app_name}`;
      ui_target = burst.clean_title || burst.app_name;
      intent = 'General office paperwork processing';
    }

    return { semantic_action, ui_target, intent };
  }

  public induceActivities(bursts: GroundedBurst[]): Activity[] {
    const activities: Activity[] = [];
    if (bursts.length === 0) return [];

    let currentGroup: GroundedBurst[] = [];

    function flushActivity() {
      if (currentGroup.length === 0) return;
      const first = currentGroup[0];
      const last = currentGroup[currentGroup.length - 1];
      const activityId = `act_${first.session_id}_${activities.length + 1}`;

      const allCaseIds = Array.from(new Set(currentGroup.flatMap(b => b.case_ids))).sort();
      const allApps = Array.from(new Set(currentGroup.map(b => b.app_name))).sort();
      const summary = currentGroup.map(b => b.semantic_action).join('; ');

      // Determine provisional process label
      let label = 'general_backoffice';
      const caseId = allCaseIds[0] || '';
      if (caseId.startsWith('INV-') || summary.includes('invoice') || summary.includes('財務会計')) {
        label = 'invoice_approval';
      } else if (caseId.startsWith('STK-') || summary.includes('stock') || summary.includes('在庫')) {
        label = 'stock_adjustment';
      } else if (caseId.startsWith('ORD-') || summary.includes('order') || summary.includes('受発注')) {
        label = 'order_processing';
      } else if (caseId.startsWith('LA-') || summary.includes('leave') || summary.includes('育児')) {
        label = 'leave_application';
      } else if (caseId.startsWith('OB-') || summary.includes('onboarding') || summary.includes('入社')) {
        label = 'employee_onboarding';
      } else if (caseId.startsWith('BV-') || summary.includes('budget') || summary.includes('予算')) {
        label = 'budget_variance';
      } else if (caseId.startsWith('SI-') || summary.includes('社保') || summary.includes('年金')) {
        label = 'social_insurance';
      } else if (caseId.startsWith('PM-') || summary.includes('支払') || summary.includes('日立')) {
        label = 'payment_processing';
      }

      activities.push({
        activity_id: activityId,
        session_id: first.session_id,
        start_ms: first.start_ms,
        start_iso: first.start_iso,
        end_ms: last.end_ms,
        end_iso: last.end_iso,
        burst_ids: currentGroup.map(b => b.burst_id),
        semantic_action_ids: currentGroup.map(b => b.burst_id),
        summary,
        app_names: allApps,
        case_ids: allCaseIds,
        provisional_label: label,
      });

      currentGroup = [];
    }

    for (let i = 0; i < bursts.length; i++) {
      const b = bursts[i];
      if (currentGroup.length > 0) {
        const prev = currentGroup[currentGroup.length - 1];
        // Break activity if case_id changed or long pause or complete shift in task domain
        const caseChanged = b.case_ids.length > 0 && prev.case_ids.length > 0 && b.case_ids[0] !== prev.case_ids[0];
        const gap = b.start_ms - prev.end_ms;
        const isLongGap = gap > 10000;

        if (caseChanged || isLongGap) {
          flushActivity();
        }
      }
      currentGroup.push(b);
    }

    flushActivity();
    return activities;
  }

  public clusterTaskThreads(activities: Activity[]): { roots: TaskThreadRoot[]; assignments: Array<{ activity_id: string; canonical_root_id: string; canonical_root_label: string }> } {
    const rootsMap = new Map<string, TaskThreadRoot>();
    const assignments: Array<{ activity_id: string; canonical_root_id: string; canonical_root_label: string }> = [];

    for (const act of activities) {
      const label = act.provisional_label;
      const rootId = `root_${label}`;

      if (!rootsMap.has(rootId)) {
        rootsMap.set(rootId, {
          canonical_root_id: rootId,
          label,
          objective: `Execute recurring business process for ${label.replace(/_/g, ' ')}`,
          deliverable: `Validated business system records and completed approval notes for ${label}`,
          success_criteria: `All validation checks complete and submitted without errors`,
          summary: `Handles multiple case instances of ${label} using portal, Excel lookup, and Notepad`,
          family_anchors: [label],
          case_anchors: [],
          activity_ids: [],
          burst_ids: [],
          observed_apps: [],
          event_count: 0,
        });
      }

      const root = rootsMap.get(rootId)!;
      root.activity_ids.push(act.activity_id);
      root.burst_ids.push(...act.burst_ids);
      for (const app of act.app_names) {
        if (!root.observed_apps.includes(app)) root.observed_apps.push(app);
      }
      for (const c of act.case_ids) {
        if (!root.case_anchors.includes(c)) root.case_anchors.push(c);
      }

      assignments.push({
        activity_id: act.activity_id,
        canonical_root_id: rootId,
        canonical_root_label: label,
      });
    }

    return {
      roots: Array.from(rootsMap.values()),
      assignments,
    };
  }
}
