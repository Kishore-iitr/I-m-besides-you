# -*- coding: utf-8 -*-
# File: config/database.py
# Description: Robust configuration for connecting to PostgreSQL database.

import os
from pathlib import Path
from dotenv import load_dotenv

# Search and load .env from current dir, parent dir, or project root
_curr_path = Path(__file__).resolve()
_potential_env_paths = [
    _curr_path.parent / ".env",
    _curr_path.parent.parent / ".env",
    _curr_path.parent.parent.parent / ".env",
    _curr_path.parent.parent.parent.parent / ".env",
]
for env_path in _potential_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        break

DB_CONFIG = {
    "host": os.getenv("DB_POSTGRESDB_HOST", os.getenv("PGHOST", "localhost")),
    "port": int(os.getenv("DB_POSTGRESDB_PORT", os.getenv("PGPORT", 5432))),
    "dbname": os.getenv("DB_POSTGRESDB_DATABASE", os.getenv("PGDATABASE", "postgres")),
    "user": os.getenv("DB_POSTGRESDB_USER", os.getenv("PGUSER", "postgres")),
    "password": os.getenv("DB_POSTGRESDB_PASSWORD", os.getenv("PGPASSWORD", "postgres")),
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", 15)),
}
