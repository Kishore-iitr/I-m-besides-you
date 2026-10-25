#!/usr/bin/env python3
"""
Master End-to-End Pipeline Runner: Task 1 + Task 2 Bridge & Puter Auth Bridge
=============================================================================
Orchestrates the complete intern assignment pipeline in a single unified command:
1. Runs Task 1: Desktop Process Execution Segmentation (raw events -> segments.jsonl)
2. Runs Task 2: Automation Candidate Profiling & ROI Ranking (segments.jsonl -> TOP_CANDIDATE_AUTOMATION_REPORT.md)
3. Supports single-session, full dataset, or standalone deep-dive analysis.
4. Integrated Puter Authentication: 1-click browser sign-in or direct token paste (no separate file needed).
"""

import argparse
import http.server
import json
import os
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHON_EXE = sys.executable
# Dynamically determine workspace root whether running from main/ or from root directory
_this_dir = Path(__file__).resolve().parent
if (_this_dir / 'Task 2').exists() or (_this_dir / 'Task 3').exists():
    WORKSPACE_ROOT = _this_dir
else:
    WORKSPACE_ROOT = _this_dir.parent
TASK1_DIR = WORKSPACE_ROOT / "Task 1"
if not TASK1_DIR.exists():
    TASK1_DIR = WORKSPACE_ROOT / "task one"
TASK2_DIR = WORKSPACE_ROOT / "Task 2"
TASK3_DIR = WORKSPACE_ROOT / "Task 3"
ENV_FILE = WORKSPACE_ROOT / ".env"
AUTH_PORT = 8765

AUTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Puter Authentication Bridge</title>
    <script src="https://js.puter.com/v2/"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #0f172a; color: #f8fafc; }
        .card { background-color: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 450px; width: 90%; border: 1px solid #334155; }
        h2 { margin-top: 0; color: #38bdf8; }
        p { color: #94a3b8; line-height: 1.5; font-size: 15px; }
        .btn { background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white; border: none; padding: 0.75rem 1.5rem; font-size: 16px; font-weight: 600; border-radius: 0.5rem; cursor: pointer; transition: transform 0.1s, opacity 0.2s; margin-top: 1rem; }
        .btn:hover { opacity: 0.95; transform: scale(1.02); }
        .status-box { margin-top: 1.5rem; padding: 0.75rem; border-radius: 0.5rem; background: #0f172a; font-size: 14px; border: 1px solid #334155; }
        .success { color: #4ade80; font-weight: bold; }
        .spinner { border: 3px solid rgba(255,255,255,0.1); width: 24px; height: 24px; border-radius: 50%; border-left-color: #38bdf8; animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 8px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <h2>Connect to Puter.com</h2>
        <p>Connecting your enterprise automation suite to Puter's AI services via secure authentication.</p>
        
        <div id="statusBox" class="status-box">
            <span class="spinner" id="spinner"></span>
            <span id="statusText">Initiating Puter sign-in...</span>
        </div>

        <button id="loginBtn" class="btn" style="display: none;" onclick="triggerLogin()">Open Sign-In Popup</button>
    </div>

    <script>
        async function triggerLogin() {
            document.getElementById('spinner').style.display = 'inline-block';
            document.getElementById('statusText').innerText = 'Please complete login in the Puter window...';
            try {
                await puter.auth.signIn();
                const token = puter.auth.getToken();
                if (!token) throw new Error("No token returned by Puter");
                
                document.getElementById('statusText').innerText = 'Authenticated! Transmitting token to Python...';
                
                const res = await fetch('/callback', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ token: token })
                });
                
                const data = await res.json();
                if (data.status === 'ok') {
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('statusBox').innerHTML = '<span class="success">✓ Successfully Connected!</span><br><br>Authentication received. You can now close this tab and return to your terminal.';
                } else {
                    throw new Error(data.message || 'Error writing credentials');
                }
            } catch (err) {
                console.error(err);
                document.getElementById('spinner').style.display = 'none';
                document.getElementById('statusText').innerText = 'Sign-in cancelled or failed: ' + err.message;
                document.getElementById('loginBtn').style.display = 'inline-block';
            }
        }

        window.addEventListener('load', () => {
            setTimeout(triggerLogin, 500);
        });
    </script>
</body>
</html>
"""


def test_puter_token(token: str) -> bool:
    """Verifies that the token can successfully query Puter API."""
    url = "https://api.puter.com/drivers/call"
    payload = {
        "interface": "puter-chat-completion",
        "driver": "ai-chat",
        "test_mode": False,
        "method": "complete",
        "args": {
            "messages": [{"role": "user", "content": "ping"}],
            "model": "gpt-4o-mini"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            return "result" in data
    except Exception as e:
        print(f"[Warning] Token verification check: {e}")
        return False


def save_token_to_env(token: str, env_file: Path):
    """Updates or appends PUTER_AUTH_TOKEN in .env."""
    lines = []
    found = False
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("PUTER_AUTH_TOKEN="):
                lines[i] = f"PUTER_AUTH_TOKEN={token}"
                found = True
                break
    if not found:
        lines.append(f"PUTER_AUTH_TOKEN={token}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Puter Auth Token successfully saved to: {env_file}")


class PuterAuthHandler(http.server.BaseHTTPRequestHandler):
    received_token = None
    shutdown_server = None

    def log_message(self, format, *args):
        return

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(AUTH_HTML.encode("utf-8"))

    def do_POST(self):
        if self.path == "/callback":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                token = data.get("token")
                if token:
                    PuterAuthHandler.received_token = token
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
                    threading.Thread(target=self.shutdown_server).start()
                    return
            except Exception:
                pass
        self.send_response(400)
        self.end_headers()


def launch_browser_login(env_path: Path):
    """Starts local HTTP server and opens browser for interactive Puter login."""
    server_address = ("127.0.0.1", AUTH_PORT)
    try:
        httpd = http.server.HTTPServer(server_address, PuterAuthHandler)
    except OSError:
        print(f"Error: Port {AUTH_PORT} is busy. If another instance is running, please close it.")
        return

    def shutdown():
        httpd.shutdown()

    PuterAuthHandler.shutdown_server = shutdown
    login_url = f"http://127.0.0.1:{AUTH_PORT}"
    
    print("\n" + "=" * 80)
    print("PUTER INTERACTIVE AUTHENTICATION BRIDGE")
    print("=" * 80)
    print(f"1. Opening browser to: {login_url}")
    print("2. Please click 'Sign in with Puter' in the popup window.")
    print("3. Waiting for authorization token...")
    print("=" * 80 + "\n")

    webbrowser.open(login_url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nLogin cancelled by user.")
        return

    if PuterAuthHandler.received_token:
        token = PuterAuthHandler.received_token
        print(f"\n[Received Token]: {token[:15]}...{token[-10:]}")
        print("Verifying token with Puter API...")
        if test_puter_token(token):
            print("✓ Token verified: connection successful!")
        else:
            print("! Token verification check returned a warning, but saving token.")
        save_token_to_env(token, env_path)
    else:
        print("No token was received.")


def run_command(cmd_args: list, cwd: Path, desc: str):
    print("\n" + "=" * 80)
    print(f"Executing: {desc}")
    print(f"Working Directory: {cwd}")
    print(f"Command: {' '.join(str(c) for c in cmd_args)}")
    print("=" * 80 + "\n")
    
    res = subprocess.run(cmd_args, cwd=str(cwd))
    if res.returncode != 0:
        print(f"\n[Error] Command failed with exit code {res.returncode}")
        sys.exit(res.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Master End-to-End Pipeline Runner for Task 1 and Task 2 with Integrated Puter Auth"
    )
    # Puter Authentication Flags
    parser.add_argument(
        "--login", "--login_browser",
        dest="login_browser",
        action="store_true",
        help="Connect to Puter via 1-click interactive browser login"
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Paste a Puter Auth Token directly to verify and save to .env"
    )
    parser.add_argument(
        "--check_auth",
        action="store_true",
        help="Check current Puter connection and token validity"
    )

    # Pipeline Flags
    parser.add_argument(
        "--dataset_dir",
        type=str,
        default=None,
        help="Path to full dataset folder (e.g. dataset_b or dataset_a)"
    )
    parser.add_argument(
        "--session_dir",
        type=str,
        default=None,
        help="Path to a single session folder"
    )
    parser.add_argument(
        "--skip_task1",
        action="store_true",
        help="Skip Task 1 execution and use existing segments.jsonl directly"
    )
    parser.add_argument(
        "--list_segments",
        action="store_true",
        help="List all segments available in Task 2"
    )
    parser.add_argument(
        "--segment_idx",
        type=int,
        default=None,
        help="Perform deep forensic analysis on a specific segment index [0..157]"
    )
    parser.add_argument(
        "--case_id",
        type=str,
        default=None,
        help="Perform deep forensic analysis on a specific Case ID"
    )
    parser.add_argument(
        "--filter_label",
        type=str,
        default=None,
        help="Filter listed segments by label substring (e.g. leave, onboarding, payroll)"
    )
    parser.add_argument(
        "--filter_session",
        type=str,
        default=None,
        help="Filter listed segments by session ID substring"
    )
    parser.add_argument(
        "--filter_case",
        type=str,
        default=None,
        help="Filter listed segments by case ID substring"
    )

    # Task 3 ERP Web Portal Flags
    parser.add_argument("--serve", action="store_true", help="Launch Task 3 Web Portal on port 5135")
    parser.add_argument("--port", type=int, default=5135, help="Port for Task 3 web server")
    parser.add_argument("--verify_task3", action="store_true", help="Run Task 3 system verification suite")
    parser.add_argument("--benchmark_task3", action="store_true", help="Run Task 3 live database benchmarks")
    args, extra_args = parser.parse_known_args()

    # Handle Puter Auth Operations directly
    if args.check_auth:
        current_token = os.environ.get("PUTER_AUTH_TOKEN")
        if not current_token and ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("PUTER_AUTH_TOKEN="):
                    current_token = line.split("=", 1)[1].strip()
                    break
        if current_token:
            print(f"Found Puter Token: {current_token[:15]}...{current_token[-10:]}")
            print("Testing connection to Puter API...")
            if test_puter_token(current_token):
                print("✓ Puter connection is ACTIVE and working!")
            else:
                print("✗ Puter connection failed. The token may be expired.")
        else:
            print("No Puter Token configured. Run with --login to authenticate.")
        return

    if args.token:
        token = args.token.strip()
        print("Testing provided token...")
        if test_puter_token(token):
            print("✓ Token verified successfully!")
        save_token_to_env(token, ENV_FILE)
        return

    if args.login_browser:
        launch_browser_login(ENV_FILE)
        return

    # If deep dive or listing is requested, delegate immediately to Task 2
    if args.list_segments or args.segment_idx is not None or args.case_id:
        cmd = [PYTHON_EXE, "run_task2.py"]
        if args.list_segments:
            cmd.append("--list_segments")
        if args.segment_idx is not None:
            cmd.extend(["--segment_idx", str(args.segment_idx)])
        if args.case_id:
            cmd.extend(["--case_id", str(args.case_id)])
        if args.filter_label:
            cmd.extend(["--filter_label", str(args.filter_label)])
        if args.filter_session:
            cmd.extend(["--filter_session", str(args.filter_session)])
        if args.filter_case:
            cmd.extend(["--filter_case", str(args.filter_case)])
        cmd.extend(extra_args)
        run_command(cmd, cwd=TASK2_DIR, desc="Task 2 Deep Dive / Segment Browser")
        return

    print("*" * 80)
    print("   MASTER EVALUATION PIPELINE: TASK 1 + TASK 2 BRIDGE   ")
    print("*" * 80)

    segments_output = TASK1_DIR / "results" / "segments.jsonl"

        # Task 3 Standalone Actions
    if args.serve:
        task3_runner = TASK3_DIR / 'run_task3.py'
        if not task3_runner.exists():
            task3_runner = TASK3_DIR / 'code files' / 'run_task3.py'
        print(f'Launching Task 3 Web Portal on port {args.port}...')
        cmd = [PYTHON_EXE, str(task3_runner), '--serve', '--port', str(args.port)]
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

    if args.verify_task3:
        task3_runner = TASK3_DIR / 'run_task3.py'
        if not task3_runner.exists():
            task3_runner = TASK3_DIR / 'code files' / 'run_task3.py'
        cmd = [PYTHON_EXE, str(task3_runner), '--verify']
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

    if args.benchmark_task3:
        task3_runner = TASK3_DIR / 'run_task3.py'
        if not task3_runner.exists():
            task3_runner = TASK3_DIR / 'code files' / 'run_task3.py'
        cmd = [PYTHON_EXE, str(task3_runner), '--benchmark']
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

    # Step 1: Run Task 1 (Process Execution Segmentation)
    if not args.skip_task1:
        task1_cmd = [PYTHON_EXE, "run_task1.py"]
        if args.session_dir:
            task1_cmd.extend(["--session_dir", args.session_dir])
            task1_cmd.extend(["--output", str(segments_output)])
        elif args.dataset_dir:
            task1_cmd.extend(["--dataset_dir", args.dataset_dir])
            task1_cmd.extend(["--output", str(segments_output)])
        else:
            print("No --dataset_dir or --session_dir specified.")
            print(f"Using pre-verified Task 1 deliverable at: {segments_output}")
            args.skip_task1 = True

        if not args.skip_task1:
            run_command(task1_cmd, cwd=TASK1_DIR, desc="Task 1: Process Execution Segmentation")

    # Step 2: Run Task 2 (Automation Candidate Profiling & Portfolio Scoring)
    task2_cmd = [
        PYTHON_EXE, "run_task2.py",
        "--segments", str(segments_output)
    ]
    if args.session_dir:
        task2_cmd.extend(["--session_dir", args.session_dir])

    run_command(task2_cmd, cwd=TASK2_DIR, desc="Task 2: Automation Candidate Profiling & Portfolio Scoring")

    print("\n" + "*" * 80)
    print("✓ Master Pipeline Finished Successfully!")
    print(f"  Task 1 Deliverable: {segments_output}")
    print(f"  Task 2 Report:      {TASK2_DIR / 'results' / 'TOP_CANDIDATE_AUTOMATION_REPORT.md'}")
    print(f"  Task 2 Rankings:    {TASK2_DIR / 'results' / 'candidate_portfolio_ranking.csv'}")
    print("*" * 80 + "\n")


if __name__ == "__main__":
    main()
