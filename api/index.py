import sys
import os
from pathlib import Path

# Add project root and Task 3/code files to Python sys.path
_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir.parent
_task3_dir = _root_dir / "Task 3" / "code files"

for p in [str(_task3_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from unified_copilot_erp_app import app
