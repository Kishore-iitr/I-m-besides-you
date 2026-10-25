#!/usr/bin/env python3
"""
Task 3: Automated Enterprise Web ERP, Multi-Process Autonomous Decision Agent,
Office Ingestion & Cloud Persistence Orchestrator.

Step 3 of Intern Selection Challenge.

Usage:
  python run_task3.py                    # Run comprehensive system verification suite
  python run_task3.py --serve            # Launch the live ERP Web Portal + Co-Pilot on port 5135
  python run_task3.py --serve --port 5135 # Launch with custom port
  python run_task3.py --benchmark        # Run 30-rule policy benchmarks on live database
  python run_task3.py --verify-ui        # Run UI layout & scroll dynamic verification
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
CODE_DIR = CURRENT_DIR / "code files"
ROOT_DIR = CURRENT_DIR.parent

# Add directories to sys.path
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(ROOT_DIR))

def run_tests():
    """Runs the full system verification test suite."""
    print("=" * 80)
    print("  TASK 3: SYSTEM VERIFICATION & COMPREHENSIVE INTEGRATION SUITE")
    print("=" * 80)
    test_script = CODE_DIR / "test_all_features.py"
    if not test_script.exists():
        print(f"Error: Test script not found at {test_script}")
        return 1

    cmd = [sys.executable, str(test_script)]
    res = subprocess.run(cmd)
    return res.returncode

def run_ui_verify():
    """Runs the UI layout and responsive verification checks."""
    print("=" * 80)
    print("  TASK 3: UI SPEC & RESPONSIVE SCROLL DYNAMICS AUDIT")
    print("=" * 80)
    ui_script = CODE_DIR / "verify_ui_spec.py"
    if not ui_script.exists():
        print(f"Error: UI script not found at {ui_script}")
        return 1

    cmd = [sys.executable, str(ui_script)]
    res = subprocess.run(cmd)
    return res.returncode

def run_benchmark():
    """Runs the 30 policy-to-SQL dynamic benchmarks."""
    print("=" * 80)
    print("  TASK 3: 30-POLICY DYNAMIC COMPILATION BENCHMARK (LIVE DATABASE)")
    print("=" * 80)
    bench_script = CODE_DIR / "test_complete_dynamic_logic.py"
    if not bench_script.exists():
        print(f"Error: Benchmark script not found at {bench_script}")
        return 1

    cmd = [sys.executable, str(bench_script)]
    res = subprocess.run(cmd)
    return res.returncode

def start_server(port: int = 5135):
    """Launches the production Unified ERP web application with Co-Pilot."""
    print("=" * 80)
    print(f"  LAUNCHING UNIFIED ENTERPRISE ERP & CO-PILOT ON PORT {port}")
    print(f"  URL: http://127.0.0.1:{port}/")
    print("=" * 80)
    app_script = CODE_DIR / "unified_copilot_erp_app.py"
    if not app_script.exists():
        app_script = ROOT_DIR / "unified_copilot_erp_app.py"
    
    env = os.environ.copy()
    env["PORT"] = str(port)
    cmd = [sys.executable, str(app_script)]
    return subprocess.run(cmd, env=env).returncode

def main():
    parser = argparse.ArgumentParser(
        description="Task 3: Automated Enterprise Web ERP, Multi-Process Autonomous Decision Agent & Cloud Persistence"
    )
    parser.add_argument("--serve", action="store_true", help="Launch the Flask web application on port 5135")
    parser.add_argument("--port", type=int, default=5135, help="Port for web server (default: 5135)")
    parser.add_argument("--verify", action="store_true", help="Run 7/7 system integration test cases")
    parser.add_argument("--verify-ui", action="store_true", help="Run UI spec and scroll verification")
    parser.add_argument("--benchmark", action="store_true", help="Run 30-policy live database benchmarks")

    args = parser.parse_args()

    if args.serve:
        sys.exit(start_server(args.port))
    elif args.verify_ui:
        sys.exit(run_ui_verify())
    elif args.benchmark:
        sys.exit(run_benchmark())
    elif args.verify:
        sys.exit(run_tests())
    else:
        # Default action: run tests
        print("No specific mode specified. Running default comprehensive verification suite...")
        code = run_tests()
        if code == 0:
            print("\nVerification passed! To start the web portal, run: python run_task3.py --serve")
        sys.exit(code)

if __name__ == "__main__":
    main()
