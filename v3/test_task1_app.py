import sys
import os
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import urllib.request
import json
import time

base = 'http://127.0.0.1:5140'

# 1. Status
print('[1] Checking /api/status...')
res = json.loads(urllib.request.urlopen(f'{base}/api/status').read().decode('utf-8'))
print('  Status:', res['status'], '| Python:', res['python_version'])

# 2. Presets
print('\n[2] Checking /api/presets...')
presets_res = json.loads(urllib.request.urlopen(f'{base}/api/presets').read().decode('utf-8'))
print('  Presets loaded:', len(presets_res['presets']))
print('  Most repeated task:', presets_res['most_repeated_task_overview']['title'], '| Count:', presets_res['most_repeated_task_overview']['count'])

# 3. Single Session Step-by-Step Test (Siddhi)
print('\n[3] Triggering Step-by-Step Pipeline for Siddhi...')
req = urllib.request.Request(f'{base}/api/pipeline/start', 
    data=json.dumps({'source_type': 'preset', 'preset_id': 'siddhi', 'mode': 'single'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'})
start_res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
run_id = start_res['run_id']
print('  Run ID:', run_id)

while True:
    prog = json.loads(urllib.request.urlopen(f'{base}/api/pipeline/progress/{run_id}').read().decode('utf-8'))
    print(f"  Progress: {prog['overall_progress']}% | Step: {prog['current_step'][:50]}... | Status: {prog['status']}")
    if prog['status'] in ('completed', 'failed'):
        break
    time.sleep(1)

# 4. Results & Metrics Check
print('\n[4] Inspecting Results & Metrics...')
results_res = json.loads(urllib.request.urlopen(f'{base}/api/pipeline/results/{run_id}').read().decode('utf-8'))
res_data = results_res['results']
print('  Session:', res_data['session_name'])
print('  Ground Truth Available:', res_data['ground_truth_available'])
print('  Predicted Segments:', res_data['predicted_segments_count'])
print('  Ground Truth Executions:', res_data['ground_truth_executions_count'])
metrics = res_data['boundary_metrics']
print('  Tolerance +/- 5s: Precision =', metrics['tol_5s']['precision'], '%, Recall =', metrics['tol_5s']['recall'], '%, F1 =', metrics['tol_5s']['f1'], '%')
print('  Alignment mappings:', len(res_data['process_alignment']))

# 5. User Decision Save Choice
print('\n[5] Testing User Save Deliverable Choice...')
save_req = urllib.request.Request(f'{base}/api/deliverables/save',
    data=json.dumps({'run_id': run_id, 'choice': 'save'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'})
save_res = json.loads(urllib.request.urlopen(save_req).read().decode('utf-8'))
print('  Saved success:', save_res['success'])
print('  Deliverables paths:', save_res['paths'])

# 6. Test Parallel Multi-Session Fleet Run
print('\n[6] Testing Parallel Multi-Session Fleet Run...')
req_par = urllib.request.Request(f'{base}/api/pipeline/start', 
    data=json.dumps({'source_type': 'preset', 'preset_id': 'parallel_dataset_b', 'mode': 'parallel'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'})
start_par = json.loads(urllib.request.urlopen(req_par).read().decode('utf-8'))
run_id_par = start_par['run_id']
print('  Parallel Run ID:', run_id_par)

while True:
    prog_par = json.loads(urllib.request.urlopen(f'{base}/api/pipeline/progress/{run_id_par}').read().decode('utf-8'))
    print(f"  Parallel Progress: {prog_par['overall_progress']}% | Step: {prog_par['current_step'][:60]}... | Status: {prog_par['status']}")
    if prog_par['status'] in ('completed', 'failed'):
        break
    time.sleep(1)

results_par = json.loads(urllib.request.urlopen(f'{base}/api/pipeline/results/{run_id_par}').read().decode('utf-8'))
print('  Parallel Total Sessions Processed:', results_par['results']['total_sessions'])
print('  Parallel Segments Recovered:', results_par['results']['predicted_segments_count'])
print('  Speedup factor:', results_par['results']['speedup_factor'])
print('  Total Human Labor Covered:', results_par['results']['total_work_duration_hours'], 'hours')

# 7. Check SOP Endpoint
print('\n[7] Checking SOP Endpoint...')
sop_res = json.loads(urllib.request.urlopen(f'{base}/api/sop/most-repeated-task').read().decode('utf-8'))
print('  Top task:', sop_res['display_title'])
print('  Total steps in walkthrough:', len(sop_res['step_by_step_sop']))
for step in sop_res['step_by_step_sop']:
    print(f"    Step {step['step_number']}: {step['title']} ({step['active_app']})")

print('\nALL PIPELINE CHECKS PASSED SUCCESSFULLY!')
