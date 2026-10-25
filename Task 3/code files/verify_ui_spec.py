import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

html = urllib.request.urlopen('http://127.0.0.1:5135/').read().decode('utf-8')

checks = [
    ('table.rules-table th sticky top: 0', 'top: 0;' in html and 'table.rules-table th' in html),
    ('No top: 34px in rules th', 'top: 34px;' not in html),
    ('Bulk Import button has no Excel icon', '一括取込 (Bulk Import)' in html and '📊 Excel一括取込' not in html),
    ('Workspace Tab 1 is 規程 (Regulations) with no 📋 icon', '規程 (Regulations)' in html and '📋 規程・メモ入力' not in html),
    ('Workspace Tab 2 is 規程マスタ (Regulation Master) with no 📊 icon', '規程マスタ (Regulation Master)' in html and '📊 規程マスタ (編集可能)' not in html),
    ('Rules container allows vertical scrolling of upper bars', 'id="llm-rules-content" style="padding: 8px 10px; flex: 1; min-height: 0; overflow-y: auto;' in html),
    ('Table wrapper not constrained by max-height 280px', 'max-height: 280px' not in html)
]

all_pass = True
for name, passed in checks:
    status = 'PASS' if passed else 'FAIL'
    if not passed:
        all_pass = False
    print(f'[{status}] {name}')

if all_pass:
    print('ALL UI SPEC CHECKS PASSED PERFECTLY!')
else:
    sys.exit(1)
