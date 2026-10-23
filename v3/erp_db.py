"""
ERP Database Layer: PostgreSQL (Supabase/Custom) with SQLite Fallback
Provides robust database persistence for both:
  1. Financial Accounting System: Invoice Processing (`erp_invoices`)
  2. HR & Payroll System: Payroll Item Processing (`erp_payroll_items`)
"""

import os
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from generate_100_benchmarks import build_105_invoices, build_105_payroll_items

INITIAL_INVOICES = build_105_invoices()
INITIAL_PAYROLL_ITEMS = build_105_payroll_items()


class DatabaseManager:
    def __init__(self):
        self.engine_type = "sqlite"
        self.db_url = os.environ.get("SUPABASE_DB_URL", "").strip()
        self.sqlite_path = Path(__file__).parent / "erp_unified.db"
        self.error_msg = None
        self._reload_env()
        self._init_connection()

    def _reload_env(self):
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()
        self.db_url = os.environ.get("SUPABASE_DB_URL", "").strip()

    def _get_pg_kwargs(self):
        self._reload_env()
        if self.db_url:
            return {"dsn": self.db_url}
        host = os.environ.get("DB_POSTGRESDB_HOST", "").strip()
        user = os.environ.get("DB_POSTGRESDB_USER", "").strip()
        pwd = os.environ.get("DB_POSTGRESDB_PASSWORD", "").strip()
        db = os.environ.get("DB_POSTGRESDB_DATABASE", "postgres").strip()
        port = os.environ.get("DB_POSTGRESDB_PORT", "5432").strip()
        if host and user and pwd:
            return {
                "host": host,
                "port": int(port) if port.isdigit() else 5432,
                "dbname": db,
                "user": user,
                "password": pwd
            }
        return None

    def _init_connection(self):
        kwargs = self._get_pg_kwargs()
        if kwargs:
            try:
                import psycopg2
                conn = psycopg2.connect(**kwargs, connect_timeout=5)
                conn.close()
                self.engine_type = "postgresql"
                self._init_pg_schema()
                self.error_msg = None
                print(f"[ERP DB] Successfully connected to PostgreSQL")
                return
            except Exception as e:
                self.error_msg = f"Failed to connect to PostgreSQL: {str(e)}"
                print(f"[ERP DB] {self.error_msg}. Falling back to SQLite.")

        # Fallback to SQLite
        self.engine_type = "sqlite"
        self._init_sqlite_schema()

    def set_custom_database(self, url_or_dsn: str) -> Dict[str, Any]:
        """Allows dynamic connection to user-supplied PostgreSQL DB or switching to SQLite."""
        if not url_or_dsn or url_or_dsn.strip().lower() in ("sqlite", "local", "default"):
            self.engine_type = "sqlite"
            self.db_url = ""
            self._init_sqlite_schema()
            return {"success": True, "engine": "sqlite", "path": str(self.sqlite_path), "message": "Switched to local SQLite database."}

        try:
            import psycopg2
            conn = psycopg2.connect(url_or_dsn.strip(), connect_timeout=5)
            conn.close()
            self.db_url = url_or_dsn.strip()
            self.engine_type = "postgresql"
            self._init_pg_schema()
            self.error_msg = None
            return {"success": True, "engine": "postgresql", "message": "Successfully connected to custom PostgreSQL database!"}
        except Exception as e:
            return {"success": False, "engine": self.engine_type, "message": f"Connection failed: {str(e)}"}

    def set_custom_sqlite_path(self, path_str: str) -> Dict[str, Any]:
        """Allows user to specify custom local SQLite file path."""
        try:
            p = Path(path_str.strip())
            p.parent.mkdir(parents=True, exist_ok=True)
            self.sqlite_path = p
            self.engine_type = "sqlite"
            self.db_url = ""
            self._init_sqlite_schema()
            self.error_msg = None
            return {"success": True, "engine": "sqlite", "path": str(self.sqlite_path), "message": f"Successfully connected to local SQLite database at {self.sqlite_path}"}
        except Exception as e:
            return {"success": False, "engine": self.engine_type, "message": f"Failed to initialize local SQLite at {path_str}: {str(e)}"}

    def _get_pg_conn(self):
        import psycopg2
        kwargs = self._get_pg_kwargs()
        if not kwargs:
            raise ValueError("No PostgreSQL configuration available.")
        return psycopg2.connect(**kwargs)

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_pg_schema(self):
        with self._get_pg_conn() as conn:
            with conn.cursor() as cur:
                # 1. Invoice Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS erp_invoices (
                        id VARCHAR(50) PRIMARY KEY,
                        employee_id VARCHAR(50),
                        name VARCHAR(255),
                        invoice_no VARCHAR(50),
                        amount VARCHAR(50),
                        raw_amount BIGINT,
                        type VARCHAR(50),
                        status VARCHAR(50),
                        ref VARCHAR(255),
                        comment TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # 2. Payroll Items Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS erp_payroll_items (
                        id VARCHAR(50) PRIMARY KEY,
                        employee_id VARCHAR(50),
                        employee_name VARCHAR(255),
                        item_category VARCHAR(100),
                        item_type VARCHAR(50),
                        amount VARCHAR(50),
                        raw_amount BIGINT,
                        status VARCHAR(50),
                        voucher_ref VARCHAR(100),
                        comment TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # 3. Audit Logs
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS erp_audit_logs (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(50),
                        record_id VARCHAR(50),
                        action VARCHAR(50),
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Ensure columns exist if previously created with older schema
                cur.execute("""
                    ALTER TABLE erp_audit_logs ADD COLUMN IF NOT EXISTS table_name VARCHAR(50);
                    ALTER TABLE erp_audit_logs ADD COLUMN IF NOT EXISTS record_id VARCHAR(50);
                """)

                # Check Invoices Count
                cur.execute("SELECT COUNT(*) FROM erp_invoices;")
                if cur.fetchone()[0] == 0:
                    from psycopg2.extras import execute_values
                    inv_rows = [
                        (inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                         inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                         inv["ref"], inv["comment"])
                        for inv in INITIAL_INVOICES
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_invoices 
                        (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                        VALUES %s
                    """, inv_rows)

                # Check Payroll Count
                cur.execute("SELECT COUNT(*) FROM erp_payroll_items;")
                if cur.fetchone()[0] == 0:
                    from psycopg2.extras import execute_values
                    pay_rows = [
                        (p["id"], p["employee_id"], p["employee_name"], p["item_category"],
                         p["item_type"], p["amount"], p["raw_amount"], p["status"],
                         p["voucher_ref"], p["comment"])
                        for p in INITIAL_PAYROLL_ITEMS
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_payroll_items 
                        (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                        VALUES %s
                    """, pay_rows)

            conn.commit()

    def _init_sqlite_schema(self):
        with self._get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS erp_invoices (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT,
                    name TEXT,
                    invoice_no TEXT,
                    amount TEXT,
                    raw_amount INTEGER,
                    type TEXT,
                    status TEXT,
                    ref TEXT,
                    comment TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS erp_payroll_items (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT,
                    employee_name TEXT,
                    item_category TEXT,
                    item_type TEXT,
                    amount TEXT,
                    raw_amount INTEGER,
                    status TEXT,
                    voucher_ref TEXT,
                    comment TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS erp_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT,
                    record_id TEXT,
                    action TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("SELECT COUNT(*) FROM erp_invoices;")
            if cur.fetchone()[0] == 0:
                for inv in INITIAL_INVOICES:
                    cur.execute("""
                        INSERT INTO erp_invoices 
                        (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                        inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                        inv["ref"], inv["comment"]
                    ))

            cur.execute("SELECT COUNT(*) FROM erp_payroll_items;")
            if cur.fetchone()[0] == 0:
                for p in INITIAL_PAYROLL_ITEMS:
                    cur.execute("""
                        INSERT INTO erp_payroll_items 
                        (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p["id"], p["employee_id"], p["employee_name"], p["item_category"],
                        p["item_type"], p["amount"], p["raw_amount"], p["status"],
                        p["voucher_ref"], p["comment"]
                    ))
            conn.commit()

    # --- Read Operations ---
    def get_all_invoices(self) -> List[Dict[str, Any]]:
        def _clean(r):
            d = dict(r)
            if "updated_at" in d and d["updated_at"] is not None:
                d["updated_at"] = str(d["updated_at"])
            return d

        if self.engine_type == "postgresql":
            import psycopg2.extras
            with self._get_pg_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment, updated_at FROM erp_invoices ORDER BY id ASC;")
                    return [_clean(r) for r in cur.fetchall()]
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment, updated_at FROM erp_invoices ORDER BY id ASC;")
                return [_clean(r) for r in cur.fetchall()]

    fetch_invoices = get_all_invoices

    def get_all_payroll_items(self) -> List[Dict[str, Any]]:
        def _clean(r):
            d = dict(r)
            if "updated_at" in d and d["updated_at"] is not None:
                d["updated_at"] = str(d["updated_at"])
            return d

        if self.engine_type == "postgresql":
            import psycopg2.extras
            with self._get_pg_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment, updated_at FROM erp_payroll_items ORDER BY id ASC;")
                    return [_clean(r) for r in cur.fetchall()]
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment, updated_at FROM erp_payroll_items ORDER BY id ASC;")
                return [_clean(r) for r in cur.fetchall()]

    fetch_payroll_items = get_all_payroll_items

    # --- Batch Update Operations (Fast & Atomic) ---
    def batch_update_invoices(self, updates: List[Dict[str, Any]]) -> int:
        if not updates:
            return 0
        if self.engine_type == "postgresql":
            from psycopg2.extras import execute_values
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    update_tuples = [(u["status"], u["comment"], u["id"]) for u in updates]
                    execute_values(cur, """
                        UPDATE erp_invoices AS inv
                        SET status = val.status, comment = val.comment, updated_at = CURRENT_TIMESTAMP
                        FROM (VALUES %s) AS val(status, comment, id)
                        WHERE inv.id = val.id OR inv.invoice_no = val.id;
                    """, update_tuples)

                    audit_tuples = [("erp_invoices", u["id"], u["status"], u["comment"]) for u in updates]
                    execute_values(cur, """
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES %s;
                    """, audit_tuples)
                conn.commit()
            return len(updates)
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    UPDATE erp_invoices 
                    SET status = ?, comment = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? OR invoice_no = ?;
                """, [(u["status"], u["comment"], u["id"], u["id"]) for u in updates])
                cur.executemany("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_invoices', ?, ?, ?);
                """, [(u["id"], u["status"], u["comment"]) for u in updates])
                conn.commit()
            return len(updates)

    def batch_update_payroll_items(self, updates: List[Dict[str, Any]]) -> int:
        if not updates:
            return 0
        if self.engine_type == "postgresql":
            from psycopg2.extras import execute_values
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    update_tuples = [(u["status"], u["comment"], u["id"]) for u in updates]
                    execute_values(cur, """
                        UPDATE erp_payroll_items AS p
                        SET status = val.status, comment = val.comment, updated_at = CURRENT_TIMESTAMP
                        FROM (VALUES %s) AS val(status, comment, id)
                        WHERE p.id = val.id;
                    """, update_tuples)

                    audit_tuples = [("erp_payroll_items", u["id"], u["status"], u["comment"]) for u in updates]
                    execute_values(cur, """
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES %s;
                    """, audit_tuples)
                conn.commit()
            return len(updates)
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    UPDATE erp_payroll_items 
                    SET status = ?, comment = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                """, [(u["status"], u["comment"], u["id"]) for u in updates])
                cur.executemany("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_payroll_items', ?, ?, ?);
                """, [(u["id"], u["status"], u["comment"]) for u in updates])
                conn.commit()
            return len(updates)

    # --- Single Record Updates & Inserts ---
    def add_invoice(self, inv: Dict[str, Any]) -> bool:
        """Adds a single new invoice record to the database."""
        raw_amt = inv.get("raw_amount")
        if raw_amt is None:
            amt_str = str(inv.get("amount", "0")).replace("¥", "").replace(",", "").strip()
            raw_amt = int(amt_str) if amt_str.isdigit() else 0
        amt_formatted = f"¥{raw_amt:,}" if "¥" not in str(inv.get("amount", "")) else inv.get("amount")

        record = {
            "id": inv.get("id"),
            "employee_id": inv.get("employee_id", "V3001"),
            "name": inv.get("name", "New Supplier"),
            "invoice_no": inv.get("invoice_no", f"INV-2026-{raw_amt%10000:04d}"),
            "amount": amt_formatted,
            "raw_amount": raw_amt,
            "type": inv.get("type", "Routine"),
            "status": inv.get("status", "Unprocessed"),
            "ref": inv.get("ref", f"Order Ref : {inv.get('invoice_no', 'NEW')}"),
            "comment": inv.get("comment", "")
        }

        if self.engine_type == "postgresql":
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO erp_invoices 
                        (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            name = EXCLUDED.name,
                            amount = EXCLUDED.amount,
                            raw_amount = EXCLUDED.raw_amount,
                            type = EXCLUDED.type,
                            status = EXCLUDED.status,
                            comment = EXCLUDED.comment;
                    """, (
                        record["id"], record["employee_id"], record["name"], record["invoice_no"],
                        record["amount"], record["raw_amount"], record["type"], record["status"],
                        record["ref"], record["comment"]
                    ))
                    cur.execute("""
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES ('erp_invoices', %s, 'INSERT', 'User manually inserted invoice record');
                    """, (record["id"],))
                conn.commit()
            return True
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO erp_invoices 
                    (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    record["id"], record["employee_id"], record["name"], record["invoice_no"],
                    record["amount"], record["raw_amount"], record["type"], record["status"],
                    record["ref"], record["comment"]
                ))
                cur.execute("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_invoices', ?, 'INSERT', 'User manually inserted invoice record');
                """, (record["id"],))
                conn.commit()
            return True

    def add_payroll_item(self, item: Dict[str, Any]) -> bool:
        """Adds a single new payroll item record to the database."""
        raw_amt = item.get("raw_amount")
        if raw_amt is None:
            amt_str = str(item.get("amount", "0")).replace("¥", "").replace(",", "").strip()
            raw_amt = int(amt_str) if amt_str.isdigit() else 0
        amt_formatted = f"¥{raw_amt:,}" if "¥" not in str(item.get("amount", "")) else item.get("amount")

        record = {
            "id": item.get("id"),
            "employee_id": item.get("employee_id", "EMP-001"),
            "employee_name": item.get("employee_name", "新規従業員"),
            "item_category": item.get("item_category", "経費精算"),
            "item_type": item.get("item_type", "Addition"),
            "amount": amt_formatted,
            "raw_amount": raw_amt,
            "status": item.get("status", "Unprocessed"),
            "voucher_ref": item.get("voucher_ref", "P1-07089771-NEW"),
            "comment": item.get("comment", "")
        }

        if self.engine_type == "postgresql":
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO erp_payroll_items 
                        (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            employee_name = EXCLUDED.employee_name,
                            item_category = EXCLUDED.item_category,
                            item_type = EXCLUDED.item_type,
                            amount = EXCLUDED.amount,
                            raw_amount = EXCLUDED.raw_amount,
                            status = EXCLUDED.status,
                            comment = EXCLUDED.comment;
                    """, (
                        record["id"], record["employee_id"], record["employee_name"], record["item_category"],
                        record["item_type"], record["amount"], record["raw_amount"], record["status"],
                        record["voucher_ref"], record["comment"]
                    ))
                    cur.execute("""
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES ('erp_payroll_items', %s, 'INSERT', 'User manually inserted payroll record');
                    """, (record["id"],))
                conn.commit()
            return True
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO erp_payroll_items 
                    (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    record["id"], record["employee_id"], record["employee_name"], record["item_category"],
                    record["item_type"], record["amount"], record["raw_amount"], record["status"],
                    record["voucher_ref"], record["comment"]
                ))
                cur.execute("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_payroll_items', ?, 'INSERT', 'User manually inserted payroll record');
                """, (record["id"],))
                conn.commit()
            return True

    def bulk_add_invoices(self, invoices: List[Dict[str, Any]]) -> int:
        """Batch inserts multiple invoices (e.g. from Excel/CSV upload or tabular copy-paste)."""
        if not invoices:
            return 0
        cleaned = []
        import time
        for idx, inv in enumerate(invoices):
            raw_amt = inv.get("raw_amount")
            if raw_amt is None:
                amt_str = str(inv.get("amount", "0")).replace("¥", "").replace(",", "").strip()
                raw_amt = int(amt_str) if amt_str.isdigit() else 0
            amt_formatted = f"¥{raw_amt:,}" if "¥" not in str(inv.get("amount", "")) else inv.get("amount")
            row_id = inv.get("id")
            if not row_id or str(row_id).lower() in ("none", ""):
                row_id = f"P6-{int(time.time()*1000)%100000000:08d}-{idx+1:03d}"
            cleaned.append({
                "id": str(row_id),
                "employee_id": str(inv.get("employee_id", "V3001")),
                "name": str(inv.get("name", "New Supplier")),
                "invoice_no": str(inv.get("invoice_no", f"INV-2026-{raw_amt%10000:04d}")),
                "amount": amt_formatted,
                "raw_amount": raw_amt,
                "type": str(inv.get("type", "Routine")),
                "status": str(inv.get("status", "Unprocessed")),
                "ref": str(inv.get("ref", f"Order Ref : {inv.get('invoice_no', 'NEW')}")),
                "comment": str(inv.get("comment", ""))
            })

        if self.engine_type == "postgresql":
            from psycopg2.extras import execute_values
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    rows = [
                        (r["id"], r["employee_id"], r["name"], r["invoice_no"],
                         r["amount"], r["raw_amount"], r["type"], r["status"],
                         r["ref"], r["comment"])
                        for r in cleaned
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_invoices 
                        (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                        VALUES %s
                        ON CONFLICT (id) DO UPDATE SET 
                            name = EXCLUDED.name,
                            amount = EXCLUDED.amount,
                            raw_amount = EXCLUDED.raw_amount,
                            type = EXCLUDED.type,
                            status = EXCLUDED.status,
                            comment = EXCLUDED.comment;
                    """, rows)
                    audit_rows = [("erp_invoices", r["id"], "BULK_INSERT", "Bulk imported invoice record") for r in cleaned]
                    execute_values(cur, """
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES %s;
                    """, audit_rows)
                conn.commit()
            return len(cleaned)
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    INSERT OR REPLACE INTO erp_invoices 
                    (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, [
                    (r["id"], r["employee_id"], r["name"], r["invoice_no"],
                     r["amount"], r["raw_amount"], r["type"], r["status"],
                     r["ref"], r["comment"])
                    for r in cleaned
                ])
                cur.executemany("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_invoices', ?, 'BULK_INSERT', 'Bulk imported invoice record');
                """, [(r["id"],) for r in cleaned])
                conn.commit()
            return len(cleaned)

    def bulk_add_payroll_items(self, items: List[Dict[str, Any]]) -> int:
        """Batch inserts multiple payroll items (e.g. from Excel/CSV upload or tabular copy-paste)."""
        if not items:
            return 0
        cleaned = []
        import time
        for idx, item in enumerate(items):
            raw_amt = item.get("raw_amount")
            if raw_amt is None:
                amt_str = str(item.get("amount", "0")).replace("¥", "").replace(",", "").strip()
                raw_amt = int(amt_str) if amt_str.isdigit() else 0
            amt_formatted = f"¥{raw_amt:,}" if "¥" not in str(item.get("amount", "")) else item.get("amount")
            row_id = item.get("id")
            if not row_id or str(row_id).lower() in ("none", ""):
                row_id = f"P4-{int(time.time()*1000)%100000000:08d}-{idx+1:03d}"
            cleaned.append({
                "id": str(row_id),
                "employee_id": str(item.get("employee_id", "EMP-001")),
                "employee_name": str(item.get("employee_name", "新規従業員")),
                "item_category": str(item.get("item_category", "経費精算")),
                "item_type": str(item.get("item_type", "Addition")),
                "amount": amt_formatted,
                "raw_amount": raw_amt,
                "status": str(item.get("status", "Unprocessed")),
                "voucher_ref": str(item.get("voucher_ref", "P1-07089771-NEW")),
                "comment": str(item.get("comment", ""))
            })

        if self.engine_type == "postgresql":
            from psycopg2.extras import execute_values
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    rows = [
                        (r["id"], r["employee_id"], r["employee_name"], r["item_category"],
                         r["item_type"], r["amount"], r["raw_amount"], r["status"],
                         r["voucher_ref"], r["comment"])
                        for r in cleaned
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_payroll_items 
                        (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                        VALUES %s
                        ON CONFLICT (id) DO UPDATE SET 
                            employee_name = EXCLUDED.employee_name,
                            item_category = EXCLUDED.item_category,
                            item_type = EXCLUDED.item_type,
                            amount = EXCLUDED.amount,
                            raw_amount = EXCLUDED.raw_amount,
                            status = EXCLUDED.status,
                            comment = EXCLUDED.comment;
                    """, rows)
                    audit_rows = [("erp_payroll_items", r["id"], "BULK_INSERT", "Bulk imported payroll record") for r in cleaned]
                    execute_values(cur, """
                        INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                        VALUES %s;
                    """, audit_rows)
                conn.commit()
            return len(cleaned)
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    INSERT OR REPLACE INTO erp_payroll_items 
                    (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, [
                    (r["id"], r["employee_id"], r["employee_name"], r["item_category"],
                     r["item_type"], r["amount"], r["raw_amount"], r["status"],
                     r["voucher_ref"], r["comment"])
                    for r in cleaned
                ])
                cur.executemany("""
                    INSERT INTO erp_audit_logs (table_name, record_id, action, comment)
                    VALUES ('erp_payroll_items', ?, 'BULK_INSERT', 'Bulk imported payroll record');
                """, [(r["id"],) for r in cleaned])
                conn.commit()
            return len(cleaned)

    def update_invoice_status(self, identifier: str, status: str, comment: str) -> bool:
        return self.batch_update_invoices([{"id": identifier, "status": status, "comment": comment}]) > 0

    def update_payroll_item_status(self, identifier: str, status: str, comment: str) -> bool:
        return self.batch_update_payroll_items([{"id": identifier, "status": status, "comment": comment}]) > 0

    def reset_all(self):
        """Resets both tables to pristine initial benchmark data."""
        if self.engine_type == "postgresql":
            from psycopg2.extras import execute_values
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM erp_invoices;")
                    cur.execute("DELETE FROM erp_payroll_items;")
                    cur.execute("DELETE FROM erp_audit_logs;")

                    inv_rows = [
                        (inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                         inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                         inv["ref"], inv["comment"])
                        for inv in INITIAL_INVOICES
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_invoices 
                        (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                        VALUES %s
                    """, inv_rows)

                    pay_rows = [
                        (p["id"], p["employee_id"], p["employee_name"], p["item_category"],
                         p["item_type"], p["amount"], p["raw_amount"], p["status"],
                         p["voucher_ref"], p["comment"])
                        for p in INITIAL_PAYROLL_ITEMS
                    ]
                    execute_values(cur, """
                        INSERT INTO erp_payroll_items 
                        (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                        VALUES %s
                    """, pay_rows)
                conn.commit()
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM erp_invoices;")
                cur.execute("DELETE FROM erp_payroll_items;")
                cur.execute("DELETE FROM erp_audit_logs;")

                inv_rows = [
                    (inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                     inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                     inv["ref"], inv["comment"])
                    for inv in INITIAL_INVOICES
                ]
                cur.executemany("""
                    INSERT INTO erp_invoices 
                    (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, inv_rows)

                pay_rows = [
                    (p["id"], p["employee_id"], p["employee_name"], p["item_category"],
                     p["item_type"], p["amount"], p["raw_amount"], p["status"],
                     p["voucher_ref"], p["comment"])
                    for p in INITIAL_PAYROLL_ITEMS
                ]
                cur.executemany("""
                    INSERT INTO erp_payroll_items 
                    (id, employee_id, employee_name, item_category, item_type, amount, raw_amount, status, voucher_ref, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, pay_rows)
                conn.commit()

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine": self.engine_type,
            "connected": True,
            "display_target": "PostgreSQL (Supabase/Custom Active)" if self.engine_type == "postgresql" else f"Local SQLite ({self.sqlite_path.name})",
            "sqlite_path": str(self.sqlite_path),
            "error": self.error_msg
        }

db_manager = DatabaseManager()

MASTER_REGULATIONS_FILE = Path(__file__).parent / "master_regulations.json"

DEFAULT_MASTER_REGULATIONS = [
    {"code": "規程第1条", "name": "交通費精算", "limit": "実費 (近郊電車・バス)", "req": "領収書・運賃照合済", "class": "Addition"},
    {"code": "規程第2条", "name": "消耗品費", "limit": "1件あたり上限 10万円", "req": "品名明細書添付要", "class": "Addition"},
    {"code": "規程第3条", "name": "出張旅費", "limit": "宿泊1.5万円/日、日当規程内 (上限15万円)", "req": "出張報告書提出済", "class": "Addition"},
    {"code": "規程第4条", "name": "研修費", "limit": "年間上限 20万円 (1回10万円)", "req": "技術受講証添付要", "class": "Addition"},
    {"code": "規程第5条", "name": "在宅勤務手当", "limit": "月額一律 15,000円", "req": "在宅勤務申請届済", "class": "Addition"},
    {"code": "規程第6条", "name": "残業手当調整", "limit": "労基法割増率 (25%〜50%)", "req": "勤怠システム打刻整合", "class": "Addition"},
    {"code": "規程第7条", "name": "接待交際費", "limit": "1件あたり上限 100,000円", "req": "超過時は役員特別決裁必須", "class": "Addition"},
    {"code": "規程第8条", "name": "役職手当新設", "limit": "役職等級基準額 (3万〜10万)", "req": "人事辞令書原本照合", "class": "Addition"},
    {"code": "規程第9条", "name": "役職手当廃止", "limit": "前職手当全額差引", "req": "退任辞令書照合済", "class": "Deduction"},
    {"code": "規程第10条", "name": "扶養控除変更", "limit": "税法所定控除額", "req": "扶養親族等申告書添付", "class": "Deduction"},
    {"code": "規程第11条", "name": "昇給", "limit": "人事考課給与辞令照合済", "req": "辞令書照合済", "class": "Addition"},
    {"code": "規程第12条", "name": "資格取得手当", "limit": "規程所定額 (3万円)", "req": "合格証原本照合済", "class": "Addition"},
    {"code": "V3001", "name": "山田製作所", "limit": "月次金型保守: ¥385,000", "req": "基本契約内・自動承認", "class": "Routine"},
    {"code": "V3002", "name": "大和商事株式会社", "limit": "委託管理費: ¥1,237,439", "req": "契約内整合・自動承認", "class": "Routine"},
    {"code": "V3005", "name": "Global Tech LLC", "limit": "月次保守費: ¥716,232", "req": "固定定額・自動承認", "class": "Routine"},
    {"code": "V3006", "name": "北陸部品工業株式会社", "limit": "定額保守費: ¥455,128", "req": "定期部品交換・自動承認", "class": "Routine"},
    {"code": "V3007", "name": "福岡システムデザイン", "limit": "基幹保守: ¥1,832,962", "req": "運用委託内・自動承認", "class": "Routine"},
    {"code": "V3008", "name": "沖縄物流センター", "limit": "変動費用 (要個別精査)", "req": "物流検収書・経理課長承認必須", "class": "Adjustment"}
]

def get_master_regulations() -> List[Dict[str, Any]]:
    import json
    if MASTER_REGULATIONS_FILE.exists():
        try:
            with open(MASTER_REGULATIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    # Initialize file
    save_master_regulations(DEFAULT_MASTER_REGULATIONS)
    return list(DEFAULT_MASTER_REGULATIONS)

def save_master_regulations(regs: List[Dict[str, Any]]) -> bool:
    import json
    try:
        with open(MASTER_REGULATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(regs, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERP DB] Error saving master regulations: {e}")
        return False
