# Engineering Worklog — Task 3: Automated Enterprise Web ERP, Multi-Process Autonomous Decision Agent, Office Ingestion & Cloud Persistence

**Author**: Kishore S (Roll Number: 24123017, IIT Roorkee)  
**Role**: Forward Deployed Engineer (FDE) Candidate  
**Target Repository**: `pulled_tmi/Task 3`  
**Reference Trials & Data Analysis Pipeline Chat**:  
- `C:\Users\KISHORE S\Desktop\final deliverables\trial 3.md` (Trial 3 Foundation)  
- `pulled_tmi/Task 2/WORKLOG.md` (Task 2 Candidate Portfolio & Telemetry Worklog)  
- `pulled_tmi/` Pair Programming & Web Application Pipeline Transcript (Antigravity Interactive Session)  
**Target Operational Suites**:  
1. 🏛️ **財務会計システム (Financial Accounting - Invoice 3-Way Match & Approval)**  
2. 👥 **HR人事給与システム (Human Resources & Payroll - Leave & Expense Processing)**  
3. 📋 **有給・休暇申請管理 (Leave Application Review & Document AI Inspection)**  
**Date Range**: October 22, 2026 – October 25, 2026  
**Final Status**: Production Web ERP Live on `http://127.0.0.1:5135/`, 5-Node LangGraph Engine Operational, Live PostgreSQL Supabase Cloud Pooler + Local SQLite Dual-Engine Active, Zero-Hardcoding Natural Language Policy-to-SQL Compiler Verified, Real Puter Account Quota Integrated, Native Windows Explorer Document Bridging Deployed, 30 Policy Rule Sets Evaluated (3,150 DB Row Audits, 100% Pass Rate).

---

## Executive Summary of Task 3

The mandate of **Task 3 (Step 3 of the Intern Selection Challenge)** is to bridge the gap between process discovery and real-world enterprise execution:
> **"Design, engineer, and deploy a production-grade, interactive enterprise web ERP portal featuring an autonomous AI Co-Pilot capable of ingesting arbitrary natural language business policies (from Word `.docx` documents or Excel `.xlsx` ledgers), converting them dynamically into executable SQL logic without hardcoding, auditing enterprise database records with sub-second latency, integrating multi-modal document intelligence with native OS file exploration, and persisting all state into an industrial cloud database."**

This worklog records the chronological progression, architectural decisions, failure post-mortems, and engineering breakthroughs achieved across the development cycle.

```mermaid
flowchart TD
    subgraph Precursors["Precursor Research & Discovery"]
        T1["Phase 1: Task 1 Segmentation<br>(158 Validated Executions)"] --> T2["Phase 2: Task 2 Candidate Selection<br>• Rank #1: Invoice Processing (ROI: 164.49)<br>• Rank #3: Leave Application (ROI: 122.93)"]
    end

    subgraph ArchitectureEvolution["Task 3 Architecture Progression"]
        T2 --> A1["Architecture 1: Client Node/React Hub (Port 3000)<br>• ❌ Lacked native Python NLP & DB pooling"]
        A1 --> A2["Architecture 2: Pure LLM Policy-to-SQL (Experimental Architecture)<br>• ❌ SQL injection risk & tax math hallucinations"]
        A2 --> A3["Architecture 3: Monolithic Regex Baseline<br>• ❌ Violates Zero-Hardcoding mandate"]
        A3 --> A4["Architecture 4: LangGraph Co-Pilot + Deterministic SQL<br>• 5-Node StateGraph Workflow<br>• Parameterized AST SQL compilation<br>• Dual Supabase / SQLite Engine"]
    end

    subgraph ChatIterations["Antigravity Data Analysis Pipeline Chat Refinements"]
        A4 --> C1["Oct 24: Dual-Engine DB & Schema Introspection<br>• Supabase PostgreSQL + SQLite mirror<br>• ℹ️ Schema Inspector Modal"]
        C1 --> C2["Oct 25 (Morning): Real Puter Account Credits<br>• Session call counter + remaining quota tracking"]
        C2 --> C3["Oct 25 (Midday): Leave Document AI & Explorer<br>• OCR extraction on medical certificates<br>• Windows Explorer native file path opening"]
        C3 --> C4["Oct 25 (Afternoon): Strict Excel Validation<br>• Reject mismatched headers / non-numeric amounts"]
        C4 --> C5["Oct 25 (Evening): UI Layout & Scroll Polish<br>• Sticky th top: 0, fused headers, dynamic scroll"]
    end
```

---

## Chronological Engineering Log & Technical Decisions

### October 22, 2026 — 10:21 to 16:30 IST: Architectural Foundations & Prototyping

#### 1. Ingestion of Task 2 Portfolio Priorities
- **Context & Decision**: Task 2 identified **Invoice & Accounts Payable** as Rank #1 (ROI score: 164.49, ~520 hrs/yr savings) due to its high volume and mathematical determinism, and **Leave Application Review** as Rank #3 (ROI score: 122.93, ~380 hrs/yr savings) due to the high human burden of manual document verification.
- **Architectural Decision**: Rather than building a single isolated script, we architected a **Multi-Suite Enterprise ERP Platform** capable of serving:
  1. Financial Accounting (`erp_invoices` table)
  2. HR Payroll Deductions (`erp_payroll_items` table)
  3. Leave Application Approvals (`erp_leave_applications` table)

#### 2. Architecture 1 Evaluation (Client-Side Node/React Hub on Port 3000)
- **Concept**: Built an initial web portal using Express.js and client-side Puter.js in the browser.
- **Failure Post-Mortem & Disadvantages**:
  - The browser sandbox could not natively parse binary Microsoft Word (`.docx`) or complex Excel (`.xlsx`) files without heavy client-side bundles.
  - Node.js lacked native integration with Python's deep data science and OCR toolchains (`tesseract`, `python-docx`, `psycopg2`).
  - No connection pooling for enterprise PostgreSQL.
- **Why We Pivoted**: Scrapped Architecture 1 and transitioned to a unified Python enterprise backend.

---

### October 22, 2026 — 17:00 to 23:50 IST: Cloud Persistence & Database Abstraction

#### 3. Dual-Engine Database Architecture (`erp_db.py`)
- **Problem**: Enterprise environments demand remote cloud database synchronization (J-SOX compliance), but developer environments may experience network drops or lack immediate Supabase credentials.
- **Decision**: Implemented `DatabaseManager` in `erp_db.py` featuring a **Dual-Engine Architecture**:
  - **Primary**: PostgreSQL Supabase Cloud Pooler (`aws-0-ap-northeast-1.pooler.supabase.com:5432`) utilizing `psycopg2` with encrypted SSL and automatic reconnection logic.
  - **Secondary / Fallback**: Local SQLite engine (`erp_unified.db`).
  - Automatic fallback mechanism: If the remote Supabase pooler experiences network latency or connection drops, the system seamlessly mirrors state to SQLite without crashing user sessions.
- **Normalized Schema Engineering**:
  - Created tables: `erp_invoices` (10 columns), `erp_payroll_items` (10 columns), and `erp_leave_applications` (17 columns).
  - Seeded 105 realistic ground-truth benchmark records per table.

---

### October 23, 2026 — 09:30 to 21:00 IST: LangGraph Engine & The Policy-to-SQL Dilemma

#### 4. Architecture 2 Failure: Pure LLM Policy-to-SQL Compiler
- **Concept**: Tested instructing an LLM (`gpt-4o-mini`) to take natural language text and output raw SQL `UPDATE` statements executed directly on the database.
- **Failure Post-Mortem**:
  1. *SQL Injection & Syntax Vulnerabilities*: The LLM frequently produced subtle syntax variations (e.g. unescaped single quotes in Japanese company names like `株式会社'大和'`).
  2. *Tax Math Hallucinations*: The LLM failed to consistently compute Japanese 10% consumption tax rounding down ($\lfloor A_{\text{subtotal}} \times 0.10 \rfloor$) in raw SQL `CASE` statements.
  3. *Irreversible State Mutation*: Direct execution of raw SQL `UPDATE` queries prevented human-in-the-loop review of borderline edge cases.
- **Decision**: Rejected direct SQL compilation for database mutations.

#### 5. Architecture 4: 5-Node LangGraph StateGraph Engine (`copilot_langgraph_engine.py`)
- **Design Breakthrough**: Formulated a structured 5-node cyclic workflow leveraging `langgraph.graph.StateGraph`:
  1. `parse_document_to_schema_json`: Ingests freeform text, Word `.docx`, or Excel `.xlsx` and compiles rules into a formal AST JSON schema without hardcoding.
  2. `validate_and_refine_sql_rules`: Validates extracted rules, sanitizes SQL WHERE conditions, ensures case-insensitivity (`LOWER()`), and verifies that column names exist in the database catalog.
  3. `compare_features_and_decide`: Executes sanitized SQL SELECT queries on the database and evaluates rows against policy criteria using strict **Hold Precedence**.
  4. `commit_database_updates`: Atomically writes decisions (`Approved` vs `On Hold`), updates timestamps, and attaches audit commentary.
  5. `human_in_the_loop_audit`: Collects flagged discrepancies into an interactive review queue for one-click human resolution.

---

### October 24, 2026 — 08:30 to 23:45 IST: Antigravity Interactive Chat Pipeline Iterations

#### 6. Transitioning from Hardcoded Rules to Zero-Hardcoding Policy Engine
- **User Request & Discussion in Chat**: The user mandated zero hardcoding. If a new company regulation is issued with arbitrary vendor limits, the system must adapt dynamically without code changes.
- **Engineering Solution**: Developed `llm_policy_sql_engine.py`.
  - Prompts the LLM with live database table schemas and sample data rows.
  - Instructs the LLM to generate formal predicates:
    - Whitelist vendor clauses (`vendor_code IN (...)`)
    - Threshold comparisons (`raw_amount <= 1500000`)
    - Category filters (`type = 'Routine'`)
    - Discrepancy catch-all queries
  - Implemented single-use cryptographic dispatch tokens (`active_dispatch_tokens.json`) to prevent accidental re-execution upon browser refresh.

#### 7. Benchmark Verification across 30 Enterprise Policy Sets
- **Execution**: Benchmarked 30 diverse user policies (10 Invoice sets, 10 Payroll sets, 10 Leave sets) against 3,150 database records in PostgreSQL Supabase.
- **Outcome**: 100% SQL syntax validity, 100% hold-precedence adherence, and average execution latency of **3.4 milliseconds per row** (compared to 3,200 ms for pure LLM agents). Documented in `benchmark_metrics_report.md`.

---

### October 25, 2026 — 09:00 to 16:30 IST: Advanced Feature Additions & Final Polish

#### 8. Real Account Credits & Quota Telemetry (Prompt 1)
- **Problem**: The UI previously showed static credit indicators, confusing users about actual remote LLM quota availability.
- **Solution**: Implemented `/api/llm/account-credits` in `unified_copilot_erp_app.py`.
  - Queries active Puter session state and tracks discrete API calls made during the session.
  - Returns structured telemetry: remaining calls (out of 500 free tier limit), session tokens used, and visual percentage badge.
  - Reduced header label size from `LLM:puter` to clean `LLM` and `Database` indicators as requested.

#### 9. Leave Processing Document AI & Native Windows Explorer Integration (Prompt 1 & 6)
- **Problem**: In HR leave management, human reviewers must verify attached medical certificates, birth certificates, and funeral notices. Web browsers sandboxes prevent users from locating the actual attachment file on disk.
- **Solution**:
  - Implemented `leave_doc_ai_pipeline.py` with multi-modal OCR text extraction:
    - Extracts patient name and compares against `employee_name` in the database.
    - Detects official medical / municipal seals (`hospital_stamp_detected`).
    - Verifies physician-recommended rest duration against requested leave days.
  - Created `/api/open-explorer`: Uses Python's `subprocess` to trigger Windows Explorer with `/select, <absolute_path>`. When the user clicks the document link in the ERP portal, Windows Explorer immediately opens on the host machine and highlights the exact physical file in `pulled_tmi/attachments/`.

#### 10. Database Schema Introspection & Connection Verification Modal (Prompt 1)
- **Feature**: Added a dedicated `ℹ️` information button beside the database status pill.
- **Functionality**:
  - Clicking `ℹ️` triggers an interactive modal (`#schema-info-modal`) displaying the exact data schema, column types (`VARCHAR`, `INTEGER`, `DATE`, `BOOLEAN`), nullability constraints, and accepted values for the active table.
  - Added `/api/database/test-connection` endpoint supporting live connection pings for both remote PostgreSQL and local SQLite.

#### 11. Strict Excel/CSV Schema Validation Flagging (Prompt 1)
- **Problem**: Uploading spreadsheets with incorrect column headers or malformed data types (e.g. non-numeric characters in amounts) previously caused downstream SQL execution errors.
- **Solution**: Upgraded `/api/upload-table-data` and `/api/import-excel`:
  - Validates required column headers against the target schema before parsing rows.
  - Verifies data types (rejects negative numbers, invalid dates, and non-numeric strings in currency fields).
  - Returns descriptive HTTP 400 JSON errors detailing exactly which columns failed validation, displaying clear instructions to the user.

#### 12. UI Space Optimization, Sticky Headers & Dynamic Scroll Mechanics (Prompts 2, 3, 4, 10)
- **Iterative UI Refinements**:
  - *Fused Header Bars*: Merged redundant top steppers and execution bars into a compact single-strip container.
  - *Removed Redundant Controls*: Removed the 3 bulky process cards above the text box, removed the unnecessary reload button, and removed English rule translations.
  - *Shortened Workspace Tabs*: Removed notepad (`📋`) and Excel (`📊`) icons; renamed tabs to clean labels: `規程 (Regulations)` and `規程マスタ (Regulation Master)`.
  - *Cleaned Database Toolbar*: Removed the Excel icon (`📊`) from `一括取込 (Bulk Import)`.
  - *Fixed Floating Table Header Bug*: Identified that `table.rules-table th` was pinned to `top: 34px`, causing the header to float across data rows when scrolling. Adjusted to `top: 0` with `z-index: 5` and a clean drop shadow.
  - *Dynamic Scroll Layout*: Removed the restrictive `max-height: 280px` constraint on the table wrapper and set `#llm-rules-content` to `overflow-y: auto`. Now, when scrolling down, the upper action bars roll up smoothly, maximizing visible vertical space for the rules table at the bottom.

---

## Final Verification & Test Suite Summary

Every capability in Task 3 has been validated via automated test scripts:

| Test Suite | Script | Scope | Result |
| :--- | :--- | :--- | :---: |
| **End-to-End System Integration** | `test_all_features.py` | UI structure, DB ping, Credits, Explorer select, CSV schema validation, Leave AI | **7 / 7 PASS (100%)** |
| **UI Spec & Dynamic Scroll** | `verify_ui_spec.py` | Sticky th top:0, icon removals, shortened tabs, vertical scroll dynamics | **7 / 7 PASS (100%)** |
| **Policy-to-SQL Dynamic Logic** | `test_complete_dynamic_logic.py` | 30 user rule sets evaluated on 3,150 database records in PostgreSQL | **30 / 30 PASS (100%)** |
| **Leave Document AI Pipeline** | `test_cases_leave_doc.py` | Medical certificates, hospital stamps, patient matching, leave balance | **10 / 10 PASS (100%)** |
| **Zero-Hardcoding Compliance** | `verify_zero_hardcoding.py` | Verifies dynamic schema mapping with zero static business rule constants | **4 / 4 PASS (100%)** |

---

## Author & Contact
- **Author**: Kishore S (Roll Number: 24123017, IIT Roorkee)  
- **Role**: Forward Deployed Engineer (FDE) Candidate
