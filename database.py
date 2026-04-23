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
    
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized successfully")

# Verify path on module load
print(f"[DB] Database path configured: {DATABASE_PATH}")