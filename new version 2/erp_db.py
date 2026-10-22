"""
ERP Database Layer: PostgreSQL (Supabase) with SQLite Fallback
Provides robust database persistence for the Financial Accounting ERP System.
"""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load .env manually if not already in os.environ
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

INITIAL_INVOICES = [
    {
        "id": "P6-07010448-001",
        "employee_id": "V3005",
        "name": "Global Tech LLC",
        "invoice_no": "INV-2026-7344",
        "amount": "¥716,232",
        "raw_amount": 716232,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7344",
        "comment": ""
    },
    {
        "id": "P6-07010448-002",
        "employee_id": "V3006",
        "name": "Hokuriku Parts Industry Co., Ltd.",
        "invoice_no": "INV-2026-7345",
        "amount": "¥455,128",
        "raw_amount": 455128,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7345",
        "comment": ""
    },
    {
        "id": "P6-07010448-003",
        "employee_id": "V3002",
        "name": "Yamato Shoji Co., Ltd.",
        "invoice_no": "INV-2026-7346",
        "amount": "¥1,237,439",
        "raw_amount": 1237439,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7346",
        "comment": ""
    },
    {
        "id": "P6-07010448-004",
        "employee_id": "V3007",
        "name": "Fukuoka System Design",
        "invoice_no": "INV-2026-7347",
        "amount": "¥1,832,962",
        "raw_amount": 1832962,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7347",
        "comment": ""
    },
    {
        "id": "P6-07010448-005",
        "employee_id": "V3008",
        "name": "Okinawa Logistics Center",
        "invoice_no": "INV-2026-7348",
        "amount": "¥317,664",
        "raw_amount": 317664,
        "type": "Adjustment",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7348",
        "comment": ""
    },
    {
        "id": "P6-07010448-006",
        "employee_id": "V3006",
        "name": "Hokuriku Parts Industry Co., Ltd.",
        "invoice_no": "INV-2026-7349",
        "amount": "¥452,219",
        "raw_amount": 452219,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7349",
        "comment": ""
    },
    {
        "id": "P6-07010448-007",
        "employee_id": "V3007",
        "name": "Fukuoka System Design",
        "invoice_no": "INV-2026-7350",
        "amount": "¥1,993,825",
        "raw_amount": 1993825,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7350",
        "comment": ""
    },
    {
        "id": "P6-07010448-008",
        "employee_id": "V3002",
        "name": "Yamato Shoji Co., Ltd.",
        "invoice_no": "INV-2026-7351",
        "amount": "¥1,218,687",
        "raw_amount": 1218687,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7351",
        "comment": ""
    },
    {
        "id": "P6-07010448-009",
        "employee_id": "V3001",
        "name": "Yamada Manufacturing Co., Ltd.",
        "invoice_no": "INV-2026-7352",
        "amount": "¥385,000",
        "raw_amount": 385000,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7352",
        "comment": ""
    },
    {
        "id": "P6-07010448-010",
        "employee_id": "V3006",
        "name": "Hokuriku Parts Industry Co., Ltd.",
        "invoice_no": "INV-2026-7353",
        "amount": "¥437,452",
        "raw_amount": 437452,
        "type": "Adjustment",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7353",
        "comment": ""
    },
    {
        "id": "P6-07010448-011",
        "employee_id": "V3001",
        "name": "Yamada Manufacturing Co., Ltd.",
        "invoice_no": "INV-2026-7354",
        "amount": "¥374,313",
        "raw_amount": 374313,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7354",
        "comment": ""
    },
    {
        "id": "P6-07010448-012",
        "employee_id": "V3007",
        "name": "Fukuoka System Design",
        "invoice_no": "INV-2026-7355",
        "amount": "¥1,685,384",
        "raw_amount": 1685384,
        "type": "Routine",
        "status": "Unprocessed",
        "ref": "Order Ref : INV-2026-7355",
        "comment": ""
    }
]

class DatabaseManager:
    def __init__(self):
        self.engine_type = "sqlite"
        self.db_url = os.environ.get("SUPABASE_DB_URL", "").strip()
        self.sqlite_path = Path(__file__).parent / "erp_invoices.db"
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
                print(f"[ERP DB] Successfully connected to Supabase PostgreSQL at {os.environ.get('DB_POSTGRESDB_HOST', 'configured URI')}")
                return
            except Exception as e:
                self.error_msg = f"Failed to connect to Supabase PostgreSQL: {str(e)}"
                print(f"[ERP DB] {self.error_msg}. Falling back to SQLite.")
        elif os.environ.get("DB_POSTGRESDB_HOST") and not (os.environ.get("DB_POSTGRESDB_USER") and os.environ.get("DB_POSTGRESDB_PASSWORD")):
            self.error_msg = "DB_POSTGRESDB_HOST is set, but DB_POSTGRESDB_USER or DB_POSTGRESDB_PASSWORD is missing in .env."

        # Fallback to SQLite
        self.engine_type = "sqlite"
        self._init_sqlite_schema()

    def _get_pg_conn(self):
        import psycopg2
        import psycopg2.extras
        kwargs = self._get_pg_kwargs()
        if not kwargs:
            raise ValueError("No PostgreSQL configuration available.")
        return psycopg2.connect(**kwargs)

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_pg_schema(self):
        import psycopg2
        with self._get_pg_conn() as conn:
            with conn.cursor() as cur:
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
                    CREATE TABLE IF NOT EXISTS erp_audit_logs (
                        id SERIAL PRIMARY KEY,
                        invoice_id VARCHAR(50),
                        action VARCHAR(50),
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Check row count
                cur.execute("SELECT COUNT(*) FROM erp_invoices;")
                count = cur.fetchone()[0]
                if count == 0:
                    for inv in INITIAL_INVOICES:
                        cur.execute("""
                            INSERT INTO erp_invoices 
                            (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                            inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                            inv["ref"], inv["comment"]
                        ))
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
                CREATE TABLE IF NOT EXISTS erp_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT,
                    action TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("SELECT COUNT(*) FROM erp_invoices;")
            count = cur.fetchone()[0]
            if count == 0:
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
            conn.commit()

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine": self.engine_type,
            "connected": True,
            "target": f"Supabase PostgreSQL ({os.environ.get('DB_POSTGRESDB_HOST', 'remote')})" if self.engine_type == "postgresql" else "Local SQLite (erp_invoices.db)",
            "configured_url_present": bool(self.db_url or (os.environ.get("DB_POSTGRESDB_HOST") and os.environ.get("DB_POSTGRESDB_USER"))),
            "host": os.environ.get("DB_POSTGRESDB_HOST", ""),
            "user_configured": bool(os.environ.get("DB_POSTGRESDB_USER", "")),
            "password_configured": bool(os.environ.get("DB_POSTGRESDB_PASSWORD", "")),
            "error": self.error_msg
        }

    def fetch_all(self) -> List[Dict[str, Any]]:
        if self.engine_type == "postgresql":
            import psycopg2.extras
            with self._get_pg_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment FROM erp_invoices ORDER BY id ASC;")
                    return [dict(row) for row in cur.fetchall()]
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment FROM erp_invoices ORDER BY id ASC;")
                return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, identifier: str) -> Optional[Dict[str, Any]]:
        if self.engine_type == "postgresql":
            import psycopg2.extras
            with self._get_pg_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment FROM erp_invoices WHERE id = %s OR invoice_no = %s LIMIT 1;", (identifier, identifier))
                    row = cur.fetchone()
                    return dict(row) if row else None
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment FROM erp_invoices WHERE id = ? OR invoice_no = ? LIMIT 1;", (identifier, identifier))
                row = cur.fetchone()
                return dict(row) if row else None

    def update_invoice(self, identifier: str, action: str, comment: str) -> Optional[Dict[str, Any]]:
        status = "Approved" if action.lower() in ["approve", "approved", "ok", "登録済み"] else "On Hold"
        if self.engine_type == "postgresql":
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE erp_invoices 
                        SET status = %s, comment = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s OR invoice_no = %s
                        RETURNING id;
                    """, (status, comment, identifier, identifier))
                    res = cur.fetchone()
                    if res:
                        actual_id = res[0]
                        cur.execute("""
                            INSERT INTO erp_audit_logs (invoice_id, action, comment)
                            VALUES (%s, %s, %s);
                        """, (actual_id, action, comment))
                conn.commit()
            return self.fetch_one(identifier)
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE erp_invoices 
                    SET status = ?, comment = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? OR invoice_no = ?;
                """, (status, comment, identifier, identifier))
                cur.execute("""
                    INSERT INTO erp_audit_logs (invoice_id, action, comment)
                    VALUES (?, ?, ?);
                """, (identifier, action, comment))
                conn.commit()
            return self.fetch_one(identifier)

    def reset(self):
        if self.engine_type == "postgresql":
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM erp_invoices;")
                    cur.execute("DELETE FROM erp_audit_logs;")
                    for inv in INITIAL_INVOICES:
                        cur.execute("""
                            INSERT INTO erp_invoices 
                            (id, employee_id, name, invoice_no, amount, raw_amount, type, status, ref, comment)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            inv["id"], inv["employee_id"], inv["name"], inv["invoice_no"],
                            inv["amount"], inv["raw_amount"], inv["type"], inv["status"],
                            inv["ref"], inv["comment"]
                        ))
                conn.commit()
        else:
            with self._get_sqlite_conn() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM erp_invoices;")
                cur.execute("DELETE FROM erp_audit_logs;")
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
                conn.commit()

# Singleton DB manager instance
db_manager = DatabaseManager()
