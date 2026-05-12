from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_DIR = ROOT_DIR / "database"
DB_PATH = DB_DIR / "software_patent.db"
SCHEMA_PATH = DB_DIR / "init.sql"


def get_connection() -> sqlite3.Connection:
    """Create a short-lived SQLite connection with dict-like rows."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize schema and idempotent default records."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()


def fetch_one(query: str, params: Iterable[object] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchone()


def fetch_all(query: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchall()

