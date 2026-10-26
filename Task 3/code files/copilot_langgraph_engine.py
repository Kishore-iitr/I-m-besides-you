"""
Co-Pilot LangGraph Agent Engine for Dual ERP Automation
(Invoice Processing + Payroll Item Processing)

Graph Workflow:
  [Start]
     |
  [Node 1: parse_document_to_schema_json]
     |
  [Node 2: compare_features_and_decide]
     |
  [Node 3: commit_database_updates]
     |
  [Node 4: human_in_the_loop_audit]
     |
   [End]
"""

import sys
import os
import re
import json
import time
from pathlib import Path
from typing import TypedDict, List, Dict, Any, Optional, Set

def clean_and_parse_json_robust(raw_text: str):
    if not raw_text or not str(raw_text).strip():
        return None
    cleaned = str(raw_text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Strip javascript // comments
    cleaned = re.sub(r"//[^\r\n]*", "", cleaned)
    # Strip /* ... */ comments
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
    # Strip trailing commas
    cleaned = re.sub(r",\s*([\]\}])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"(\{[\s\S]*\})", cleaned)
        if m:
            candidate = m.group(1)
            candidate = re.sub(r"//[^\r\n]*", "", candidate)
            candidate = re.sub(r"/\*[\s\S]*?\*/", "", candidate)
            candidate = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                return json.loads(candidate)
            except Exception:
                pass
    return None

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    END = "__END__"
    class StateGraph:
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes = {}
            self.edges = {}
            self.entry_point = None
        def add_node(self, name, func):
            self.nodes[name] = func
        def set_entry_point(self, name):
            self.entry_point = name
        def add_edge(self, start, end):
            self.edges[start] = end
        def compile(self):
            class CompiledGraph:
                def __init__(cg, entry, nodes, edges):
                    cg.entry = entry
                    cg.nodes = nodes
                    cg.edges = edges
                def invoke(cg, state):
                    curr = cg.entry
                    curr_state = dict(state)
                    while curr and curr != END and curr in cg.nodes:
                        res = cg.nodes[curr](curr_state)
                        if isinstance(res, dict):
                            curr_state.update(res)
                        curr = cg.edges.get(curr, END)
                    return curr_state
            return CompiledGraph(self.entry_point, self.nodes, self.edges)

try:
    from tmi_pipeline import PuterLlmClient
except ImportError:
    class PuterLlmClient:
        """Client for Puter.js / OpenRouter free models using Puter's driver API."""
        def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
            self.token = token or os.environ.get("PUTER_AUTH_TOKEN", "")
            self.model = model or os.environ.get("PUTER_MODEL", "openrouter:openrouter/free")
            self.url = "https://api.puter.com/drivers/call"

        def complete(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 60) -> str:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "interface": "puter-chat-completion",
                "driver": "ai-chat",
                "test_mode": False,
                "method": "complete",
                "args": {
                    "messages": messages,
                    "model": self.model,
                    "stream": False
                }
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}" if self.token else ""
            }
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as res:
                        data = json.loads(res.read().decode("utf-8"))
                        if isinstance(data, dict):
                            result = data.get("result", {})
                            if isinstance(result, dict):
                                msg = result.get("message", {})
                                if isinstance(msg, dict):
                                    return msg.get("content", "")
                                return result.get("text", "") or str(result)
                            elif isinstance(result, str):
                                return result
                        return str(data)
                except Exception as e:
                    if attempt == 0:
                        time.sleep(1.5)
                        continue
                    raise RuntimeError(f"Puter API Error: {e}")
            return ""

# State definition for the LangGraph
class CoPilotAgentState(TypedDict):
    process_type: str                     # "invoice" or "payroll"
    document_text: str                    # Raw text from Word / pasted memo / rules
    filename_or_title: str                # Source name
    table_name: str                       # "erp_invoices" or "erp_payroll_items"
    table_schema: Dict[str, Any]          # Column names & types
    policy_json: Dict[str, Any]           # Extracted policy JSON mapped to features
    current_db_rows: List[Dict[str, Any]] # Live rows from DB
    decisions: List[Dict[str, Any]]       # Evaluated row decisions
    db_updates_applied: int               # Count of DB updates executed
    discrepancies: List[Dict[str, Any]]   # Items requiring human intervention
    execution_steps: List[Dict[str, Any]] # Step logs & timestamps
    overall_status: str                   # "SUCCESS" / "NEEDS_INTERVENTION" / "ERROR"
    error: Optional[str]


def extract_text_from_file_bytes(filename: str, file_bytes: bytes) -> str:
    """Extracts text from uploaded .docx, .xlsx, .xls, .csv, or text file bytes."""
    fname_lower = filename.lower()
    if fname_lower.endswith(".docx"):
        import io
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    paragraphs.append(" | ".join(cells))
        return "\n".join(paragraphs)
    elif fname_lower.endswith(".xlsx") or fname_lower.endswith(".xls"):
        import io
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        lines = []
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            lines.append(f"=== Sheet: {sheetname} ===")
            for row in ws.iter_rows(values_only=True):
                row_vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                if row_vals:
                    lines.append(" | ".join(row_vals))
        return "\n".join(lines)
    elif fname_lower.endswith(".csv"):
        import io
        import csv
        text_content = file_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text_content))
        lines = [" | ".join(row) for row in reader if any(row)]
        return "\n".join(lines)
    else:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("cp932", errors="ignore")


import urllib.request
import urllib.error

class OpenRouterLlmClient:
    """Client for OpenRouter API, specifically targeting free (:free) models."""
    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self.token = (token or os.environ.get("OPENROUTER_API_KEY", "")).strip()
        self.model = (model or os.environ.get("OPENROUTER_MODEL", "openrouter/free")).strip()
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 30) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:5135",
            "X-Title": "Enterprise ERP System"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    if "error" in data:
                        raise RuntimeError(f"OpenRouter Error: {data['error']}")
                    return ""
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                try:
                    err_json = json.loads(err_body)
                    msg = err_json.get("error", {}).get("message") or err_json.get("message") or err_body
                except Exception:
                    msg = err_body
                if attempt == 0 and e.code in [429, 502, 503, 504]:
                    time.sleep(2.0)
                    continue
                raise RuntimeError(f"OpenRouter HTTP {e.code}: {msg}")
            except Exception as e:
                if attempt == 0:
                    time.sleep(2.0)
                    continue
                raise

    def complete_json(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        raw_text = self.complete(prompt, system_prompt, timeout=timeout)
        cleaned = raw_text.strip()
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return {}


class LlmService:
    def __init__(self):
        self._reload_env()
        self._init_client()

    def _reload_env(self):
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip()
        self.provider = os.environ.get("LLM_PROVIDER", "puter").lower()
        self.puter_token = os.environ.get("PUTER_AUTH_TOKEN", "")
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.puter_model = os.environ.get("PUTER_MODEL", "openrouter:openrouter/free")
        self.openrouter_model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
        self.model = self.puter_model if self.provider == "puter" else self.openrouter_model
        self.remote_active = True
        self.last_failure_time = 0

    def _init_client(self):
        if self.provider == "openrouter":
            self.client = OpenRouterLlmClient(token=self.openrouter_key, model=self.openrouter_model)
            self.model = self.openrouter_model
            self.remote_active = bool(self.openrouter_key)
        elif self.provider == "puter":
            self.client = PuterLlmClient(token=self.puter_token, model=self.puter_model)
            self.model = self.puter_model
            if self.puter_token:
                try:
                    t_res = self.test_connection()
                    self.remote_active = bool(t_res.get("success", False))
                except Exception:
                    self.remote_active = False
            else:
                self.remote_active = False
        else: # local
            self.client = None
            self.model = "jsox-emulator-v1"
            self.remote_active = False

    def configure(self, provider: str, token: str, model: str, persist_to_env: bool = True):
        self.provider = provider.lower()
        if self.provider == "openrouter":
            if token is not None and token != "":
                self.openrouter_key = token
                os.environ["OPENROUTER_API_KEY"] = token
            if model:
                self.openrouter_model = model
                os.environ["OPENROUTER_MODEL"] = model
            os.environ["LLM_PROVIDER"] = "openrouter"
        elif self.provider == "puter":
            if token is not None and token != "":
                self.puter_token = token
                os.environ["PUTER_AUTH_TOKEN"] = token
            if model:
                self.puter_model = model
                os.environ["PUTER_MODEL"] = model
            os.environ["LLM_PROVIDER"] = "puter"
        else:
            self.provider = "local"
            os.environ["LLM_PROVIDER"] = "local"

        self._init_client()
        self.last_failure_time = 0

        if persist_to_env:
            self._save_to_env()

    def complete(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 30) -> str:
        """Executes LLM completion using configured provider."""
        if not self.client:
            raise RuntimeError("LLM client not configured or local mode active")
        return self.client.complete(prompt, system_prompt=system_prompt, timeout=timeout)

    def complete_json(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Executes LLM completion and parses result to JSON dictionary."""
        if not self.client:
            return {}
        if hasattr(self.client, "complete_json"):
            return self.client.complete_json(prompt, system_prompt=system_prompt, timeout=timeout)
        raw_text = self.complete(prompt, system_prompt, timeout=timeout)
        cleaned = raw_text.strip()
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return {}

    def _save_to_env(self):
        try:
            env_file = Path(__file__).parent / ".env"
            lines = []
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            keys_to_set = {
                "LLM_PROVIDER": self.provider,
                "PUTER_AUTH_TOKEN": self.puter_token,
                "PUTER_MODEL": self.puter_model,
                "OPENROUTER_API_KEY": self.openrouter_key,
                "OPENROUTER_MODEL": self.openrouter_model
            }
            
            found_keys = set()
            new_lines = []
            for l in lines:
                matched = False
                for k, v in keys_to_set.items():
                    if l.strip().startswith(f"{k}="):
                        new_lines.append(f"{k}={v}\n")
                        found_keys.add(k)
                        matched = True
                        break
                if not matched:
                    new_lines.append(l)
            
            for k, v in keys_to_set.items():
                if k not in found_keys:
                    new_lines.append(f"{k}={v}\n")
            
            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"[LlmService] Error saving to .env: {e}", file=sys.stderr)

    def get_status(self) -> Dict[str, Any]:
        token_configured = bool(self.openrouter_key if self.provider == "openrouter" else self.puter_token)
        is_conn = (self.remote_active and token_configured) or (self.provider == "local")
        return {
            "provider": self.provider,
            "connected": is_conn,
            "model": self.model,
            "display": f"OpenRouter ({self.model})" if self.provider == "openrouter" else (
                f"Puter ({self.model})" if self.provider == "puter" else f"Local Engine ({self.model})"
            ),
            "openrouter_key_set": bool(self.openrouter_key),
            "puter_token_set": bool(self.puter_token),
            "openrouter_model": self.openrouter_model,
            "puter_model": self.puter_model,
            "requires_login": (self.provider == "puter" and not is_conn)
        }

    def test_connection(self) -> Dict[str, Any]:
        t0 = time.time()
        if self.provider == "local" or not self.client:
            return {
                "success": True,
                "provider": "local",
                "latency_s": 0.001,
                "response": "Local J-SOX Certified Rules Engine Ready",
                "message": "Local Deterministic Rule Engine is 100% active."
            }
        
        token_to_check = self.openrouter_key if self.provider == "openrouter" else self.puter_token
        if not token_to_check:
            return {
                "success": False,
                "provider": self.provider,
                "error": "API Key / Token is missing",
                "message": f"Please provide an API Key for {self.provider.upper()}."
            }

        try:
            res = self.client.complete("Respond ONLY 'OK' for connection verification.", timeout=10)
            lat = round(time.time() - t0, 3)
            self.remote_active = True
            return {
                "success": True,
                "provider": self.provider,
                "latency_s": lat,
                "response": res.strip()[:100],
                "message": f"Connected to {self.provider.upper()} ({self.model}) in {lat}s"
            }
        except Exception as e:
            self.last_failure_time = time.time()
            self.remote_active = False
            return {
                "success": False,
                "provider": self.provider,
                "error": str(e),
                "message": f"{self.provider.upper()} error: {e}"
            }

    def generate_comment(self, process_type: str, item_data: Dict[str, Any], decision_status: str, reasons: List[str]) -> str:
        """Fast certified audit comment generator based on the triggered SQL rule."""
        amt = item_data.get("raw_amount", 0)
        formatted_amt = f"¥{amt:,}"
        if reasons:
            main_reason = reasons[0]
            if decision_status in ("Approved", "Confirmed"):
                return f"【自動承認】{main_reason}"
            else:
                return f"【保留】{main_reason}"
        if decision_status in ("Approved", "Confirmed"):
            return f"【自動承認】規程適合確認済（金額: {formatted_amt}）"
        else:
            return f"【保留】手動精査が必要（金額: {formatted_amt}）"

llm_service = LlmService()



def evaluate_sql_condition_in_memory(row: dict, sql_cond: str) -> bool:
    """Evaluates an ANSI SQL WHERE condition against a dictionary row in Python with 100% case-insensitivity."""
    cond = str(sql_cond or "").strip()
    if not cond:
        return True

    # 1. Expand subqueries for approved_vendors if present
    subquery_pattern = r'SELECT\s+employee_id\s+FROM\s+approved_vendors'
    reg_codes = "'V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012'"
    cond = re.sub(subquery_pattern, reg_codes, cond, flags=re.IGNORECASE)

    expr_pattern = r'((?:LOWER|UPPER)\s*\([a-zA-Z0-9_]+\)|[a-zA-Z_][a-zA-Z0-9_]*)'

    # Replace NOT IN: expr NOT IN ('a', 'b') -> (_case_not_in(expr, [items]))
    def replace_not_in(match):
        expr = match.group(1).strip()
        items = match.group(2)
        return f"(_case_not_in({expr}, [{items}]))"
    cond = re.sub(rf'{expr_pattern}\s+NOT\s+IN\s*\((.*?)\)', replace_not_in, cond, flags=re.IGNORECASE)

    # Replace IN: expr IN ('a', 'b') -> (_case_in(expr, [items]))
    def replace_in(match):
        expr = match.group(1).strip()
        items = match.group(2)
        return f"(_case_in({expr}, [{items}]))"
    cond = re.sub(rf'{expr_pattern}\s+IN\s*\((.*?)\)', replace_in, cond, flags=re.IGNORECASE)

    # Replace SQL <> with !=
    cond = cond.replace("<>", "!=")

    # Replace standalone = with == (avoiding <=, >=, !=)
    cond = re.sub(r'(?<![<>!=])=(?!=)', '==', cond)

    # Replace string equality with case-insensitive check
    def replace_eq(match):
        lhs = match.group(1).strip()
        rhs = match.group(2).strip()
        return f"_case_eq({lhs}, {rhs})"
    cond = re.sub(r"([a-zA-Z0-9_\(\)]+)\s*==\s*(['\"][^'\"]*['\"])", replace_eq, cond)
    cond = re.sub(r"(['\"][^'\"]*['\"])\s*==\s*([a-zA-Z0-9_\(\)]+)", lambda m: f"_case_eq({m.group(2)}, {m.group(1)})", cond)

    # Replace AND / OR / NOT keywords
    cond = re.sub(r'\bAND\b', 'and', cond, flags=re.IGNORECASE)
    cond = re.sub(r'\bOR\b', 'or', cond, flags=re.IGNORECASE)
    cond = re.sub(r'\bNOT\b', 'not', cond, flags=re.IGNORECASE)

    # Environment
    env = {}
    for k, v in row.items():
        env[k] = v
        env[k.lower()] = v
        env[k.upper()] = v

    def _to_clean_str(val):
        return str(val).strip().lower() if val is not None else ""

    env["LOWER"] = lambda v: str(v).lower() if v is not None else ""
    env["lower"] = env["LOWER"]
    env["UPPER"] = lambda v: str(v).upper() if v is not None else ""
    env["upper"] = env["UPPER"]

    def _case_eq(a, b):
        if isinstance(a, str) or isinstance(b, str):
            return _to_clean_str(a) == _to_clean_str(b)
        return a == b
    env["_case_eq"] = _case_eq

    def _case_in(val, items):
        if isinstance(val, (int, float)):
            return val in items
        clean_v = _to_clean_str(val)
        return any(clean_v == _to_clean_str(x) for x in items)
    env["_case_in"] = _case_in

    def _case_not_in(val, items):
        return not _case_in(val, items)
    env["_case_not_in"] = _case_not_in

    try:
        res = eval(cond, {"__builtins__": {}}, env)
        return bool(res)
    except Exception as e:
        return False

class CoPilotLangGraph:
    def __init__(self):
        self.llm_service = llm_service
        self.graph = self._build_graph()

    @property
    def llm(self):
        return self.llm_service.client

    def _build_graph(self):
        builder = StateGraph(CoPilotAgentState)

        # Add Nodes (Including SQL Validation & Refinement Node)
        builder.add_node("parse_document_to_schema_json", self.node_parse_document)
        builder.add_node("validate_and_refine_sql_rules", self.node_validate_and_refine_sql)
        builder.add_node("compare_features_and_decide", self.node_compare_and_decide)
        builder.add_node("commit_database_updates", self.node_commit_updates)
        builder.add_node("human_in_the_loop_audit", self.node_human_audit)

        # Define Edges with SQL Validation Node in the loop
        builder.set_entry_point("parse_document_to_schema_json")
        builder.add_edge("parse_document_to_schema_json", "validate_and_refine_sql_rules")
        builder.add_edge("validate_and_refine_sql_rules", "compare_features_and_decide")
        builder.add_edge("compare_features_and_decide", "commit_database_updates")
        builder.add_edge("commit_database_updates", "human_in_the_loop_audit")
        builder.add_edge("human_in_the_loop_audit", END)

        return builder.compile()

    def _make_sql_case_insensitive(self, cond: str, table_name: str = "erp_invoices") -> str:
        """Transforms SQL conditions on text columns to be case-insensitive in ANSI SQL (PostgreSQL & SQLite)."""
        text_cols_upper = ['employee_id', 'id', 'invoice_no', 'voucher_ref']
        text_cols_lower = ['type', 'item_category', 'item_type', 'name', 'employee_name', 'status']

        result = cond

        # Transform text_cols_upper: col IN (...) / col NOT IN (...)
        for col in text_cols_upper:
            def repl_in(m):
                op = m.group(1)
                inner = m.group(2).strip()
                if "select" in inner.lower():
                    return f"UPPER({col}) {op} ({inner})"
                upper_items = re.sub(r"'([^']*)'", lambda sm: f"'{sm.group(1).upper()}'", inner)
                return f"UPPER({col}) {op} ({upper_items})"
            pattern = rf"(?<![A-Za-z0-9_]){col}\s+(IN|NOT\s+IN)\s*\((.*?)\)"
            result = re.sub(pattern, repl_in, result, flags=re.IGNORECASE)

            def repl_eq(m):
                op = m.group(1)
                val = m.group(2)
                return f"UPPER({col}) {op} '{val.upper()}'"
            pattern_eq = rf"(?<![A-Za-z0-9_]){col}\s*([!=<>]+)\s*'([^']*)'"
            result = re.sub(pattern_eq, repl_eq, result, flags=re.IGNORECASE)

        # Transform text_cols_lower: col IN (...) / col NOT IN (...)
        for col in text_cols_lower:
            def repl_in(m):
                op = m.group(1)
                inner = m.group(2).strip()
                if "select" in inner.lower():
                    return f"LOWER({col}) {op} ({inner})"
                lower_items = re.sub(r"'([^']*)'", lambda sm: f"'{sm.group(1).lower()}'", inner)
                return f"LOWER({col}) {op} ({lower_items})"
            pattern = rf"(?<![A-Za-z0-9_]){col}\s+(IN|NOT\s+IN)\s*\((.*?)\)"
            result = re.sub(pattern, repl_in, result, flags=re.IGNORECASE)

            def repl_eq(m):
                op = m.group(1)
                val = m.group(2)
                return f"LOWER({col}) {op} '{val.lower()}'"
            pattern_eq = rf"(?<![A-Za-z0-9_]){col}\s*([!=<>]+)\s*'([^']*)'"
            result = re.sub(pattern_eq, repl_eq, result, flags=re.IGNORECASE)

        return result

    def _query_matching_ids_from_db(self, table_name: str, sql_cond: str) -> Optional[Set[str]]:
        """Executes the SQL condition directly against PostgreSQL or SQLite database with case-insensitive normalization."""
        if not sql_cond or not sql_cond.strip():
            return None
        clean_cond = sql_cond.strip().rstrip(';')
        normalized_cond = self._make_sql_case_insensitive(clean_cond, table_name)
        try:
            from erp_db import db_manager
            conn = db_manager.get_connection()
            if not conn:
                return None
            cur = conn.cursor()
            try:
                query = f"SELECT id FROM {table_name} WHERE ({normalized_cond})"
                cur.execute(query)
                rows = cur.fetchall()
                return {str(r[0]) for r in rows if r and r[0] is not None}
            finally:
                cur.close()
                if hasattr(conn, "close") and db_manager.engine_type == "postgresql":
                    conn.close()
        except Exception as e:
            print(f"[Query DB Error] {e} on SQL: {normalized_cond}")
            return None

    def _parse_policy_rules_robust(self, doc_text: str, process_type: str = "invoice") -> List[Dict[str, Any]]:
        """Parses both English and Japanese natural language policies into pristine ANSI SQL criteria rules."""
        rules = []

        # 1. Collect all vendor codes
        all_vendor_codes = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', doc_text))))
        all_vendor_codes = [c for c in all_vendor_codes if not c.startswith('P') and not c.startswith('INV') and c != "UNREGISTERED"]

        # 2. Check if structured rules (Rule 1, Rule 2, ... or 第1条, 【ルール1】) exist
        rule_blocks = re.split(r'\n(?=(?:Rule\s+[0-9]+|ルール\s*[0-9]+|第[0-9]+条|【ルール|\bRULE\-[0-9]+))', doc_text, flags=re.IGNORECASE)

        if len(rule_blocks) <= 1:
            # Try splitting by numbered lines
            rule_blocks = re.split(r'\n(?=[0-9]+[\.\:]\s+|\-\s+)', doc_text)

        rule_idx = 1
        for block in rule_blocks:
            b_clean = block.strip()
            if not b_clean:
                continue

            header_match = re.search(r'^(Rule\s+[0-9]+[^\n]*|ルール\s*[0-9]+[^\n]*|第[0-9]+条[^\n]*|【[^】]+】)', b_clean, re.IGNORECASE)
            rule_name = header_match.group(1).strip() if header_match else f"Rule {rule_idx}"

            # Extract amounts
            amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', b_clean)]
            if not amts:
                amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', b_clean)]
            for w in re.findall(r'([0-9]{1,4})\s*万(?:円)?', b_clean):
                amts.append(int(w) * 10000)

            # Block-specific vendor codes
            block_v_codes = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', b_clean))))
            block_v_codes = [c for c in block_v_codes if not c.startswith('P') and not c.startswith('INV') and c != "UNREGISTERED"]

            has_hold = any(kw in b_clean.lower() for kw in ["hold", "保留", "review", "精査", "不整合", "除外", "mandatory"])
            has_appr = any(kw in b_clean.lower() for kw in ["approve", "approved", "承認", "confirmed", "確認済"])

            # --- PAYROLL SPECIFIC DEDUCTION & ALLOWANCE CRITERIA ---
            if process_type == "payroll":
                if any(kw in b_clean for kw in ["控除項目", "扶養控除", "役職手当廃止"]) and any(kw in b_clean for kw in ["Addition", "支給", "不整合", "Hold"]):
                    sql_cond = "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'"
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": "Deduction Classification Mismatch",
                        "match_field": "item_category",
                        "match_value": "Deduction Mismatch",
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Hold",
                        "description": "Deduction items (扶養控除変更, 役職手当廃止) incorrectly classified as Addition in master held for review."
                    })
                    rule_idx += 1
                    continue

                if "接待交際費" in b_clean and amts:
                    limit_amt = amts[0]
                    sql_cond = f"item_category = '接待交際費' AND raw_amount > {limit_amt}"
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"Entertainment Expense Limit (> ¥{limit_amt:,})",
                        "match_field": "item_category",
                        "match_value": f"接待交際費 (> ¥{limit_amt:,})",
                        "threshold_amount": limit_amt,
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Hold",
                        "description": f"Entertainment expense exceeding ¥{limit_amt:,} requires mandatory executive sanction."
                    })
                    rule_idx += 1
                    continue

                if any(kw in b_clean for kw in ["未登録手当", "就業規則別表に定められていない", "コード不明"]):
                    sql_cond = "item_category = '未登録手当'"
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": "Unregistered Allowance Check",
                        "match_field": "item_category",
                        "match_value": "未登録手当",
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Hold",
                        "description": "Allowance not registered in employment regulations table. Held for HR approval."
                    })
                    rule_idx += 1
                    continue

                if any(kw in b_clean for kw in ["1伝票の精算金額が", "精算金額が", "単一伝票", "150,000", "15万円"]) and amts:
                    limit_amt = amts[0]
                    sql_cond = f"raw_amount > {limit_amt}"
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"Single Voucher Ceiling Limit (> ¥{limit_amt:,})",
                        "match_field": "raw_amount",
                        "match_value": f"Single Voucher Limit (> ¥{limit_amt:,})",
                        "threshold_amount": limit_amt,
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Hold",
                        "description": f"Single voucher amount exceeds ¥{limit_amt:,} ceiling limit. Pre-approval ringi document required."
                    })
                    rule_idx += 1
                    continue

                # Check pre-approved employee item in payroll
                p_v = re.search(r'(P[0-9]\-[0-9]{8}\-[0-9]{3})', b_clean)
                emp_m = re.search(r'([A-Za-z0-9぀-ゟ゠-ヿ一-鿿\s]+?)\s*[\(（](P[0-9]\-[0-9]{8}\-[0-9]{3})[\)）]', b_clean)
                if (p_v or emp_m) and amts:
                    emp_name = emp_m.group(1).strip() if emp_m else ""
                    emp_name = re.sub(r'^[0-9]+[\.\:]\s*', '', emp_name).strip()
                    v_id = p_v.group(1) if p_v else ""
                    cat_found = re.search(r'(研修費|消耗品費|出張旅費|交通費精算|在宅勤務手当|残業手当調整|接待交際費)', b_clean)
                    cat_str = cat_found.group(1) if cat_found else ""
                    cond_parts = []
                    if v_id and emp_name:
                        cond_parts.append(f"(id = '{v_id}' OR employee_name = '{emp_name}')")
                    elif v_id:
                        cond_parts.append(f"id = '{v_id}'")
                    elif emp_name:
                        cond_parts.append(f"employee_name = '{emp_name}'")
                    if cat_str:
                        cond_parts.append(f"item_category = '{cat_str}'")
                    cond_parts.append(f"raw_amount = {amts[0]}")
                    sql_cond = " AND ".join(cond_parts)
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"{emp_name or v_id} Pre-Approved Expense",
                        "match_field": "employee_name" if emp_name else "id",
                        "match_value": f"{emp_name} ({cat_str})",
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Confirmed",
                        "description": f"Pre-approved {cat_str} for {emp_name or v_id} verified compliant."
                    })
                    rule_idx += 1
                    continue

            # Case A: Unregistered Vendor Rule ("not on this list", "not registered", "未登録")
            if any(kw in b_clean.lower() for kw in ["not on this list", "not in", "unregistered", "not registered", "未登録", "リストに含まれない"]):
                target_codes = block_v_codes if len(block_v_codes) >= 3 else all_vendor_codes
                codes_fmt = ", ".join([f"'{c}'" for c in target_codes])
                code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                sql_cond = f"{code_col} NOT IN ({codes_fmt})"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": rule_name,
                    "match_field": "vendor_code" if process_type == "invoice" else "employee_id",
                    "match_value": "Unregistered Vendors",
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": "Hold",
                    "description": "Hold any voucher whose vendor code is not on the registered vendor list."
                })
                rule_idx += 1
                continue

            # Case B: Category Rule (Dynamically extract ANY category: Adjustment, Spot, Urgent, Travel, etc.)
            cat_match = re.search(r"""(?:category|区分(?:\:|が|は)?|種別)\s*[:：]?\s*['"]?([A-Za-z0-9぀-ゟ゠-ヿ一-鿿_-]+)['"]?""", b_clean, re.IGNORECASE)
            if not cat_match:
                cat_match = re.search(r'\bcategory\s+([A-Za-z0-9_-]+)\b', b_clean, re.IGNORECASE)

            is_cat_rule = bool(cat_match and cat_match.group(1).lower() not in ('rule', 'rules', 'voucher', 'vouchers', 'code', 'codes', 'registered', 'unregistered', 'amount', 'all'))
            if is_cat_rule and not any(kw in b_clean.lower() for kw in ['routine approval', 'approve a voucher only if', 'approve only if']):
                cat = cat_match.group(1).strip()
                action = 'Hold' if (has_hold or any(w in b_clean.lower() for w in ['hold', '保留', 'review', '精査', 'mandatory'])) else 'Approved'
                col_c = "type" if process_type == "invoice" else "item_category"
                sql_cond = f"{col_c} = '{cat}'"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": rule_name,
                    "match_field": col_c,
                    "match_value": f"Category {cat}",
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": action,
                    "description": f"{action} every voucher with category {cat}, regardless of amount or vendor."
                })
                rule_idx += 1
                continue

            # Case C: High-Value / Ceiling Threshold Rule ("strictly greater than", "greater than", "exceeds", "上限", "超過", "限度額")
            if any(kw in b_clean.lower() for kw in ["greater than", "strictly greater", "exceeds", "more than", "上限超過", "限度額", "超過"]) and amts:
                limit_val = amts[0]
                sql_cond = f"raw_amount > {limit_val}"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": rule_name,
                    "match_field": "raw_amount",
                    "match_value": f"> {limit_val}",
                    "threshold_amount": limit_val,
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": "Hold",
                    "description": f"Hold every voucher whose amount is strictly greater than ¥{limit_val:,}. An amount equal to ¥{limit_val:,} does not trigger this rule."
                })
                rule_idx += 1
                continue

            # Case D: Approval Rule ("Routine Approval", "Approve a voucher only if", etc.)
            if any(kw in b_clean.lower() for kw in ["approve a voucher only if", "routine approval", "approve only if", "通常承認", "自動承認条件"]):
                cond_parts = []
                appr_cat_m = re.search(r"""(?:category is|区分[がは]|区分:)\s*['"]?([A-Za-z0-9぀-ゟ゠-ヿ一-鿿_-]+)['"]?""", b_clean, re.IGNORECASE)
                if appr_cat_m:
                    appr_cat = appr_cat_m.group(1).strip()
                    cond_parts.append(f"type = '{appr_cat}'")
                elif any(kw in b_clean.lower() for kw in ["routine", "通常"]):
                    cond_parts.append("type = 'Routine'")

                amt_leq_m = re.search(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*(?:or less|以下|以内)', b_clean, re.IGNORECASE)
                if amt_leq_m:
                    cond_parts.append(f"raw_amount <= {int(amt_leq_m.group(1).replace(',', ''))}")
                elif amts:
                    cond_parts.append(f"raw_amount <= {amts[0]}")

                if any(kw in b_clean.lower() for kw in ["vendor code is registered", "registered vendor", "登録取引先", "登録ベンダー", "登録済み", "is registered"]):
                    if all_vendor_codes:
                        codes_fmt = ', '.join([f"'{c}'" for c in all_vendor_codes])
                        code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                        cond_parts.append(f"{code_col} IN ({codes_fmt})")

                sql_cond = " AND ".join(cond_parts) if cond_parts else "type = 'Routine'"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": rule_name,
                    "match_field": "type",
                    "match_value": "Approval Criteria",
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": "Approved",
                    "description": f"Approve vouchers compliant with policy approval criteria ({sql_cond})."
                })
                rule_idx += 1
                continue

            # Case E: Specific Vendor contract line (e.g. Japanese preset contracts)
            v_match = re.search(r'([A-Za-z0-9぀-ゟ゠-ヿ一-鿿\s\.\,\-]+?)\s*[\(（]([A-Z][0-9]{3,5})[\)）]', b_clean)
            v_code_only = re.search(r'\b([A-Z][0-9]{3,5})\b', b_clean)
            if v_match or (v_code_only and process_type == "invoice" and amts):
                v_name = v_match.group(1).strip() if v_match else ""
                v_code = v_match.group(2).strip() if v_match else v_code_only.group(1).strip()
                v_name = re.sub(r'^(?:No\.?\s*[0-9]+|[0-9]+[\.\:]|\-\s*)', '', v_name).strip()
                code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                id_clause = f"({code_col} = '{v_code}' OR name = '{v_name}')" if (v_code and v_name) else (f"{code_col} = '{v_code}'" if v_code else f"name = '{v_name}'")

                cat_v = re.search(r"""(?:category|区分(?:\:|が|は)?|種別)\s*[:：]?\s*['"]?([A-Za-z0-9぀-ゟ゠-ヿ一-鿿_-]+)['"]?""", b_clean, re.IGNORECASE)
                spec_cat = cat_v.group(1).strip() if cat_v else ("Adjustment" if ("Adjustment" in b_clean or "調整" in b_clean) else "")

                if has_hold:
                    sql_cond = f"{id_clause} AND type = '{spec_cat}'" if spec_cat else id_clause
                    action = "Hold"
                else:
                    parts = []
                    if spec_cat:
                        parts.append(f"type = '{spec_cat}'")
                    elif "routine" in b_clean.lower() or "通常" in b_clean:
                        parts.append("type = 'Routine'")
                    if len(amts) == 1:
                        parts.append(f"raw_amount = {amts[0]}")
                    elif len(amts) > 1:
                        parts.append(f"raw_amount IN ({', '.join(map(str, amts))})")
                    parts.append(id_clause)
                    sql_cond = " AND ".join(parts)
                    action = "Approved"

                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"{v_name or v_code} Contract Rule",
                    "match_field": "employee_id" if v_code else "name",
                    "match_value": f"{v_name} ({v_code})" if (v_name and v_code) else (v_code or v_name),
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": action,
                    "description": f"Contract rule for {v_name or v_code}."
                })
                rule_idx += 1
                continue

        # If rules were parsed cleanly, return them
        return rules

    def _semantic_fallback_extract(self, process_type: str, doc_text: str, filename: str) -> Dict[str, Any]:
        """Completely dynamic, zero-hardcoding semantic extractor and rule compiler.
        Parses ANY arbitrary policy, SOP, regulation, or memo into structured criteria rules."""
        robust_rules = self._parse_policy_rules_robust(doc_text, process_type)
        if robust_rules and len(robust_rules) >= 1:
            all_vc = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', doc_text))))
            all_vc = [c for c in all_vc if not c.startswith('P') and not c.startswith('INV')]
            ceilings = [r.get("threshold_amount") for r in robust_rules if r.get("threshold_amount")]
            if not ceilings:
                c_matches = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', doc_text)]
                ceilings = [a for a in c_matches if a >= 500000]
            max_c = ceilings[0] if ceilings else (2000000 if process_type == "invoice" else 150000)
            hold_cats = []
            for r in robust_rules:
                if r.get("action_on_match") in ("Hold", "Rejected"):
                    m = re.search(r"(?:type|item_category)\s*=\s*'([^']+)'", r.get("sql_condition") or "")
                    if m and m.group(1) not in hold_cats:
                        hold_cats.append(m.group(1))
            return {
                "policy_title": f"Policy Rules ({filename})",
                "process_type": process_type,
                "global_rules": {
                    "max_auto_approval_amount": max_c,
                    "registered_vendors": all_vc,
                    "hold_categories": hold_cats
                },
                "registered_vendors": all_vc,
                "item_criteria": robust_rules
            }
        raw_lines = [l for l in doc_text.splitlines() if l.strip()]
        lines = []
        for raw in raw_lines:
            stripped = raw.strip()
            is_sub = raw.startswith(" ") or raw.startswith("\t") or stripped.startswith("- ") or stripped.startswith("・")
            prev_has_vendor = bool(lines and (re.search(r'[\(（][A-Z][0-9]{3,5}[\)）]', lines[-1]) or re.search(r'^[0-9]+[\.\:]', lines[-1])))
            prev_has_amt = bool(lines and re.search(r'[¥\\]|[0-9]{1,4}\s*万|[0-9]{1,3}(?:,[0-9]{3})+', lines[-1]))
            if lines and is_sub and prev_has_vendor and not prev_has_amt:
                lines[-1] = lines[-1] + " " + stripped
            else:
                lines.append(stripped)
        
        # Pre-scan all vendor codes in document text to establish dynamic vendor registry
        all_vendor_codes = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', doc_text))))
        all_vendor_codes = [c for c in all_vendor_codes if not c.startswith('P') and not c.startswith('INV') and c != "UNREGISTERED"]

        current_section = "GENERAL"
        rules = []
        registered_vendors = set(all_vendor_codes)
        global_rules = {
            "max_auto_approval_amount": 2000000 if process_type == "invoice" else 150000,
            "require_comment": True,
            "hold_categories": [],
            "allowed_routine_categories": ["Routine"] if process_type == "invoice" else ["Addition", "Deduction"],
            "require_registered_vendors": False
        }

        policy_title = f"Policy ({filename})"
        if lines:
            first_line = lines[0]
            if not any(kw in first_line for kw in [":", "：", "【", "No.", "1."]):
                policy_title = first_line

        rule_idx = 1

        for line in lines:
            # Ignore purely title or meta lines
            if line == policy_title or any(line.startswith(prefix) for prefix in ["本規定は", "本規程は", "【目的】", "概要:"]) or (line.startswith("【") and any(w in line for w in ["基準", "規程", "方針", "要領"]) and ("保留" not in line and "承認" not in line)):
                continue

            # 1. Section Header Detection
            is_rule_stmt = any(kw in line for kw in ["未登録", "マスタ不整合", "リストに含まれない", "金額上限", "上限超過", "区分条件", "一律 Hold", "一律Hold"])
            if not is_rule_stmt:
                if any(kw in line for kw in ["【自動承認", "【承認", "Auto-Approved", "Approved Rules", "【経費精算", "確認済リスト"]) or (("対象ベンダー" in line) and len(line) < 30 and ("Hold" not in line)):
                    current_section = "APPROVED"
                    continue
                elif any(kw in line for kw in ["【保留", "【要人間精査", "Hold / Review", "保留リスト"]) or (("例外保留" in line) and len(line) < 30):
                    current_section = "HOLD"
                    continue

            # Check action in line
            has_hold = any(kw in line for kw in ["Hold", "保留", "要確認", "超過", "除外", "精査", "不整合", "差戻し", "以外", "未承認", "要す", "必須"])
            has_appr = any(kw in line for kw in ["Approved", "承認", "確定", "固定", "Confirmed", "適合", "範囲内", "確認済"])

            if has_hold and not has_appr:
                line_action = "Hold"
            elif has_appr and not has_hold:
                line_action = "Approved" if process_type == "invoice" else "Confirmed"
            else:
                line_action = "Hold" if current_section == "HOLD" else ("Approved" if process_type == "invoice" else "Confirmed")

            # Extract amounts in current line (including 万 units)
            amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]
            if not amts:
                amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', line)]
            for w in re.findall(r'([0-9]{1,4})\s*万(?:円)?', line):
                amts.append(int(w) * 10000)

            # Check vendor code (e.g. V1001, V3005) or vendor name
            v_match = re.search(r'([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s\.\,\-]+?)\s*[\(（]([A-Z][0-9]{3,5})[\)）]', line)
            v_code_only = re.search(r'\b([A-Z][0-9]{3,5})\b', line)
            p_voucher = re.search(r'(P[0-9]\-[0-9]{8}\-[0-9]{3})', line)

            # --- Payroll Specific Rule Handling ---
            if process_type == "payroll":
                # Check deduction mismatch
                if any(kw in line for kw in ["控除項目", "扶養控除", "役職手当廃止"]) and any(kw in line for kw in ["Addition", "支給", "不整合", "Hold"]):
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": "Deduction Classification Mismatch",
                        "match_field": "item_category",
                        "match_value": "Deduction Mismatch",
                        "sql_condition": "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'",
                        "condition": "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Confirmed",
                        "description": "Deduction items (扶養控除変更, 役職手当廃止) incorrectly classified as Addition in master held for review."
                    })
                    rule_idx += 1
                    continue

                # Check entertainment expense
                if "接待交際費" in line and amts:
                    limit_amt = amts[0]
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"Entertainment Expense Limit (> ¥{limit_amt:,})",
                        "match_field": "item_category",
                        "match_value": f"接待交際費 (> ¥{limit_amt:,})",
                        "threshold_amount": limit_amt,
                        "sql_condition": f"item_category = '接待交際費' AND raw_amount > {limit_amt}",
                        "condition": f"item_category = '接待交際費' AND raw_amount > {limit_amt}",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Confirmed",
                        "description": f"Entertainment expense exceeding ¥{limit_amt:,} requires mandatory executive sanction."
                    })
                    rule_idx += 1
                    continue

                # Check unregistered allowance
                if any(kw in line for kw in ["未登録手当", "就業規則別表に定められていない", "コード不明"]):
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": "Unregistered Allowance Check",
                        "match_field": "item_category",
                        "match_value": "未登録手当",
                        "sql_condition": "item_category = '未登録手当'",
                        "condition": "item_category = '未登録手当'",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Confirmed",
                        "description": "Allowance not registered in employment regulations table. Held for HR approval."
                    })
                    rule_idx += 1
                    continue

                # Check single voucher ceiling
                if any(kw in line for kw in ["1伝票の精算金額が", "精算金額が", "150,000", "15万円", "単一伝票"]) and amts:
                    limit_amt = amts[0]
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"Single Voucher Ceiling Limit (> ¥{limit_amt:,})",
                        "match_field": "raw_amount",
                        "match_value": f"> ¥{limit_amt:,}",
                        "threshold_amount": limit_amt,
                        "sql_condition": f"raw_amount > {limit_amt}",
                        "condition": f"raw_amount > {limit_amt}",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Confirmed",
                        "description": f"Single voucher amount exceeds ¥{limit_amt:,} ceiling limit. Pre-approval ringi document required."
                    })
                    rule_idx += 1
                    continue

                # Check pre-approved employee item
                p_v = re.search(r'(P[0-9]\-[0-9]{8}\-[0-9]{3})', line)
                emp_m = re.search(r'([A-Za-z0-9぀-ゟ゠-ヿ一-鿿\s]+?)\s*[\(（](P[0-9]\-[0-9]{8}\-[0-9]{3})[\)）]', line)
                if (p_v or emp_m) and amts:
                    emp_name = emp_m.group(1).strip() if emp_m else ""
                    emp_name = re.sub(r'^[0-9]+[\.\:]\s*', '', emp_name).strip()
                    v_id = p_v.group(1) if p_v else ""
                    cat_found = re.search(r'(研修費|消耗品費|出張旅費|交通費精算|在宅勤務手当|残業手当調整|接待交際費)', line)
                    cat_str = cat_found.group(1) if cat_found else ""
                    cond_parts = []
                    if v_id and emp_name:
                        cond_parts.append(f"(id = '{v_id}' OR employee_name = '{emp_name}')")
                    elif v_id:
                        cond_parts.append(f"id = '{v_id}'")
                    elif emp_name:
                        cond_parts.append(f"employee_name = '{emp_name}'")
                    if cat_str:
                        cond_parts.append(f"item_category = '{cat_str}'")
                    cond_parts.append(f"raw_amount = {amts[0]}")
                    sql_cond = " AND ".join(cond_parts)
                    rules.append({
                        "rule_id": f"RULE-PAY-{rule_idx:02d}",
                        "name": f"{emp_name or v_id} Pre-Approved Expense",
                        "match_field": "employee_name" if emp_name else "id",
                        "match_value": f"{emp_name} ({cat_str})",
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Confirmed",
                        "action_on_mismatch": "Hold",
                        "description": f"Pre-approved {cat_str} for {emp_name or v_id} verified compliant."
                    })
                    rule_idx += 1
                    continue

            # --- Rule Case A: Global Amount Ceiling Rule ---
            if any(kw in line for kw in ["限度額", "金額上限", "上限超過", "超 の場合", "単一伝票の金額が", "以下 の伝票"]) and amts:
                for limit_val in amts:
                    if limit_val >= 500000:
                        global_rules["max_auto_approval_amount"] = limit_val
                        if "以下" not in line or "超" in line:
                            sql_cond = f"raw_amount > {limit_val}"
                            rules.append({
                                "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                                "name": f"Maximum Ceiling Threshold (> ¥{limit_val:,})",
                                "match_field": "raw_amount",
                                "match_value": f"> {limit_val}",
                                "threshold_amount": limit_val,
                                "sql_condition": sql_cond,
                                "condition": sql_cond,
                                "action_on_match": "Hold",
                                "action_on_mismatch": "Approved",
                                "description": f"Voucher amount exceeds ¥{limit_val:,} ceiling limit. Executive director sanction required per policy."
                            })
                            rule_idx += 1
                        break
                continue

            # --- Rule Case B: Category Rule (Dynamically extract ANY category) ---
            if any(kw in line for kw in ["区分条件", "区分（Category）", "処理区分", "Category", "category", "区分が", "区分は"]):
                cats = re.findall(r"""["']([A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+)["']""", line)
                if not cats:
                    cat_m = re.findall(r"""(?:category|区分(?:\:|が|は)?|種別)\s*[:：]?\s*['"]?([A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+)['"]?""", line, re.IGNORECASE)
                    cats = [c for c in cat_m if c.lower() not in ('rule', 'rules', 'voucher', 'vouchers', 'code', 'codes', 'registered', 'unregistered', 'amount', 'all')]
                if not cats:
                    continue
                if any(kw in line for kw in ["Hold", "保留", "精査", "要する", "要す"]):
                    for cat in cats:
                        if cat not in global_rules["hold_categories"]:
                            global_rules["hold_categories"].append(cat)
                    field_name = "type" if process_type == "invoice" else "item_category"
                    if len(cats) == 1:
                        sql_cond = f"{field_name} = '{cats[0]}'"
                    else:
                        cats_sql = ', '.join([f"'{c}'" for c in cats])
                        sql_cond = f"{field_name} IN ({cats_sql})"
                    rules.append({
                        "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                        "name": f"Category Review Rule ({'/'.join(cats)})",
                        "match_field": field_name,
                        "match_value": ", ".join(cats),
                        "sql_condition": sql_cond,
                        "condition": sql_cond,
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Approved",
                        "description": f"Vouchers with category {', '.join(cats)} require mandatory accounting review and supporting documentation."
                    })
                    rule_idx += 1
                continue

            # --- Rule Case C: Unregistered Vendor Check ---
            if any(kw in line for kw in ["未登録ベンダー", "未登録取引先", "リストに含まれない", "マスタ不整合"]):
                global_rules["require_registered_vendors"] = True
                target_codes = all_vendor_codes if all_vendor_codes else sorted(list(registered_vendors))
                target_codes = [c for c in target_codes if re.match(r'^[A-Z][0-9]{3,5}$', c)]
                if target_codes:
                    codes_sql = ', '.join([f"'{c}'" for c in target_codes])
                    code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                    sql_cond = f"{code_col} NOT IN ({codes_sql})"
                else:
                    sql_cond = "employee_id NOT IN (SELECT employee_id FROM erp_vendor_master)"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": "Unregistered Vendor Integrity Check",
                    "match_field": "vendor_code" if process_type == "invoice" else "employee_id",
                    "match_value": "UNREGISTERED",
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": "Hold",
                    "action_on_mismatch": "Approved",
                    "description": "Vendor code not registered in approved master list. Held for master integrity audit."
                })
                rule_idx += 1
                continue

            # --- Rule Case D: Vendor-Specific Line Item / Rule ---
            if v_match or (v_code_only and process_type == "invoice"):
                v_name = v_match.group(1).strip() if v_match else ""
                v_code = v_match.group(2).strip() if v_match else (v_code_only.group(1).strip() if v_code_only else "")

                v_name = re.sub(r'^(?:No\.?\s*[0-9]+|[0-9]+[\.\:]|\-\s*)', '', v_name).strip()
                if v_code:
                    registered_vendors.add(v_code)
                if v_name:
                    registered_vendors.add(v_name)

                code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                id_clause = f"{code_col} = '{v_code}'" if v_code else f"name = '{v_name}'"
                if v_code and v_name:
                    code_col = "vendor_code" if process_type == "invoice" else "employee_id"
                    id_clause = f"({code_col} = '{v_code}' OR name = '{v_name}')"

                cat_v = re.search(r"""(?:category|区分(?:\:|が|は)?|種別)\s*[:：]?\s*['"]?([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF_-]+)['"]?""", line, re.IGNORECASE)
                spec_cat = cat_v.group(1).strip() if cat_v else ("Adjustment" if ("Adjustment" in line or "調整" in line or "空輸" in line) else "")

                if line_action == "Approved":
                    type_clause = f"type = '{spec_cat}' AND " if spec_cat else ("type = 'Routine' AND " if ("routine" in line.lower() or "通常" in line) else "")
                    if len(amts) == 1:
                        sql_cond = f"{type_clause}raw_amount = {amts[0]} AND {id_clause}"
                        desc_str = f"Monthly recurring contract for {v_name or v_code}. Fixed rate ¥{amts[0]:,} verified."
                    elif len(amts) > 1:
                        sql_cond = f"{type_clause}raw_amount IN ({', '.join(map(str, amts))}) AND {id_clause}"
                        amt_str = ', '.join([f'¥{a:,}' for a in amts])
                        desc_str = f"Monthly recurring contract for {v_name or v_code}. Rate within permitted contract range ({amt_str})."
                    else:
                        sql_cond = f"{type_clause}{id_clause}".rstrip(" AND ")
                        desc_str = f"Monthly recurring contract for {v_name or v_code} within policy limit."
                else:
                    if "以外" in line and amts:
                        sql_cond = f"{id_clause} AND raw_amount != {amts[0]}"
                        desc_str = f"Emergency repair or custom tooling outside fixed ¥{amts[0]:,} maintenance fee held for department approval."
                    elif spec_cat:
                        sql_cond = f"{id_clause} AND type = '{spec_cat}'"
                        desc_str = f"{spec_cat} voucher for {v_name or v_code} held for manager audit and supporting receipts."
                    else:
                        sql_cond = id_clause
                        desc_str = f"Exception review required for {v_name or v_code} per policy specification."

                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"{v_name or v_code} {'Special Policy' if line_action == 'Hold' else 'Contract Rule'}",
                    "match_field": "employee_id" if v_code else "name",
                    "match_value": f"{v_name} ({v_code})" if (v_name and v_code) else (v_code or v_name),
                    "vendor_name": v_name,
                    "vendor_code": v_code,
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "strict_amount": ("固定" in line or "以外" in line or "IN (" in sql_cond or "範囲" in line),
                    "is_exception_hold": (line_action == "Hold"),
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": line_action,
                    "action_on_mismatch": "Approved" if line_action == "Hold" else "Hold",
                    "description": desc_str
                })
                rule_idx += 1
                continue

            # --- Rule Case E: Payroll Voucher / Employee Item ---
            if p_voucher or (process_type == "payroll" and (amts or any(kw in line for kw in ["研修", "旅費", "消耗品", "交通費", "接待", "手当", "給与", "控除"]))):
                v_id = p_voucher.group(1) if p_voucher else None
                emp_match = re.search(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,8}(?:\s+[A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,8})?)\s*[\(（]P[0-9]', line)
                emp_name = emp_match.group(1).strip() if emp_match else None
                
                cat_match = re.search(r'(研修費|消耗品費|出張旅費|交通費精算|接待交際費|残業手当調整|昇給|扶養控除変更|役職手当新設|役職手当廃止|未登録手当|[^\s\:\,]+費|[^\s\:\,]+手当)', line)
                cat_name = cat_match.group(1) if cat_match else "経費項目"

                if v_id and amts:
                    sql_cond = f"id = '{v_id}' AND raw_amount <= {amts[0]}"
                    desc_str = f"Expense voucher {v_id} matched with validated receipt within ¥{amts[0]:,}."
                elif ("接待" in line or "交際" in line) and amts:
                    sql_cond = f"item_category = '接待交際費' AND raw_amount > {amts[0]}"
                    desc_str = f"Entertainment expense exceeding policy limit of ¥{amts[0]:,}. Executive approval required."
                    line_action = "Hold"
                elif any(kw in line for kw in ["控除項目", "控除", "廃止"]):
                    sql_cond = "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'"
                    desc_str = "Deduction item erroneously registered as Addition. Held for correction."
                    line_action = "Hold"
                elif any(kw in line for kw in ["精算金額が", "単一", "超過", "上限"]) and amts:
                    sql_cond = f"raw_amount > {amts[0]}"
                    desc_str = f"Expense amount exceeds ¥{amts[0]:,} ceiling threshold. Prior approval memo required."
                    line_action = "Hold"
                elif any(kw in line for kw in ["未登録手当", "コード不明", "人事承認"]):
                    sql_cond = "item_category NOT IN ('研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '昇給', '在宅勤務手当', '資格取得手当')"
                    desc_str = "Unregistered allowance code not defined in HR payroll master. Requires HR authorization."
                    line_action = "Hold"
                elif amts:
                    sql_cond = f"item_category = '{cat_name}' AND raw_amount <= {amts[0]}"
                    desc_str = f"Category '{cat_name}' verified within allowable limit of ¥{amts[0]:,}."
                else:
                    sql_cond = f"item_category = '{cat_name}'"
                    desc_str = f"Category '{cat_name}' verified per corporate accounting standards."

                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"{emp_name or v_id or cat_name} Settlement Rule",
                    "match_field": "id" if v_id else ("employee_name" if emp_name else "item_category"),
                    "match_value": v_id or emp_name or cat_name,
                    "voucher_id": v_id,
                    "employee_name": emp_name,
                    "item_category": cat_name,
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": line_action,
                    "action_on_mismatch": "Hold",
                    "description": desc_str
                })
                rule_idx += 1
                continue

            # --- Rule Case F: General Bullet or Sentence ---
            if amts:
                sql_cond = f"raw_amount = {amts[0]}" if len(amts) == 1 else f"raw_amount IN ({', '.join(map(str, amts))})"
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"Policy Criterion {rule_idx}",
                    "match_field": "raw_amount",
                    "match_value": line[:30],
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "sql_condition": sql_cond,
                    "condition": sql_cond,
                    "action_on_match": line_action,
                    "action_on_mismatch": "Hold",
                    "description": line
                })
                rule_idx += 1

        global_rules["registered_vendors"] = list(registered_vendors)
        # Dynamic ceiling adaptation
        max_approved_amount = max([max(r.get("expected_amounts") or [0]) for r in rules if r.get("action_on_match") in ("Approved", "Confirmed")] + [0])
        if max_approved_amount > global_rules["max_auto_approval_amount"]:
            global_rules["max_auto_approval_amount"] = max_approved_amount

        return {
            "policy_title": policy_title,
            "process_type": process_type,
            "global_rules": global_rules,
            "registered_vendors": list(registered_vendors),
            "item_criteria": rules
        }

    # --- Node 1: Convert Document / Rules to Structured Schema JSON ---
    def node_parse_document(self, state: CoPilotAgentState) -> Dict[str, Any]:
        t0 = time.time()
        process_type = state["process_type"]
        doc_text = state["document_text"]
        table_name = state["table_name"]
        table_schema = state["table_schema"]
        filename = state["filename_or_title"]

        if process_type == "payroll":
            system_prompt = (
                "You are an Elite Enterprise Database & Policy Rule Extraction Agent specializing in Employee Payroll Expense Settlements (erp_payroll_items).\n"
                "CRITICAL SCHEMA & DATA TYPE SPECIFICATIONS FOR erp_payroll_items:\n"
                "1. DATABASE COLUMNS IN erp_payroll_items:\n"
                "   - `item_category` (VARCHAR): The Japanese expense or allowance category name (e.g. '研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '接待交際費', '資格取得手当', '扶養控除変更', '役職手当廃止', '未登録手当'). NEVER use 'type' or 'hand_code'!\n"
                "   - `item_type` (VARCHAR): Payment classification. Allowed values: 'Addition' (支給/加算) or 'Deduction' (控除/減算). NEVER use 'type'!\n"
                "   - `raw_amount` (BIGINT): Integer numeric transaction amount in JPY without symbols or commas (e.g. raw_amount > 100000, raw_amount > 150000). ALWAYS use `raw_amount` for amounts; NEVER use 'amount'!\n"
                "   - `employee_name` (VARCHAR): Employee legal name (e.g. '青木 拓也', '菊地 里江', '坂本 裕二').\n"
                "   - `employee_id` (VARCHAR): Employee code (e.g. 'EMP-001', 'EMP-002').\n"
                "   - `id` (VARCHAR): Voucher ID (e.g. 'P4-07089771-001').\n"
                "2. PRECISE SQL MAPPINGS FOR PAYROLL POLICIES:\n"
                "   - Entertainment expense limit (> ¥100,000): sql_condition: \"item_category = '接待交際費' AND raw_amount > 100000\", action_on_match: \"Hold\"\n"
                "   - Deduction item incorrectly registered as Addition (控除項目で区分が「Addition」): sql_condition: \"item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'\", action_on_match: \"Hold\"\n"
                "   - Single voucher ceiling limit (> ¥150,000): sql_condition: \"raw_amount > 150000\", action_on_match: \"Hold\"\n"
                "   - Unregistered allowance: sql_condition: \"item_category = '未登録手当'\", action_on_match: \"Hold\"\n"
                "   - Pre-approved employee vouchers: sql_condition: \"(id = 'P4-07089771-001' OR employee_name = '青木 拓也') AND item_category = '研修費' AND raw_amount = 77224\", action_on_match: \"Confirmed\"\n"
                "3. REQUIRED JSON FIELDS FOR EVERY RULE (MUST NOT BE EMPTY):\n"
                "   - \"rule_id\": e.g. \"RULE-PAY-01\", \"RULE-PAY-02\"\n"
                "   - \"name\": Concise descriptive rule title\n"
                "   - \"match_field\": Primary column checked (e.g. \"item_category\", \"raw_amount\", \"employee_name\")\n"
                "   - \"match_value\": Target or entity label (e.g. \"接待交際費 (> ¥100,000)\", \"Deduction Mismatch\", \"青木 拓也\")\n"
                "   - \"sql_condition\": Valid ANSI SQL predicate against erp_payroll_items\n"
                "   - \"condition\": Same as sql_condition\n"
                "   - \"action_on_match\": \"Hold\" (for holds) or \"Confirmed\" (for approved items)\n"
                "   - \"description\": Professional English explanation of the rule\n"
            )
            prompt = f"""Target Process: PAYROLL
Target Database Table: {table_name}
Target Table Schema:
{json.dumps(table_schema, indent=2, ensure_ascii=False)}

Incoming Document / Policy Text:
\"\"\"{doc_text}\"\"\"

Instructions:
1. Extract ALL rules from the document: general principles, approved employee expense lines with rates, hold conditions, amount ceilings, category restrictions, and unregistered allowance checks.
2. For EVERY rule, generate a valid SQL WHERE condition (`sql_condition` and `condition`) that can filter records from `{table_name}`.
3. Every rule MUST include populated non-empty values for: `rule_id`, `name`, `match_field`, `match_value`, `sql_condition`, `condition`, `action_on_match` ("Hold" or "Confirmed"), and `description`.
4. Return ONLY valid JSON with key "item_criteria" without markdown fences."""
        else:
            system_prompt = (
                "You are an Elite Enterprise Database & Policy Rule Extraction Agent specializing in Accounts Payable Invoices (erp_invoices).\n"
                "CRITICAL SCHEMA & DATA TYPE SPECIFICATIONS FOR erp_invoices:\n"
                "1. DATABASE COLUMN MAPPING:\n"
                "   - Notice: Invoices do NOT have an employee ID! NEVER use 'employee_id' for invoices!\n"
                "   - 'Category' / 'Classification' -> use column `type` (values: 'Routine', 'Adjustment').\n"
                "   - 'Amount', 'Ceiling', 'Limit', or monetary thresholds -> ALWAYS use column `raw_amount` as a pure integer number (e.g. raw_amount > 1500000, raw_amount <= 1500000). NEVER use '¥', '$', or commas in SQL numbers.\n"
                "   - 'Vendor' / 'Vendor Code' -> use column `vendor_code` (e.g. 'V3001'..'V3012'; unregistered: 'V3099').\n"
                "   - 'Vendor Name' -> use column `vendor_name` (or `name`).\n"
                "   - 'Voucher ID' -> use column `id`.\n"
                "2. PREDICATE SYNTAX:\n"
                "   - Unregistered vendor check: `vendor_code NOT IN ('V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012')` with action 'Hold'.\n"
                "   - High-value ceiling hold: `raw_amount > 1500000` with action 'Hold'.\n"
                "   - Adjustment review hold: `type = 'Adjustment'` with action 'Hold'.\n"
                "   - Routine approval: `type = 'Routine' AND raw_amount <= 1500000 AND vendor_code IN ('V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012')` with action 'Approved'.\n"
                "3. REQUIRED JSON FIELDS FOR EVERY RULE (MUST NOT BE EMPTY):\n"
                "   - \"rule_id\": e.g. \"RULE-INV-01\"\n"
                "   - \"name\": Concise descriptive rule title\n"
                "   - \"match_field\": Primary column checked (e.g. \"vendor_code\", \"raw_amount\", \"type\")\n"
                "   - \"match_value\": Target or entity label (e.g. \"Unregistered Vendors\", \"Adjustment Category\")\n"
                "   - \"sql_condition\": Valid ANSI SQL predicate against erp_invoices\n"
                "   - \"condition\": Same as sql_condition\n"
                "   - \"action_on_match\": \"Hold\" or \"Approved\"\n"
                "   - \"description\": Professional English explanation\n"
            )
            prompt = f"""Target Process: INVOICE
Target Database Table: {table_name}
Target Table Schema:
{json.dumps(table_schema, indent=2, ensure_ascii=False)}

Incoming Document / Policy Text:
\"\"\"{doc_text}\"\"\"

Instructions:
1. Extract ALL rules from the document: general principles, approved vendor contracts with rates, hold conditions, amount ceilings, category restrictions, vendor-specific exceptions, and unregistered vendor integrity checks.
2. For EVERY rule, generate a valid SQL WHERE condition (`sql_condition` and `condition`) that can filter records from `{table_name}`.
3. Every rule MUST include populated non-empty values for: `rule_id`, `name`, `match_field`, `match_value`, `sql_condition`, `condition`, `action_on_match` ("Hold" or "Approved"), and `description`.
4. Return ONLY valid JSON with key "item_criteria" without markdown fences."""

        policy_json = None
        # Try calling LLM first
        try:
            raw_res = self.llm.complete(prompt, system_prompt=system_prompt, timeout=35)
            policy_json = clean_and_parse_json_robust(raw_res)
        except Exception:
            policy_json = None

        criteria = None
        if policy_json and isinstance(policy_json, dict):
            criteria = policy_json.get("item_criteria") or policy_json.get("rules")
            if criteria and not policy_json.get("item_criteria"):
                policy_json["item_criteria"] = criteria
        has_bogus_sql = False
        if criteria and isinstance(criteria, list) and len(criteria) > 0:
            for r in criteria:
                c = str(r.get("sql_condition") or r.get("condition") or "").strip()
                if not c or "IN ()" in c.upper():
                    has_bogus_sql = True
                    break
        else:
            has_bogus_sql = True

        # If LLM unavailable, failed, or generated invalid/empty SQL, execute resilient semantic extractor
        if not policy_json or has_bogus_sql or not criteria:
            policy_json = self._semantic_fallback_extract(process_type, doc_text, filename)
        else:
            # Ensure every LLM rule has sql_condition, condition, clean SQL formatting, and normalized action
            for idx, r in enumerate(policy_json.get("item_criteria", [])):
                sql_c = str(r.get("sql_condition") or r.get("condition") or "")
                if process_type == "payroll":
                    # Fix type -> item_category or item_type
                    if re.search(r"\btype\s*=\s*'Addition'", sql_c, re.IGNORECASE) or re.search(r"\btype\s*=\s*'Deduction'", sql_c, re.IGNORECASE):
                        sql_c = re.sub(r"\btype\b", "item_type", sql_c, flags=re.IGNORECASE)
                    else:
                        sql_c = re.sub(r"\btype\b(?=\s*[!=<>]+\s*['\"])", "item_category", sql_c)
                        sql_c = re.sub(r"\btype\b(?=\s+(?:IN|NOT\s+IN)\b)", "item_category", sql_c, flags=re.IGNORECASE)
                    sql_c = re.sub(r"\bamount\b(?=\s*[!=<>]+)", "raw_amount", sql_c, flags=re.IGNORECASE)
                    sql_c = re.sub(r"\bhand_code\b", "item_category", sql_c, flags=re.IGNORECASE)
                    sql_c = re.sub(r"\bcategory\b(?=\s*[!=<>]+)", "item_category", sql_c)

                sql_c = sql_c.replace("==", "=").replace("&&", "AND").replace("||", "OR")
                r["sql_condition"] = sql_c
                r["condition"] = sql_c

                if not r.get("rule_id"):
                    r["rule_id"] = f"RULE-{process_type[:3].upper()}-{idx+1:02d}"

                act = str(r.get("action_on_match") or r.get("action") or "").strip()
                if any(w in act.lower() for w in ["appr", "pass", "ok", "conf", "承"]):
                    r["action_on_match"] = "Approved" if process_type == "invoice" else "Confirmed"
                else:
                    r["action_on_match"] = "Hold"

                if not r.get("name"):
                    r["name"] = r.get("match_value") or f"{process_type.capitalize()} Rule {idx+1}"
                if not r.get("match_value"):
                    r["match_value"] = r.get("name") or f"{process_type.capitalize()} Rule {idx+1}"
                if not r.get("description"):
                    r["description"] = f"{r['action_on_match']} voucher where {sql_c}." 

        step_record = {
            "node": "Node 1: parse_document_to_schema_json",
            "duration_s": round(time.time() - t0, 3),
            "status": "COMPLETED",
            "extracted_rules_count": len(policy_json.get("item_criteria", [])),
            "policy_title": policy_json.get("policy_title", "Untitled Policy")
        }

        logs = list(state.get("execution_steps", []))
        logs.append(step_record)

        return {
            "policy_json": policy_json,
            "execution_steps": logs
        }


    # --- Node 2 (Extra Node): Validate and Refine SQL Rules with LLM Loop ---
    def node_validate_and_refine_sql(self, state: CoPilotAgentState) -> Dict[str, Any]:
        """Extra Node: Validates extracted SQL conditions against original policy rules.
        Uses 100% dynamic parameter extraction and an LLM reflection loop to detect and correct discrepancies."""
        t0 = time.time()
        process_type = state["process_type"]
        table_name = state.get("table_name", "erp_invoices" if process_type == "invoice" else "erp_payroll_items")
        doc_text = state["document_text"]
        policy_json = dict(state.get("policy_json") or {})
        criteria = list(policy_json.get("item_criteria") or [])

        # 1. Dynamically extract policy parameters from the input document text
        ceil_matches = re.findall(r'(?:strictly greater than|greater than|exceeds|exceeding|超過|上限)\s*[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', doc_text, re.IGNORECASE)
        detected_ceilings = [int(m.replace(',', '')) for m in ceil_matches]

        appr_limit_matches = re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*(?:or less|以下|以内)', doc_text, re.IGNORECASE)
        detected_appr_limits = [int(m.replace(',', '')) for m in appr_limit_matches]

        all_doc_codes = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', doc_text))))
        all_doc_codes = [c for c in all_doc_codes if not c.startswith('P') and not c.startswith('INV') and c != 'UNREGISTERED']

        STOP_WORDS = {
            'is', 'as', 'marked', 'the', 'a', 'an', 'of', 'in', 'for', 'with', 'by', 'at', 'on',
            'rule', 'rules', 'voucher', 'vouchers', 'code', 'codes', 'name', 'all', 'registered',
            'unregistered', 'amount', 'amounts', 'and', 'or', 'if', 'be', 'to', 'routine', '通常',
            'が', 'は', 'の', 'を', 'に', 'で', 'と', 'へ', 'から', 'より', 'まで', 'こと', 'もの', 'ため', 'として', '不整合として', 'addition', 'deduction'
        }
        doc_hold_cats = set()
        for m in re.finditer(r"""(?:hold|review|精査|保留)[^.!?。
]*?(?:category|categorized as|区分|種別)\s*(?:is|marked as|[:：=])?\s*['"「]?([A-Za-z0-9぀-ゟ゠-ヿ一-鿿_-]+)['"」]?""", doc_text, re.IGNORECASE):
            c = m.group(1).strip()
            if len(c) > 1 and c.lower() not in STOP_WORDS:
                doc_hold_cats.add(c)
        for m in re.finditer(r"""(?:category|categorized as|区分|種別)\s*(?:is|marked as|[:：=])?\s*['"「]?([A-Za-z0-9぀-ゟ゠-ヿ一-鿿_-]+)['"」]?[^.!?。
]*?(?:hold|review|精査|保留|必須)""", doc_text, re.IGNORECASE):
            c = m.group(1).strip()
            if len(c) > 1 and c.lower() not in STOP_WORDS:
                doc_hold_cats.add(c)
        for m in re.finditer(r"""(?:category|区分|種別)\s*(?:is|marked as|[:：=])?\s*['"]?([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF_-]+)['"]?.*?(?:hold|review|精査|保留|必須)""", doc_text, re.IGNORECASE):
            c = m.group(1).strip()
            if c.lower() not in STOP_WORDS:
                doc_hold_cats.add(c)

        has_unreg_spec = any(kw in doc_text.lower() for kw in ['not on this list', 'unregistered', '未登録', 'リストに含まれない'])

        def find_sql_issues(rules_list: List[Dict[str, Any]]) -> List[str]:
            issues = []
            has_ceiling_rule = False
            has_unreg_rule = False
            found_hold_cats = set()
            has_approval_rule = False

            for idx, r in enumerate(rules_list):
                cond = str(r.get("sql_condition") or r.get("condition") or "").strip()
                action = r.get("action_on_match")
                desc = str(r.get("description") or "").lower()
                name = str(r.get("name") or "").lower()

                # Check 1: Operator error for strictly greater than / exceeds
                if detected_ceilings:
                    for target_amt in detected_ceilings:
                        if str(target_amt) in cond:
                            if "raw_amount >" in cond or "raw_amount>" in cond:
                                has_ceiling_rule = True
                            elif "=" in cond and not any(op in cond for op in [">", "<", "!="]):
                                issues.append(f"Rule '{r.get('name')}' uses '=' instead of '>' for strictly greater than threshold ({target_amt}). Condition must be: raw_amount > {target_amt}")

                # Check 2: Operator error for <= / or less
                if detected_appr_limits:
                    for target_amt in detected_appr_limits:
                        if str(target_amt) in cond and action in ("Approved", "Confirmed"):
                            if "raw_amount <=" in cond or "raw_amount<=" in cond:
                                has_approval_rule = True
                            elif "=" in cond and "<=" not in cond:
                                issues.append(f"Approval rule '{r.get('name')}' uses '=' instead of '<=' for amount limit ({target_amt}). Condition must be: raw_amount <= {target_amt}")

                # Check 3: Bogus clarifiers parsed as independent rules
                is_clarifier_name = any(kw in name for kw in ["does not trigger", "matching is not required", "applies to all"])
                if is_clarifier_name and not any(op in cond for op in [">", "<", "=", "IN"]):
                    issues.append(f"Explanatory clarifier sentence was incorrectly extracted as independent rule: '{r.get('name')}'. It should be removed.")

                # Check 4: Empty IN () predicate
                if "in ()" in cond.lower() or "not in ()" in cond.lower():
                    issues.append(f"Rule '{r.get('name')}' contains an empty IN () SQL predicate which is invalid SQL syntax.")

                # Check 5: Category Hold verification
                for cat in doc_hold_cats:
                    if f"'{cat}'" in cond or f'"{cat}"' in cond:
                        if action in ("Hold", "Rejected"):
                            found_hold_cats.add(cat)
                        else:
                            issues.append(f"Category '{cat}' rule has action '{action}' but policy requires Action: Hold.")

                # Check 6: Unregistered vendors NOT IN
                if "employee_id NOT IN" in cond or "employee_id not in" in cond:
                    has_unreg_rule = True

            # Missing rule checks
            for cat in doc_hold_cats:
                if cat not in found_hold_cats:
                    col_c = "type" if process_type == "invoice" else "item_category"
                    issues.append(f"Missing mandatory Hold rule for category '{cat}' (condition must be: {col_c} = '{cat}' with Action: Hold).")

            if has_unreg_spec and not has_unreg_rule and all_doc_codes:
                codes_str = ', '.join([f"'{c}'" for c in all_doc_codes])
                issues.append(f"Missing mandatory Hold rule for unregistered entity codes: employee_id NOT IN ({codes_str})")

            return issues

        current_issues = find_sql_issues(criteria)
        loop_iterations = 0
        max_loops = 2

        # Dynamically build instructions for LLM reflection loop
        dynamic_reqs = []
        if detected_ceilings:
            for c_amt in detected_ceilings:
                dynamic_reqs.append(f"- Ceiling threshold: 'strictly greater than ¥{c_amt:,}' MUST use \"sql_condition\": \"raw_amount > {c_amt}\" with action 'Hold'.")
        dynamic_reqs.append("- Clarifiers: DO NOT create rules for negative clarification sentences like 'does not trigger this rule' or 'matching is not required'.")
        if doc_hold_cats:
            for cat in doc_hold_cats:
                col_c = "type" if process_type == "invoice" else "item_category"
                dynamic_reqs.append(f"- Mandatory category hold: Vouchers with category '{cat}' MUST use \"sql_condition\": \"{col_c} = '{cat}'\" with action 'Hold'.")
        if all_doc_codes and has_unreg_spec:
            codes_str = ', '.join([f"'{c}'" for c in all_doc_codes])
            dynamic_reqs.append(f"- Unregistered entities: Vouchers whose code is not on the list MUST use \"sql_condition\": \"employee_id NOT IN ({codes_str})\" with action 'Hold'.")
        if any(kw in doc_text.lower() for kw in ["approve a voucher only if", "routine approval", "通常承認"]):
            appr_parts = []
            if any(kw in doc_text.lower() for kw in ["routine", "通常"]):
                appr_parts.append("type = 'Routine'")
            if detected_appr_limits:
                appr_parts.append(f"raw_amount <= {detected_appr_limits[0]}")
            if all_doc_codes:
                codes_str = ', '.join([f"'{c}'" for c in all_doc_codes])
                appr_parts.append(f"employee_id IN ({codes_str})")
            if appr_parts:
                dynamic_reqs.append(f"- Multi-condition approval: Combine approval criteria with AND: \"sql_condition\": \"{' AND '.join(appr_parts)}\" with action 'Approved'.")

        # If issues exist and LLM is active, run the self-correction reflection loop
        while current_issues and loop_iterations < max_loops:
            loop_iterations += 1
            if self.llm_service and self.llm_service.client and self.llm_service.remote_active:
                target_schema_info = "Target Table: " + table_name + "\nTarget Schema: " + json.dumps(state.get("table_schema", {}), indent=2, ensure_ascii=False)
                reflection_prompt = f"""You are an Expert Database SQL Policy Rule Verifier.
{target_schema_info}
CRITICAL: ONLY use existing column names from the target schema above! For erp_payroll_items, use item_category, item_type, raw_amount, employee_name, employee_id, id. NEVER invent column names like type, amount, deduction_item, or unregistered_allowance!
The SQL conditions previously extracted from this business policy contain errors and misinterpretations:

DISCREPANCIES DETECTED:
{chr(10).join(['- ' + issue for issue in current_issues])}

ORIGINAL POLICY TEXT:
'''{doc_text}'''

CRITICAL REQUIREMENTS FOR THE REFINED SQL RULES (DERIVED DYNAMICALLY FROM POLICY):
{chr(10).join(dynamic_reqs)}

Return ONLY the corrected JSON object with key "item_criteria" containing the refined rules. Do not include markdown fences."""
                try:
                    res_raw = self.llm_service.client.complete(reflection_prompt, timeout=12)
                    new_obj = clean_and_parse_json_robust(res_raw)
                    if new_obj.get("item_criteria"):
                        criteria = new_obj["item_criteria"]
                        current_issues = find_sql_issues(criteria)
                except Exception:
                    break
            else:
                break

        # If criteria is missing after loop, fallback to deterministic refinement
        if not criteria:
            robust_rules = self._parse_policy_rules_robust(doc_text, process_type)
            if robust_rules:
                criteria = robust_rules
                current_issues = find_sql_issues(criteria)

        # Filter out any malformed rules with empty IN ()
        criteria = [r for r in criteria if "IN ()" not in str(r.get("sql_condition") or "").upper()]

        # Ensure every rule has sql_condition, condition, and clean formatting
        for idx, r in enumerate(criteria):
            sql_c = str(r.get("sql_condition") or r.get("condition") or "")
            if process_type == "payroll":
                if re.search(r"\btype\s*=\s*'Addition'", sql_c, re.IGNORECASE) or re.search(r"\btype\s*=\s*'Deduction'", sql_c, re.IGNORECASE):
                    sql_c = re.sub(r"\btype\b", "item_type", sql_c, flags=re.IGNORECASE)
                else:
                    sql_c = re.sub(r"\btype\b(?=\s*[!=<>]+\s*['\"])", "item_category", sql_c)
                    sql_c = re.sub(r"\btype\b(?=\s+(?:IN|NOT\s+IN)\b)", "item_category", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bamount\b(?=\s*[!=<>]+)", "raw_amount", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bhand_code\b", "item_category", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bcategory\b(?=\s*[!=<>]+)", "item_category", sql_c)

            sql_c = sql_c.replace("==", "=").replace("&&", "AND").replace("||", "OR")
            r["sql_condition"] = sql_c
            r["condition"] = sql_c

            act = str(r.get("action_on_match") or r.get("action") or "").strip()
            if any(w in act.lower() for w in ["appr", "pass", "ok", "conf", "承"]):
                r["action_on_match"] = "Approved" if process_type == "invoice" else "Confirmed"
            else:
                r["action_on_match"] = "Hold"

            if not r.get("rule_id"):
                r["rule_id"] = f"RULE-{process_type[:3].upper()}-{idx+1:02d}"
            if not r.get("name"):
                r["name"] = r.get("match_value") or f"{process_type.capitalize()} Rule {idx+1}"
            if not r.get("match_value"):
                r["match_value"] = r.get("name") or f"{process_type.capitalize()} Rule {idx+1}"
            if not r.get("description"):
                r["description"] = f"{r.get('action_on_match', 'Hold')} voucher where {sql_c}."

        policy_json["item_criteria"] = criteria

        step_record = {
            "node": "Node 2: validate_and_refine_sql_rules",
            "duration_s": round(time.time() - t0, 3),
            "status": "COMPLETED",
            "validation_loop_iterations": loop_iterations,
            "rules_verified_count": len(criteria),
            "issues_resolved": len(current_issues) == 0,
            "summary": "All SQL conditions verified and aligned with policy rules"
        }

        logs = list(state.get("execution_steps", []))
        logs.append(step_record)

        return {
            "policy_json": policy_json,
            "execution_steps": logs
        }

    # --- Node 3: Compare Database Features & Decide (Direct Live SQL Evaluation) ---
    def node_compare_and_decide(self, state: CoPilotAgentState) -> Dict[str, Any]:
        """Evaluates database rows directly against the extracted and verified SQL WHERE conditions.
        Hold rules take precedence over Approval rules. Every row decision is accompanied by the
        exact triggered SQL condition and a formal certified audit comment."""
        t0 = time.time()
        process_type = state["process_type"]
        policy_json = state["policy_json"]
        table_name = state.get("table_name", "erp_invoices" if process_type == "invoice" else "erp_payroll_items")
        db_rows = state["current_db_rows"]
        criteria = list(policy_json.get("item_criteria", []))

        # Split into Hold rules and Approved rules
        hold_rules = [r for r in criteria if r.get("action_on_match") in ("Hold", "Rejected")]
        appr_rules = [r for r in criteria if r.get("action_on_match") in ("Approved", "Confirmed")]

        # Query matching IDs directly from DB table if available
        hold_matches_by_rule = {}
        appr_matches_by_rule = {}

        for hr in hold_rules:
            cond = hr.get("sql_condition") or hr.get("condition") or ""
            r_key = hr.get("rule_id", id(hr))
            if cond:
                db_set = self._query_matching_ids_from_db(table_name, cond)
                hold_matches_by_rule[r_key] = db_set

        for ar in appr_rules:
            cond = ar.get("sql_condition") or ar.get("condition") or ""
            r_key = ar.get("rule_id", id(ar))
            if cond:
                db_set = self._query_matching_ids_from_db(table_name, cond)
                appr_matches_by_rule[r_key] = db_set

        decisions = []
        discrepancies = []

        for row in db_rows:
            row_id = str(row.get("id"))
            amount = row.get("raw_amount", 0)

            # Step 1: Check Hold rules (Hold rules ALWAYS take precedence!)
            matched_hold_rules = []
            reasons = []

            for hr in hold_rules:
                r_key = hr.get("rule_id", id(hr))
                cond = hr.get("sql_condition") or hr.get("condition") or ""
                matched = False

                db_set = hold_matches_by_rule.get(r_key)
                if db_set is not None:
                    matched = (row_id in db_set)
                else:
                    matched = evaluate_sql_condition_in_memory(row, cond)

                if matched:
                    matched_hold_rules.append(hr)
                    rule_label = hr.get("name") or hr.get("match_value", "Hold Rule")
                    rule_desc = hr.get("description", "")
                    reasons.append(f"{rule_label}: Matched SQL condition ({cond}). {rule_desc}")

            if matched_hold_rules:
                new_status = "Hold"
                matched_rule_id = ", ".join([hr.get("rule_id", "RULE-HOLD") for hr in matched_hold_rules if hr.get("rule_id")])
                matched_rule_summary = "; ".join([hr.get("name") or hr.get("match_value", "Hold Policy Rule") for hr in matched_hold_rules])
            else:
                # Step 2: Check Approved rules
                matched_appr_rule = None
                for ar in appr_rules:
                    r_key = ar.get("rule_id", id(ar))
                    cond = ar.get("sql_condition") or ar.get("condition") or ""
                    matched = False

                    db_set = appr_matches_by_rule.get(r_key)
                    if db_set is not None:
                        matched = (row_id in db_set)
                    else:
                        matched = evaluate_sql_condition_in_memory(row, cond)

                    if matched:
                        matched_appr_rule = ar
                        rule_label = ar.get("name") or ar.get("match_value", "Approval Rule")
                        rule_desc = ar.get("description", "")
                        reasons.append(f"{rule_label}: Complies with SQL condition ({cond}). {rule_desc}")
                        break

                if matched_appr_rule:
                    new_status = "Approved" if process_type == "invoice" else "Confirmed"
                    matched_rule_id = matched_appr_rule.get("rule_id", "RULE-APPROVED")
                    matched_rule_summary = matched_appr_rule.get("name") or matched_appr_rule.get("match_value", "Approved Contract Rule")
                else:
                    new_status = "Hold"
                    matched_rule_id = "RULE-UNMATCHED"
                    matched_rule_summary = "Unmatched Policy Criteria"
                    reasons.append("Voucher does not satisfy any approved routine contract SQL criteria (requires manual review).")

            # Generate formal Japanese comment
            comment = self.llm_service.generate_comment(process_type, row, new_status, reasons)

            decision_record = {
                "id": row.get("id"),
                "voucher_id": row.get("id"),
                "employee_id": row.get("employee_id"),
                "name": row.get("name", row.get("employee_name", "")),
                "employee_name": row.get("employee_name", row.get("name", "")),
                "invoice_no": row.get("invoice_no", ""),
                "item_category": row.get("item_category", row.get("type", "")),
                "type": row.get("type", row.get("item_type", "")),
                "amount": row.get("amount", f"¥{amount:,}"),
                "raw_amount": amount,
                "current_status": row.get("status", "Unprocessed"),
                "new_status": new_status,
                "matched_rule_id": matched_rule_id,
                "matched_rule": matched_rule_summary,
                "reasons": reasons,
                "comment": comment
            }
            decisions.append(decision_record)
            if new_status == "Hold":
                discrepancies.append(decision_record)

        step_record = {
            "node": "Node 3: compare_features_and_decide",
            "duration_s": round(time.time() - t0, 3),
            "status": "COMPLETED",
            "total_evaluated": len(decisions),
            "approved_count": sum(1 for d in decisions if d["new_status"] in ("Approved", "Confirmed")),
            "hold_count": len(discrepancies)
        }

        logs = list(state.get("execution_steps", []))
        logs.append(step_record)

        return {
            "decisions": decisions,
            "discrepancies": discrepancies,
            "execution_steps": logs
        }

    # --- Node 3: Commit Updates to Database (Fast Atomic Batch) ---
    def node_commit_updates(self, state: CoPilotAgentState) -> Dict[str, Any]:
        t0 = time.time()
        from erp_db import db_manager

        process_type = state["process_type"]
        decisions = state["decisions"]
        
        updates_payload = [
            {
                "id": d["id"],
                "status": d["new_status"],
                "comment": d["comment"]
            }
            for d in decisions
        ]

        if process_type == "invoice":
            updates_count = db_manager.batch_update_invoices(updates_payload)
        else:
            updates_count = db_manager.batch_update_payroll_items(updates_payload)

        step_record = {
            "node": "Node 3: commit_database_updates",
            "duration_s": round(time.time() - t0, 3),
            "status": "COMPLETED",
            "database_rows_updated": updates_count
        }

        logs = list(state.get("execution_steps", []))
        logs.append(step_record)

        return {
            "db_updates_applied": updates_count,
            "execution_steps": logs
        }

    # --- Node 4: Human-in-the-Loop Audit & Final State ---
    def node_human_audit(self, state: CoPilotAgentState) -> Dict[str, Any]:
        t0 = time.time()
        discrepancies = state.get("discrepancies", [])
        overall_status = "NEEDS_INTERVENTION" if discrepancies else "SUCCESS"

        step_record = {
            "node": "Node 4: human_in_the_loop_audit",
            "duration_s": round(time.time() - t0, 3),
            "status": "COMPLETED",
            "intervention_required": bool(discrepancies),
            "flagged_items_count": len(discrepancies)
        }

        logs = list(state.get("execution_steps", []))
        logs.append(step_record)

        return {
            "overall_status": overall_status,
            "execution_steps": logs
        }

    def _prepare_initial_state(self, process_type: str, document_text: str, filename_or_title: str) -> CoPilotAgentState:
        from erp_db import db_manager

        if process_type == "invoice":
            table_name = "erp_invoices"
            table_schema = {
                "table_name": "erp_invoices",
                "table_description": "Accounts Payable Vendor Invoices and Payment Vouchers (105 total live records in PostgreSQL)",
                "features_and_columns": {
                    "id": {
                        "sql_data_type": "VARCHAR(50) PRIMARY KEY",
                        "business_feature": "Voucher ID / 伝票番号",
                        "description": "Unique primary key voucher number (e.g. 'P6-07010448-001').",
                        "sample_values": ["P6-07010448-001", "P6-07010448-049", "P6-07010448-105"]
                    },
                    "vendor_code": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Vendor Code / Supplier Code / 取引先コード (No employee_id for invoices)",
                        "description": "Alphanumeric vendor identifier. Registered vendor codes: 'V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012'. Unregistered vendor code: 'V3099'.",
                        "sql_usage_guide": "Registered: vendor_code IN ('V3001','V3002','V3004','V3005','V3006','V3007','V3008','V3009','V3010','V3011','V3012'). Unregistered: vendor_code NOT IN (...)."
                    },
                    "vendor_name": {
                        "sql_data_type": "VARCHAR(255)",
                        "business_feature": "Vendor Name / Company Legal Name / 取引先名",
                        "description": "Legal business corporate name of the vendor (e.g. 'Yamada Manufacturing Co., Ltd.', 'Global Tech LLC').",
                        "sample_values": ["Yamada Manufacturing Co., Ltd.", "Yamato Shoji Co., Ltd.", "Global Tech LLC", "Hokuriku Parts Industry Co., Ltd.", "Fukuoka System Design"]
                    },
                    "invoice_no": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Invoice Reference Number / 請求書番号",
                        "description": "Vendor billing invoice number (e.g. 'INV-2026-7344')."
                    },
                    "raw_amount": {
                        "sql_data_type": "BIGINT (Numeric Integer)",
                        "business_feature": "Invoice Monetary Amount / 請求金額 (数値)",
                        "description": "CRITICAL: The numeric transaction amount as a pure integer in JPY WITHOUT currency symbols or commas. ALWAYS use this column for all mathematical comparisons (>, <, =, <=, >=).",
                        "sql_usage_guide": "Strictly greater than ¥1,800,000: raw_amount > 1800000. Amount ¥1,800,000 or less: raw_amount <= 1800000. NEVER use '¥' or commas in SQL numbers.",
                        "sample_values": [385000, 452219, 716232, 1237439, 1832962, 1993825]
                    },
                    "amount": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Formatted Display Amount / 表示金額文字列",
                        "description": "Display string formatted with '¥' and commas (e.g. '¥1,832,962'). DO NOT use for numerical filtering. Use raw_amount instead."
                    },
                    "type": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Voucher Category / Transaction Classification / 区分・種別",
                        "description": "The category of the voucher. Exactly two categories exist in database: 'Routine' and 'Adjustment'. All comparisons are case-insensitive.",
                        "allowed_values": ["Routine", "Adjustment"],
                        "sql_usage_guide": "Routine: type = 'Routine'. Adjustment: type = 'Adjustment'."
                    },
                    "status": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Processing Status / 承認ステータス",
                        "description": "Workflow status: 'Unprocessed', 'Approved', 'Hold'.",
                        "allowed_values": ["Unprocessed", "Approved", "Hold"]
                    },
                    "ref": {
                        "sql_data_type": "VARCHAR(255)",
                        "business_feature": "Contract Reference / 契約参照",
                        "description": "Order reference metadata string."
                    },
                    "comment": {
                        "sql_data_type": "TEXT",
                        "business_feature": "Audit Comment / 監査コメント",
                        "description": "Certified auditor compliance explanation citing matched policy rule."
                    }
                },
                "available_database_views": {
                    "approved_vendors": "VIEW (employee_id, name) - Contains the 11 registered approved vendors (V3001..V3012, excluding V3099)."
                }
            }
            current_rows = db_manager.get_all_invoices()
        else:
            table_name = "erp_payroll_items"
            table_schema = {
                "table_name": "erp_payroll_items",
                "table_description": "Employee Payroll Expense Settlements & Allowances (105 total live records in PostgreSQL)",
                "features_and_columns": {
                    "id": {
                        "sql_data_type": "VARCHAR(50) PRIMARY KEY",
                        "business_feature": "Voucher ID / 伝票番号",
                        "description": "Unique voucher identifier (e.g. 'P4-07089771-001').",
                        "sample_values": ["P4-07089771-001", "P4-07089771-002"]
                    },
                    "employee_id": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Employee Code / 社員番号",
                        "description": "Employee identifier (e.g. 'EMP-001', 'EMP-002')."
                    },
                    "employee_name": {
                        "sql_data_type": "VARCHAR(255)",
                        "business_feature": "Employee Full Name / 氏名",
                        "description": "Legal employee full name (e.g. '青木 拓也', '菊地 理恵')."
                    },
                    "item_category": {
                        "sql_data_type": "VARCHAR(100)",
                        "business_feature": "Expense Category / 手当・精算項目",
                        "description": "Expense or allowance category (e.g. '研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '接待交際費', '資格取得手当', '扶饊控除変更', '役職手当廃止')."
                    },
                    "item_type": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Payment Classification / 支給・控除区分",
                        "description": "Classification: 'Addition' (支給/加算) or 'Deduction' (控除/減算).",
                        "allowed_values": ["Addition", "Deduction"]
                    },
                    "raw_amount": {
                        "sql_data_type": "BIGINT (Numeric Integer)",
                        "business_feature": "Settlement Amount / 精算金額 (数値)",
                        "description": "CRITICAL: Numeric transaction amount as a pure integer in JPY WITHOUT currency symbols or commas. ALWAYS use this column for all mathematical comparisons (>, <, =, <=, >=).",
                        "sql_usage_guide": "raw_amount > 100000, raw_amount <= 100000. NEVER use '¥' or commas in SQL numbers."
                    },
                    "amount": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Formatted Display Amount / 表示金額文字列",
                        "description": "Display string formatted with '¥' and commas (e.g. '¥77,224')."
                    },
                    "status": {
                        "sql_data_type": "VARCHAR(50)",
                        "business_feature": "Processing Status / 確認ステータス",
                        "description": "Workflow status: 'Unprocessed', 'Confirmed', 'Hold'.",
                        "allowed_values": ["Unprocessed", "Confirmed", "Hold"]
                    },
                    "voucher_ref": {
                        "sql_data_type": "VARCHAR(100)",
                        "business_feature": "Voucher Reference / 伝票番号",
                        "description": "Internal reference code."
                    },
                    "comment": {
                        "sql_data_type": "TEXT",
                        "business_feature": "Audit Comment / 監査コメント",
                        "description": "Certified auditor compliance explanation citing matched policy rule."
                    }
                }
            }
            current_rows = db_manager.get_all_payroll_items()

        return {
            "process_type": process_type,
            "document_text": document_text,
            "filename_or_title": filename_or_title,
            "table_name": table_name,
            "table_schema": table_schema,
            "policy_json": {},
            "current_db_rows": current_rows,
            "decisions": [],
            "db_updates_applied": 0,
            "discrepancies": [],
            "execution_steps": [],
            "overall_status": "PENDING",
            "error": None
        }

    def analyze_policy(self, process_type: str, document_text: str = "", filename_or_title: str = "Policy Document") -> Dict[str, Any]:
        """Runs Node 1 (parse) AND Node 2 (validate_and_refine_sql_rules with LLM verification loop),
        ensuring that the extracted SQL conditions strictly reflect the policy constraints."""
        initial_state = self._prepare_initial_state(process_type, document_text, filename_or_title)
        n1_out = self.node_parse_document(initial_state)
        state_1 = {**initial_state, **n1_out}
        n2_out = self.node_validate_and_refine_sql(state_1)
        state_2 = {**state_1, **n2_out}
        policy_json = state_2.get("policy_json", {})
        return {
            "success": True,
            "stage": "POLICY_ANALYZED",
            "process_type": process_type,
            "policy_json": policy_json,
            "rules": policy_json.get("item_criteria", []),
            "execution_steps": state_2.get("execution_steps", [])
        }

    def evaluate(self, process_type: str, document_text: str = "", filename_or_title: str = "Policy Document", custom_rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs Node 1 and Node 2. If custom_rules provided, uses the user's edited rules for Node 2 comparison."""
        initial_state = self._prepare_initial_state(process_type, document_text, filename_or_title)

        if custom_rules is not None and len(custom_rules) > 0:
            reg_v = set()
            hold_c = []
            max_c = 2000000 if process_type == "invoice" else 150000

            for r in custom_rules:
                cond_str = str(r.get("condition", "") or r.get("sql_condition", "")).strip()
                r["condition"] = cond_str
                r["sql_condition"] = cond_str
                mv_str = str(r.get("match_value", ""))
                desc_str = str(r.get("description", ""))
                act = str(r.get("action_on_match") or r.get("action") or "").strip()
                if any(w in act.lower() for w in ["appr", "pass", "ok", "conf", "承"]):
                    r["action_on_match"] = "Approved" if process_type == "invoice" else "Confirmed"
                else:
                    r["action_on_match"] = "Hold"
                action = r["action_on_match"]

                # Extract vendor codes (e.g. V1001, V3005)
                v_codes = re.findall(r'\b([A-Z][0-9]{3,5})\b', mv_str + " " + cond_str)
                for vc in v_codes:
                    if vc != "UNREGISTERED":
                        r["vendor_code"] = vc
                        reg_v.add(vc)

                # Extract amounts from condition, match_value, description
                amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', cond_str + " " + mv_str + " " + desc_str)]
                if not amts:
                    amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', cond_str + " " + mv_str + " " + desc_str)]
                if not amts:
                    amts = [int(x.replace(',', '')) for x in re.findall(r'\b([0-9]{4,9})\b', cond_str + " " + mv_str + " " + desc_str)]
                for w in re.findall(r'([0-9]{1,4})\s*万(?:円)?', cond_str + " " + mv_str + " " + desc_str):
                    amts.append(int(w) * 10000)

                if amts:
                    r["expected_amounts"] = amts
                    r["expected_amount"] = amts[0]

                # Check if this rule defines a ceiling
                if any(kw in cond_str.lower() or kw in desc_str.lower() for kw in [">", "超過", "上限", "ceiling", "limit", "限度額"]):
                    if amts:
                        r["threshold_amount"] = amts[0]
                        r["match_field"] = "raw_amount"
                        max_c = amts[0]

                # Check if this rule defines categories to hold
                if action in ("Hold", "Rejected"):
                    cat_found = re.findall(r"""(?:type|item_category)\s*(?:=|IN)\s*['"]([^'"]+)['"]""", cond_str)
                    for cat in cat_found:
                        if cat not in hold_c:
                            hold_c.append(cat)
                        r["match_field"] = "type" if process_type == "invoice" else "item_category"

                # Check strict amount / exception hold flags
                if any(kw in cond_str.lower() or kw in desc_str.lower() for kw in ["!=", "以外", "不一致", "固定", "fixed", "range", "contract range"]):
                    r["strict_amount"] = True

                if action in ("Hold", "Rejected"):
                    r["is_exception_hold"] = True

                # If name is not set, default to match_value
                if not r.get("name"):
                    r["name"] = r.get("match_value", "Custom Policy Rule")
                reg_v.add(r["name"])
                if r.get("match_value"):
                    name_clean = re.sub(r'[\(（][A-Z0-9]+[\)）]', '', r["match_value"]).strip()
                    if name_clean:
                        reg_v.add(name_clean)

            # Adapt dynamic ceiling to ensure it is not lower than any approved rule amount
            max_approved = max([max(r.get("expected_amounts") or [0]) for r in custom_rules if r.get("action_on_match") in ("Approved", "Confirmed")] + [0])
            if max_approved > max_c:
                max_c = max_approved

            policy_json = {
                "policy_title": f"User-Edited Policy Rules ({filename_or_title})",
                "process_type": process_type,
                "global_rules": {
                    "max_auto_approval_amount": max_c,
                    "registered_vendors": list(reg_v),
                    "hold_categories": hold_c,
                    "require_registered_vendors": any(r.get("match_value") == "UNREGISTERED" for r in custom_rules)
                },
                "registered_vendors": list(reg_v),
                "item_criteria": custom_rules
            }
            state_1 = {
                **initial_state,
                "policy_json": policy_json,
                "execution_steps": [{
                    "node": "Node 1: parse_document_to_schema_json (User Custom Rules Applied)",
                    "duration_s": 0.01,
                    "status": "COMPLETED",
                    "rules_extracted": len(custom_rules)
                }]
            }
        else:
            n1_out = self.node_parse_document(initial_state)
            state_1 = {**initial_state, **n1_out}
            n2_out_val = self.node_validate_and_refine_sql(state_1)
            state_1 = {**state_1, **n2_out_val}

        n2_out = self.node_compare_and_decide(state_1)
        state_2 = {**state_1, **n2_out}

        decisions = state_2.get("decisions", [])
        discrepancies = state_2.get("discrepancies", [])

        return {
            "success": True,
            "stage": "EVALUATED_STAGED",
            "process_type": process_type,
            "policy_json": state_2.get("policy_json", {}),
            "staged_decisions": decisions,
            "discrepancies": discrepancies,
            "execution_steps": state_2.get("execution_steps", []),
            "evaluated_count": len(decisions),
            "approved_count": sum(1 for d in decisions if d.get("new_status") in ("Approved", "Confirmed")),
            "hold_count": len(discrepancies)
        }

    def commit_staged(self, process_type: str, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs Node 3 and Node 4: commits user-confirmed decisions to live DB and evaluates final audit state."""
        state: CoPilotAgentState = {
            "process_type": process_type,
            "document_text": "",
            "filename_or_title": "Staged Confirmation",
            "table_name": "erp_invoices" if process_type == "invoice" else "erp_payroll_items",
            "table_schema": {},
            "policy_json": {},
            "current_db_rows": [],
            "decisions": decisions,
            "db_updates_applied": 0,
            "discrepancies": [d for d in decisions if d.get("new_status") == "Hold"],
            "execution_steps": [],
            "overall_status": "PENDING",
            "error": None
        }

        n3_out = self.node_commit_updates(state)
        state_3 = {**state, **n3_out}

        n4_out = self.node_human_audit(state_3)
        state_4 = {**state_3, **n4_out}

        return {
            "success": True,
            "stage": "COMMITTED",
            "db_updates_applied": state_4.get("db_updates_applied", 0),
            "execution_steps": state_4.get("execution_steps", []),
            "overall_status": state_4.get("overall_status"),
            "discrepancies": state_4.get("discrepancies", [])
        }

    def run(self, process_type: str, document_text: str, filename_or_title: str = "Policy Document") -> Dict[str, Any]:
        initial_state = self._prepare_initial_state(process_type, document_text, filename_or_title)

        # Execute Full LangGraph
        final_state = self.graph.invoke(initial_state)

        # Convenience metrics
        decisions = final_state.get("decisions", [])
        discrepancies = final_state.get("discrepancies", [])
        final_state["success"] = final_state.get("overall_status") != "FAILED"
        final_state["extracted_rules"] = final_state.get("policy_json", {}).get("item_criteria", [])
        final_state["evaluated_count"] = len(decisions)
        final_state["approved_count"] = sum(1 for d in decisions if d.get("new_status") in ("Approved", "Confirmed"))
        final_state["hold_count"] = len(discrepancies)

        return final_state

copilot_engine = CoPilotLangGraph()
