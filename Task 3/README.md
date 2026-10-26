# Task 3: Automated Enterprise Web ERP, Multi-Process Autonomous Decision Agent, Office Ingestion & Cloud Persistence

**Step 3 of Intern Selection Challenge**: *Design, engineer, and deploy a production-grade, interactive enterprise web ERP portal featuring an autonomous AI Co-Pilot capable of ingesting arbitrary natural language business policies, converting them dynamically into executable SQL logic without hardcoding, auditing enterprise database records with sub-second latency, integrating multi-modal document intelligence with native OS file exploration, and persisting all state into an industrial cloud database.*

---

## 1. System Architecture Overview

Task 3 delivers a complete, end-to-end enterprise solution bridging unstructured human business policies with deterministic relational database execution.

```mermaid
flowchart TD
    subgraph UI["Interactive Web ERP Frontend (Port 5135)"]
        User["Human Operator / Auditor"]
        ERP["Core ERP Tables View<br>• 🏛️ 財務会計 (Invoices)<br>• 👥 HR人事給与 (Payroll Items)<br>• 📋 有給・休暇申請 (Leave Applications)"]
        CoPilotUI["Enterprise Co-Pilot Panel<br>• Tab 1: 規程 (Regulations)<br>• Tab 2: 規程マスタ (Regulation Master)<br>• Fused Stepper & Execution Strip<br>• Dynamic Scroll Rules Table (top: 0)"]
        SchemaModal["ℹ️ Database Schema Inspector Modal<br>(Field Types, Constraints, Accepted Formats)"]
    end

    subgraph LangGraph["5-Node LangGraph Autonomous Agent Engine"]
        N1["Node 1: parse_document_to_schema_json<br>• Ingest Word .docx / Excel .xlsx / Text<br>• Extract Structured Rules JSON"]
        N2["Node 2: validate_and_refine_sql_rules<br>• Case-insensitive LOWER() wrapping<br>• Column catalog verification & AST sanitization"]
        N3["Node 3: compare_features_and_decide<br>• Parameterized SQL query execution<br>• Strict Hold-Precedence reconciliation"]
        N4["Node 4: commit_database_updates<br>• Atomic PostgreSQL / SQLite commit<br>• Status update & Audit commentary logging"]
        N5["Node 5: human_in_the_loop_audit<br>• Flagged discrepancy triage<br>• Single-use cryptographic dispatch tokens"]
    end

    subgraph LLM["LLM Policy-to-SQL Compiler"]
        PuterDriver["Puter.js AI Client<br>(gpt-4o-mini / deepseek-chat)"]
        OpenRouterDriver["OpenRouter Free Models Alone<br>(:free suffix models, $0.00 cost)"]
        CreditsService["Real Account Credits Telemetry<br>(Session call counter & quota tracking)"]
    end

    subgraph DB["Dual-Engine Persistence Layer"]
        SupabaseCloud[("PostgreSQL Supabase Cloud Pooler<br>aws-0-ap-northeast-1.pooler.supabase.com:5432")]
        LocalSQLite[("Local SQLite Mirror<br>erp_unified.db")]
        Validator["Excel / CSV Schema Validator & Flagger<br>(Header verification & data type enforcement)"]
    end

    subgraph DocAI["Multi-Modal Document AI & Native OS Integration"]
        OCR["Tesseract OCR Engine (jpn+eng)<br>Medical & Municipal Certificate Extractor"]
        WinExplorer["Native Windows Explorer Bridging<br>(explorer /select <absolute_path>)"]
    end

    User <--> ERP
    User <--> CoPilotUI
    CoPilotUI <--> N1
    N1 --> N2 --> N3 --> N4 --> N5
    N1 <--> PuterDriver
    N1 <--> OpenRouterDriver
    PuterDriver <--> CreditsService
    N3 <--> SupabaseCloud
    N3 <--> LocalSQLite
    N4 --> SupabaseCloud
    N4 --> LocalSQLite
    ERP <--> Validator
    ERP <--> DocAI
    DocAI <--> WinExplorer
    ERP <--> SchemaModal
```

---

## 2. Candidate Selection & Prioritization Rationale

From the empirical analysis of **158 validated business process executions** in Dataset B (profiled and scored in Task 2 using the **Industrial Automation Suitability Index (IASI)**), we identified and selected the core candidates to build the automation.

### Candidate Portfolio Ranking Matrix

| Rank | Candidate Process Family | Japanese Domain | Cases | Total Work Time | Mean Cycle | Determinism | Stability | Feasibility | ROI Priority Score | Projected Annual Savings | Automation Recommendation & Role in Task 3 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **#1** | **`Invoice & Accounts Payable`** | 財務会計・請求書処理 | **59** | **31.4 min** | **31.9s** | **9.5 / 10** | **9.2 / 10** | **93.7%** | **164.49** | **~520 hrs/yr** | **PRIMARY AUTOMATION SELECTION**<br>High-volume deterministic 3-way matching pipeline. |
| **#2** | **`Batch Order Fulfillment`** | 出荷・在庫引当・受注管理 | **20** | **26.9 min** | **80.7s** | **8.9 / 10** | **8.6 / 10** | **87.7%** | **123.46** | **~440 hrs/yr** | **SECONDARY BATCH CANDIDATE**<br>High-volume inventory and shipping dispatch. |
| **#3** | **`Leave Application Review`** | 有給・休暇申請管理 | **22** | **31.2 min** | **85.2s** | **8.2 / 10** | **8.0 / 10** | **81.1%** | **122.93** | **~380 hrs/yr** | **INTERACTIVE CO-PILOT SELECTION**<br>Multi-modal Document AI + Human-in-the-loop audit. |
| **#4** | **`Employee Onboarding`** | 社員入社・人事異動台帳 | **12** | **16.3 min** | **81.7s** | **7.5 / 10** | **7.8 / 10** | **76.3%** | **57.33** | **~240 hrs/yr** | Variable contract document formats. |
| **#5** | **`Social Insurance Admin`** | 社会保険・年金届出 | **14** | **15.8 min** | **67.9s** | **8.0 / 10** | **7.5 / 10** | **77.8%** | **57.00** | **~210 hrs/yr** | Periodic / monthly batch filing. |
| **#6** | **`Payroll Deductions`** | 給与・控除・経費整備 | **13** | **11.2 min** | **51.7s** | **8.8 / 10** | **8.5 / 10** | **86.7%** | **50.27** | **~190 hrs/yr** | **INTEGRATED HR SUITE**<br>Monthly discrete payroll adjustment reconciliation. |
| **#7** | **`Purchase Orders & Approvals`** | 購買発注・稟議承認 | **11** | **13.1 min** | **71.2s** | **7.8 / 10** | **7.0 / 10** | **74.4%** | **42.75** | **~160 hrs/yr** | Supplier negotiations & capex checks. |
| **#8** | **`Resident Tax Admin`** | 住民税特別徴収・改定 | **7** | **4.8 min** | **40.7s** | **8.5 / 10** | **7.5 / 10** | **80.5%** | **18.17** | **~75 hrs/yr** | Lowest transactional volume. |

---

### Why We Chose These Candidates for Task 3

#### 1. Why Rank #1 (Invoice & Accounts Payable) was chosen as the Primary Core Automation:
1. **Dominant Transaction Volume**: Invoices accounted for **59 out of 158 executions (37.3%)** across Dataset B operators, representing the highest operational overhead in the enterprise.
2. **Pure Mathematical Determinism (Score: 9.5 / 10)**: 
   - 3-Way Matching between Purchase Order (`PO-2026-XXXX`) and Invoice (`INV-2026-XXXX`).
   - Japanese Consumption Tax calculation: $T = \lfloor A_{\text{subtotal}} \times 0.10 \rfloor$.
   - Whitelist vendor checks and monetary threshold ceilings ($\le ¥1,000,000$ or $¥2,000,000$).
3. **Elimination of Severe Human Copy-Paste Fatigue**: Operators executed an average of 16.8 keystrokes, 11.5 mouse clicks, and 2.0 clipboard transfers per case between Word contracts and the ERP portal.
4. **Deterministic SQL Latency Advantage**: Compiling policies into parameterized SQL evaluates rows in **3.4 milliseconds**, compared to **3,200 ms** for a raw LLM agent (1,000x faster, $0.00 marginal cost, 100% arithmetic accuracy).

#### 2. Why Rank #3 (Leave Application Review) was chosen for Interactive Multi-Modal Document AI:
1. **High Cognitive Burden of Document Verification**: Unlike numerical invoice ledgers, leave requests depend on unstructured external certificates (hospital doctor certificates, birth registrations, funeral invitations).
2. **Human Discretion Mandate**: Full automated approval without human oversight risks labor compliance violations. It requires an **interactive Co-Pilot** that extracts facts with OCR, verifies them against policy rules, presents findings in an audit commentary drawer, and lets human supervisors inspect the original file with one click.
3. **Native OS Bridging Requirement**: Operators in Dataset B constantly switch between browser forms and Windows file folders. Integrating native Windows Explorer opening (`explorer /select <file>`) bridges the physical gap between row data and local attachment files.

#### 3. How Rank #2 (Batch Order Fulfillment) and Rank #6 (Payroll Items) Integrate:
- `Batch Order Fulfillment` represents continuous warehouse shipments, while `Payroll Items` (`erp_payroll_items`) represents monthly discrete compensation deductions. Both share the normalized tabular structure and are fully supported by our dual-suite ERP portal.

---

## 3. LangGraph State Graph Architecture & Node Workflow

Task 3 coordinates autonomous policy compilation and database execution via a **5-Node Cyclic LangGraph State Graph** (`copilot_langgraph_engine.py`):

```mermaid
flowchart TD
    Start([User Uploads Policy Doc / Pastes Rules]) --> N1["Node 1: parse_document_to_schema_json<br>• Extracts rules from Word (.docx), Excel (.xlsx), or text<br>• Uses LLM to produce JSON AST without hardcoding"]
    
    N1 --> N2["Node 2: validate_and_refine_sql_rules<br>• Sanitizes SQL predicates<br>• Wraps text comparisons with LOWER()<br>• Validates column existence against live DB catalog"]
    
    N2 --> N3["Node 3: compare_features_and_decide<br>• Executes parameterized SELECT queries on DB<br>• Evaluates rows against AST policy<br>• Applies STRICT Hold-Precedence"]
    
    N3 --> N4["Node 4: commit_database_updates<br>• Commits 'Approved' or 'On Hold' to DB<br>• Writes timestamped audit comments<br>• Logs execution trace"]
    
    N4 --> N5["Node 5: human_in_the_loop_audit<br>• Renders flagged discrepancies in UI drawer<br>• Provides one-click human override<br>• Issues cryptographic single-use dispatch token"]
    
    N5 --> End([Audit Complete & Persisted in Cloud DB])

    N2 -.-> |Syntax Error Detected| N1
    N3 -.-> |Missing Column Detected| N2
```

### State Graph Schema (`CoPilotAgentState`)

```python
class CoPilotAgentState(TypedDict):
    process_type: str                     # "invoice", "payroll", or "leave"
    document_text: str                    # Raw text from Word / pasted memo / rules
    filename_or_title: str                # Source document name
    table_name: str                       # "erp_invoices", "erp_payroll_items", "erp_leave_applications"
    table_schema: Dict[str, Any]          # Catalog of column names & SQLite/PostgreSQL data types
    policy_json: Dict[str, Any]           # Extracted rule tree (whitelist, ceilings, conditions)
    current_db_rows: List[Dict[str, Any]] # Live database records loaded for evaluation
    decisions: List[Dict[str, Any]]       # Per-row evaluation verdict, matched rule ID, audit comment
    db_updates_applied: int               # Count of atomic row updates persisted
    discrepancies: List[Dict[str, Any]]   # Items flagged for human supervisor review
    execution_steps: List[Dict[str, Any]] # Chronological execution telemetry and latencies
    overall_status: str                   # "SUCCESS" / "NEEDS_INTERVENTION" / "ERROR"
    error: Optional[str]                  # Traceback or error details if failure occurred
```

### In-Depth Node Descriptions

1. **`parse_document_to_schema_json`**:
   - Ingests freeform Japanese or English text, `.docx` binary paragraphs/tables, or `.xlsx` workbooks.
   - Prompts the LLM (via Puter or OpenRouter) with the live database catalog schema.
   - Synthesizes a structured JSON AST containing policy title, vendor whitelist, monetary caps, transaction type rules, and discrepancy conditions.
2. **`validate_and_refine_sql_rules`**:
   - Prevents SQL syntax errors and schema mismatches.
   - Converts case-sensitive comparisons into ANSI SQL `LOWER(column) = LOWER('value')`.
   - Strips dangerous SQL keywords (`DROP`, `DELETE`, `UPDATE`, `;`) ensuring read-only query evaluation.
3. **`compare_features_and_decide`**:
   - Queries the active database (PostgreSQL Supabase or SQLite) using parameterized SELECT queries.
   - Reconciles every record against the policy rules.
   - **Strict Hold Precedence Guarantee**: If a record matches an "Approve" condition (e.g. amount $\le ¥1,000,000$) but triggers a "Hold" condition (e.g. unlisted vendor or `Adjustment` type), the "Hold" rule **strictly overrides**, safeguarding corporate compliance.
4. **`commit_database_updates`**:
   - Executes atomic SQL `UPDATE` operations: modifies status from `Unprocessed` to `Approved` or `On Hold`.
   - Appends audit reconciliation notes (e.g. `「IT業務委託契約・検収完了及び月次予算枠内確認済」`).
   - Persists state synchronously to the cloud PostgreSQL database and mirrors locally.
5. **`human_in_the_loop_audit`**:
   - Displays discrepancy cards in the ERP UI with red/amber badges.
   - Enables human operators to inspect the evidence, click on audit comments, or trigger manual approvals.
   - Implements single-use cryptographic tokens (`active_dispatch_tokens.json`) to prevent accidental repeat execution upon browser reload.

---

## 4. Converting Natural Language User Queries to SQL

A core architectural breakthrough in Task 3 is the **Zero-Hardcoding Natural Language Policy-to-SQL Compiler** (`llm_policy_sql_engine.py`).

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant UI as ERP Web Co-Pilot
    participant LLM as Puter / OpenRouter LLM
    participant AST as SQL AST Validator
    participant DB as PostgreSQL Supabase

    User->>UI: Paste regulation text or upload Word/Excel doc
    UI->>DB: Introspect current table schema & sample rows
    DB-->>UI: Return columns: id, name, raw_amount, type, status...
    UI->>LLM: Prompt with Schema Grounding + User Policy
    Note over LLM: LLM translates natural language rules<br/>into valid PostgreSQL SELECT queries
    LLM-->>UI: Return Structured Rules JSON with SQL Predicates
    UI->>AST: Validate & Sanitize SQL (Case-insensitivity, anti-injection)
    AST-->>UI: Clean parameterized queries
    UI->>DB: Execute SELECT id, raw_amount FROM erp_invoices WHERE ...
    DB-->>UI: Return matched row IDs
    Note over UI: Apply Strict Hold Precedence & evaluate discrepancies
    UI->>DB: Atomic COMMIT: UPDATE erp_invoices SET status='...', audit_comment='...'
    DB-->>UI: Commit Confirmed
    UI-->>User: Render live updated table + audit comments
```

### The 4-Stage Query-to-SQL Transformation

#### Stage 1: Live Schema Grounding Prompt
The engine inspects the target table at runtime and constructs a schema-grounded prompt:
```text
Table: erp_invoices
Columns:
- id (VARCHAR): Voucher ID (e.g. 'P6-07010448-001')
- name (VARCHAR): Vendor legal name (e.g. 'Yamada Manufacturing Co., Ltd.')
- raw_amount (INTEGER): Invoiced amount in JPY (e.g. 385000)
- type (VARCHAR): Processing Category ('Routine' or 'Adjustment')
- status (VARCHAR): Workflow state ('Unprocessed', 'Approved', 'On Hold')

Task: Convert the policy document into valid PostgreSQL SELECT queries identifying
which records to approve and which to hold.
```

#### Stage 2: Structured JSON AST Output
The LLM returns a structured JSON payload rather than unconstrained raw SQL:
```json
{
  "policy_title": "月次定額保守取引先契約運用基準",
  "rules": [
    {
      "rule_id": "RULE-INV-01",
      "target_action": "hold",
      "comment": "未登録取引先・個別契約精査保留",
      "sql_query": "SELECT id FROM erp_invoices WHERE vendor_code NOT IN ('V3001', 'V3002', 'V3005')"
    },
    {
      "rule_id": "RULE-INV-02",
      "target_action": "hold",
      "comment": "予算上限150万円超過・役員決裁要保留",
      "sql_query": "SELECT id FROM erp_invoices WHERE raw_amount > 1500000"
    },
    {
      "rule_id": "RULE-INV-03",
      "target_action": "approve",
      "comment": "月次契約予算内・定常検収自動承認",
      "sql_query": "SELECT id FROM erp_invoices WHERE type = 'Routine' AND raw_amount <= 1500000 AND vendor_code IN ('V3001', 'V3002', 'V3005')"
    }
  ]
}
```

#### Stage 3: SQL Sanitization & Case Normalization
Before execution, `validate_and_refine_sql_rules` wraps string columns with `LOWER()` and ensures ANSI compliance:
$$\text{WHERE } \text{LOWER}(\text{type}) = \text{LOWER}('Routine') \text{ AND } \text{raw\_amount} \le 1500000$$

#### Stage 4: Deterministic Dynamic Comparator
The comparator applies an exact mathematical reconciliation:
1. Every row matching a `hold` query is flagged with status `On Hold`.
2. Every row matching an `approve` query is marked `Approved` **if and only if** it has zero active `hold` flags.
3. Any unmapped row or boundary outlier is captured by the catch-all `discrepancy_query` and flagged for human intervention.

---

## 5. Advanced Features & Enterprise Capabilities

### 1. Dual-Engine Cloud Persistence (PostgreSQL Supabase + SQLite)
- **Cloud Database**: Directly connected to Supabase PostgreSQL cluster (`aws-0-ap-northeast-1.pooler.supabase.com:5432`) with connection pooling and SSL encryption.
- **Local Fallback Mirror**: Automatically mirrors all updates to local SQLite (`erp_unified.db`). If internet connectivity drops, transactions continue seamlessly without user interruption.
- **Connection Testing Endpoint**: `/api/database/test-connection` provides immediate health checks for both database engines.

### 2. Interactive Database Schema Inspector (`ℹ️` Modal)
- Located directly beside the database status indicator in the top navigation bar.
- Clicking the `ℹ️` button opens an interactive modal displaying:
  - Table schemas (`erp_invoices`, `erp_payroll_items`, `erp_leave_applications`)
  - Accepted column names, data types, nullability, and primary keys
  - Valid range specifications and format requirements (e.g. numeric integer amounts, ISO dates `YYYY-MM-DD`).

### 3. Strict Excel / CSV Schema Validation Flagging
- Proactive validation prevents corrupted or malformed data files from polluting the database.
- Uploads to `/api/upload-table-data` and `/api/import-excel` are checked against the target schema:
  - Verifies presence of mandatory columns (`id`, `employee_id`, `name`, `amount`).
  - Verifies numeric types (rejects negative numbers or alphabetical characters in amount fields).
  - Returns descriptive HTTP 400 JSON errors detailing exactly which columns failed validation, guiding the user on how to correct the file.

### 4. Real Puter Account Credits & Quota Telemetry
- Endpoint `/api/llm/account-credits` queries live session state and Puter API quota.
- Returns remaining free-tier calls (out of 500), total session tokens consumed, and real-time percentage indicators.
- Prevents sudden API credit exhaustion by warning operators when quotas run low.

### 5. Multi-Modal Document AI & Native Windows Explorer Integration
- **Document AI (`leave_doc_ai_pipeline.py`)**:
  - Leverages Tesseract OCR (`jpn+eng`) to extract text from medical diagnosis certificates, birth certificates, and bereavement letters.
  - Automatically compares patient names with employee names in the database.
  - Detects official hospital / physician seals (`hospital_stamp_detected`).
  - Validates requested leave duration against the physician's recommended rest period.
- **Windows Explorer Bridging (`/api/open-explorer`)**:
  - Clicking the document link in the ERP portal executes `explorer.exe /select, <absolute_file_path>`.
  - Windows Explorer immediately pops up on the host system and highlights the exact physical certificate in `pulled_tmi/attachments/`, ensuring complete alignment between database metadata and physical documents.

### 6. Space-Efficient, Fused UI Design & Dynamic Scroll Mechanics
- **Sticky Table Headers (`table.rules-table th`)**: Headers dock cleanly at `top: 0` (`z-index: 5`) with a subtle drop shadow, completely eliminating the bug where headers floated in the middle of data rows.
- **Dynamic Vertical Scroll**: Parent container `#llm-rules-content` is vertically scrollable (`overflow-y: auto`). As the user scrolls down, the upper action bars roll up smoothly, maximizing visible vertical space for the rules table at the bottom.
- **Shortened Workspace Tabs**: Notepad (`📋`) and Excel (`📊`) icons removed; renamed to clean, professional labels: `規程 (Regulations)` and `規程マスタ (Regulation Master)`.
- **Streamlined Database Toolbar**: Removed the Excel icon from `一括取込 (Bulk Import)`.

---

## 6. Empirical Benchmarks & Verification Metrics

### Master Evaluation Summary (30 Enterprise Rule Sets on 3,150 Live Records)

Documented in full in [`results/benchmark_metrics_report.md`](./results/benchmark_metrics_report.md):

| Suite | Table | Rule Sets | Records / Run | Total Evaluations | SQL Syntax Validity | Hold Integrity | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Financial Invoices** | `erp_invoices` | 10 | 105 | 1,050 | 100% PASS | 100% PASS | **ALL PASS** |
| **Payroll Deductions** | `erp_payroll_items` | 10 | 105 | 1,050 | 100% PASS | 100% PASS | **ALL PASS** |
| **Leave Management** | `erp_leave_applications` | 10 | 105 | 1,050 | 100% PASS | 100% PASS | **ALL PASS** |
| **Combined Total** | **Supabase PostgreSQL** | **30** | **105** | **3,150** | **100% PASS (0 err)** | **100% PASS (0 viol)** | **100% PASS** |

### Execution Latency & Efficiency Benchmark

| Architecture / Execution Paradigm | Modality | Cycle Time / Case | Latency | Precision | Token Cost / 1k Tx |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Human Baseline (Dataset B)** | Manual Desktop Entry | 57.2s | 57,200 ms | 94.2% | $0.00 (Labor $25/hr) |
| **Architecture 1: Client Node/React Hub** | Puter.js in Browser | 3.20s | 3,200 ms | 68.4% | $0.00 (Quota-limited) |
| **Architecture 2: Pure LLM Policy-to-SQL** | Prompt-only SQL compile | 4.85s | 4,850 ms | 74.2% | $4.50 (Remote tokens) |
| **Architecture 3: Monolithic Regex Baseline** | Static regex rules | 0.01s | 10 ms | 82.5% | $0.00 (Rigid/Hardcoded) |
| **Architecture 4: Task 3 LangGraph + Parameterized SQL** | **Word/Excel + AST SQL** | **0.42s** | **3.4 ms** | **100.0%** | **$0.00 (Free Puter quota)** |

---

## 7. Quickstart Guide: Running Task 3

### Prerequisites
- Python 3.10+ (Anaconda Python recommended on Windows).
- Required packages: `flask`, `psycopg2-binary`, `python-docx`, `openpyxl`, `langgraph`, `requests`, `pytesseract`.

Navigate to the `Task 3` directory:
```bash
cd "c:\Users\KISHORE S\Desktop\pulled_tmi\Task 3"
```

### 1. Launch the Live Web ERP Portal with AI Co-Pilot (`--serve`)
```bash
python run_task3.py --serve
```
Access the application in your browser: **[http://127.0.0.1:5135/](http://127.0.0.1:5135/)**

### 2. Run Comprehensive System Verification Suite (`--verify`)
Validates all 7 core features (Database connection, UI elements, account credits, Windows Explorer integration, CSV validation flagging, Leave Document AI):
```bash
python run_task3.py --verify
```

### 3. Run UI Spec & Dynamic Scroll Audit (`--verify-ui`)
Verifies table header sticky behavior (`top: 0`), icon removals, shortened tab labels, and vertical scroll layout:
```bash
python run_task3.py --verify-ui
```

### 4. Run 30-Policy Dynamic SQL Benchmark (`--benchmark`)
Executes all 30 enterprise policy sets against live PostgreSQL Supabase tables:
```bash
python run_task3.py --benchmark
```

---

## 8. Directory & File Reference

```
Task 3/
├── README.md                                      # This Master Architecture & User Guide
├── WORKLOG.md                                     # Exhaustive Date & Time Engineering Worklog
├── run_task3.py                                   # Universal CLI Runner (--serve, --verify, --benchmark, --verify-ui)
│
├── code files/                                    # [Complete Source Code]
│   ├── unified_copilot_erp_app.py                 # Unified ERP Web App & Co-Pilot Server (Flask)
│   ├── copilot_langgraph_engine.py                # 5-Node LangGraph State Graph Agent Engine
│   ├── llm_policy_sql_engine.py                   # Zero-Hardcoding LLM Policy-to-SQL Compiler
│   ├── leave_doc_ai_pipeline.py                   # Multi-Modal Leave Document AI & OCR Pipeline
│   ├── erp_db.py                                  # Dual-Engine Database Manager (PostgreSQL + SQLite)
│   ├── generate_100_benchmarks.py                 # Ground-truth synthetic enterprise benchmark generator
│   ├── test_all_features.py                       # 7/7 System Integration Test Suite
│   ├── verify_ui_spec.py                          # UI spec and dynamic scroll verification
│   ├── test_complete_dynamic_logic.py             # 30-policy live database benchmark runner
│   ├── test_cases_leave_doc.py                    # Multi-modal Leave Document AI test cases
│   ├── test_doc_to_sql.py                         # Policy-to-SQL prompt & parsing unit test
│   ├── verify_clean_app.py                        # App syntax and route auditor
│   ├── verify_live_sql.py                         # Live SQL verification suite
│   ├── verify_live_payroll_sql.py                 # Live Payroll SQL verification suite
│   └── verify_zero_hardcoding.py                  # Zero-hardcoding compliance auditor
│
├── results/                                       # [Deliverables, Benchmarks & Metrics]
│   ├── benchmark_metrics_report.md                # 653-line Comprehensive 30-Rule-Set Live Benchmark Report
│   ├── benchmark_evaluation_summary.json          # Machine-readable evaluation metrics (Accuracy, Latency, Precision)
│   ├── test_cases_summary.json                    # Detailed test case definitions and assertions
│   ├── leave_document_ai_benchmarks.json          # Document AI OCR and Leave attachment scorecard
│   └── execution_latency_comparison.csv           # Latency metrics: Deterministic SQL vs Pure LLM
│
└── artifacts/                                     # [Sample Data & Master Regulations]
    ├── doc2_text.txt                              # Master demo Japanese regulations document
    ├── master_regulations.json                    # Editable regulation master seed data
    └── schema_definitions.json                    # Formal normalized database catalog definitions
```

---

## Author & Contact
- **Author**: Kishore S (Roll Number: 24123017, IIT Roorkee)  
- **Role**: Forward Deployed Engineer (FDE) Candidate
