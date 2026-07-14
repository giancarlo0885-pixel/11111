from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from config import DATABASE_PATH, STARTING_BALANCE

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _path() -> str:
    p = Path(DATABASE_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)

@contextmanager
def connect():
    conn = sqlite3.connect(_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize_database() -> None:
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS portfolios (
            market TEXT PRIMARY KEY,
            cash REAL NOT NULL,
            starting_balance REAL NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL NOT NULL,
            highest_price REAL NOT NULL,
            opened_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(market, symbol)
        );
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            value REAL NOT NULL,
            realized_pnl REAL NOT NULL DEFAULT 0,
            score REAL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            score REAL NOT NULL,
            action TEXT NOT NULL,
            confidence REAL NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            horizon_days INTEGER NOT NULL,
            target_price REAL NOT NULL,
            low_price REAL NOT NULL,
            high_price REAL NOT NULL,
            probability_up REAL NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            equity REAL NOT NULL,
            cash REAL NOT NULL,
            positions_value REAL NOT NULL,
            drawdown REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            symbol TEXT,
            source TEXT,
            created_at TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS intelligence_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            provider TEXT NOT NULL,
            symbol TEXT,
            title TEXT NOT NULL,
            details TEXT,
            event_time TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS worker_status (
            id INTEGER PRIMARY KEY CHECK (id=1),
            status TEXT NOT NULL,
            message TEXT,
            last_run TEXT,
            heartbeat TEXT
        );
        """)
        for market in ("cash", "crypto"):
            conn.execute("""
                INSERT OR IGNORE INTO portfolios(market,cash,starting_balance,updated_at)
                VALUES(?,?,?,?)
            """, (market, STARTING_BALANCE, STARTING_BALANCE, utc_now()))
        conn.execute("""
            INSERT OR IGNORE INTO worker_status(id,status,message,last_run,heartbeat)
            VALUES(1,'waiting','Worker has not completed a scan yet.',NULL,?)
        """, (utc_now(),))

def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]

def row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    r = rows(query, params)
    return r[0] if r else None

def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with connect() as conn:
        conn.execute(query, params)

def set_worker_status(status: str, message: str, completed: bool=False) -> None:
    now = utc_now()
    with connect() as conn:
        conn.execute("""
            UPDATE worker_status
            SET status=?, message=?, heartbeat=?,
                last_run=CASE WHEN ? THEN ? ELSE last_run END
            WHERE id=1
        """, (status, message, now, int(completed), now))

def save_json_signal(market, symbol, price, score, action, confidence, details):
    with connect() as conn:
        conn.execute("""
            INSERT INTO signals(market,symbol,price,score,action,confidence,details,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, (market,symbol,price,score,action,confidence,json.dumps(details),utc_now()))

def save_forecast(market, symbol, forecast):
    with connect() as conn:
        conn.execute("""
            INSERT INTO forecasts(market,symbol,horizon_days,target_price,low_price,high_price,
            probability_up,model,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (market,symbol,forecast.horizon_days,forecast.target_price,forecast.low_price,
              forecast.high_price,forecast.probability_up,forecast.model,utc_now()))

def add_alert(category, severity, title, message, symbol=None, source=None):
    with connect() as conn:
        conn.execute("""
            INSERT INTO alerts(category,severity,title,message,symbol,source,created_at)
            VALUES(?,?,?,?,?,?,?)
        """, (category,severity,title,message,symbol,source,utc_now()))

def save_intelligence_event(category, provider, title, details, symbol=None, event_time=None):
    with connect() as conn:
        conn.execute("""
            INSERT INTO intelligence_events(category,provider,symbol,title,details,event_time,created_at)
            VALUES(?,?,?,?,?,?,?)
        """, (category,provider,symbol,title,json.dumps(details),event_time,utc_now()))

def trim_old_records():
    with connect() as conn:
        for table, limit in [("signals",6000),("forecasts",3000),("equity_snapshots",15000),
                             ("alerts",3000),("intelligence_events",5000)]:
            conn.execute(f"DELETE FROM {table} WHERE id NOT IN (SELECT id FROM {table} ORDER BY id DESC LIMIT {limit})")
