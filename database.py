"""Database configuration and initialization."""

import os
import sqlite3
from pathlib import Path

def get_database_path():
    """
    Get database path from environment with smart defaults.
    
    Priority:
    1. DATABASE_PATH environment variable
    2. Default: ./data/accounting.db (relative to project root)
    """
    # Get from environment or use default
    db_path = os.environ.get("DATABASE_PATH", "./data/accounting.db")
    
    # Convert to Path object
    path = Path(db_path).expanduser()  # Expand ~ to home directory
    
    # If still relative, make it relative to this file's directory
    if not path.is_absolute():
        project_root = Path(__file__).parent.resolve()
        path = project_root / path
    
    # CRITICAL: Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    return str(path)


# Global database path (computed once at import)
DATABASE_PATH = get_database_path()


def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cursor, table_name, column_name, definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing = {row["name"] for row in cursor.fetchall()}
    if column_name not in existing:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'cost')),
            UNIQUE(user_id, name)
        )
    """)
    
    # Sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            UNIQUE(user_id, name)
        )
    """)
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            source_id INTEGER REFERENCES sources(id),
            description TEXT
        )
    """)
    
    # Budget periods table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            year INTEGER NOT NULL,
            month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, year, month)
        )
    """)
    
    # Budget items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget_period_id INTEGER NOT NULL REFERENCES budget_periods(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            planned_amount REAL NOT NULL,
            notes TEXT,
            UNIQUE(budget_period_id, category_id)
        )
    """)

    # Financial events definitions (recurring or single)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            source_id INTEGER REFERENCES sources(id),
            frequency TEXT NOT NULL DEFAULT 'once',
            repeat_interval INTEGER NOT NULL DEFAULT 1,
            start_date TEXT NOT NULL,
            end_date TEXT,
            occurrence_limit INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    """)

    # Generated instances (pending, confirmed, skipped, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_event_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES financial_events(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            snoozed_from TEXT,
            transaction_id INTEGER REFERENCES transactions(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_modified_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            from_source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
            to_source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
            amount REAL NOT NULL CHECK(amount > 0),
            date TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            CHECK(from_source_id != to_source_id)
        );

        CREATE INDEX IF NOT EXISTS idx_transfers_user ON transfers(user_id);
        CREATE INDEX IF NOT EXISTS idx_transfers_from_source ON transfers(from_source_id);
        CREATE INDEX IF NOT EXISTS idx_transfers_to_source ON transfers(to_source_id);
        CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers(date);
    """)

    # Ensure legacy tables contain soft-delete support used across services
    for table_name in (
        "categories",
        "sources",
        "transactions",
        "transfers",
        "budget_periods",
        "budget_items",
        "financial_events",
        "financial_event_instances",
    ):
        _ensure_column(cursor, table_name, "deleted_at", "TEXT")

    # Keep query speed high for calendar and forecasting modules
    cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_financial_events_user_active
            ON financial_events(user_id, status, deleted_at);
        CREATE INDEX IF NOT EXISTS idx_financial_events_date
            ON financial_events(user_id, start_date);
        CREATE INDEX IF NOT EXISTS idx_financial_event_instances_user_due
            ON financial_event_instances(user_id, due_date, status);
        CREATE INDEX IF NOT EXISTS idx_financial_event_instances_event
            ON financial_event_instances(event_id, due_date);
    """)

    for table_name in (
        "categories",
        "sources",
        "transactions",
        "transfers",
        "budget_periods",
        "budget_items",
    ):
        _ensure_column(cursor, table_name, "deleted_at", "TEXT")
    
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized successfully")

# Verify path on module load
print(f"[DB] Database path configured: {DATABASE_PATH}")
