import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("accounting.db")


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(cursor, name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table must exist first so FK references work
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Helper to recreate a table with a new schema while preserving data
    def _recreate_table(create_sql, old_name, new_name):
        cursor.execute(create_sql)
        # Copy data from old table to new table, mapping old columns to new columns
        cursor.execute(f"PRAGMA table_info({old_name})")
        old_cols = [row["name"] for row in cursor.fetchall()]
        cursor.execute(f"PRAGMA table_info({new_name})")
        new_cols = [row["name"] for row in cursor.fetchall()]
        common_cols = [c for c in new_cols if c in old_cols]
        if common_cols:
            cols = ", ".join(common_cols)
            cursor.execute(
                f"INSERT INTO {new_name} ({cols}) SELECT {cols} FROM {old_name}"
            )
        cursor.execute(f"DROP TABLE {old_name}")

    # Categories
    if _table_exists(cursor, "categories") and not _column_exists(
        cursor, "categories", "user_id"
    ):
        cursor.execute("ALTER TABLE categories RENAME TO categories_old")
        _recreate_table(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'cost')),
                UNIQUE(user_id, name)
            )
            """,
            "categories_old",
            "categories",
        )
        cursor.execute("DROP TABLE IF EXISTS categories_old")
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'cost')),
                UNIQUE(user_id, name)
            )
            """
        )

    # Sources
    if _table_exists(cursor, "sources") and not _column_exists(
        cursor, "sources", "user_id"
    ):
        cursor.execute("ALTER TABLE sources RENAME TO sources_old")
        _recreate_table(
            """
            CREATE TABLE sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                UNIQUE(user_id, name)
            )
            """,
            "sources_old",
            "sources",
        )
        cursor.execute("DROP TABLE IF EXISTS sources_old")
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                UNIQUE(user_id, name)
            )
            """
        )

    # Transactions
    if _table_exists(cursor, "transactions") and not _column_exists(
        cursor, "transactions", "user_id"
    ):
        cursor.execute("ALTER TABLE transactions RENAME TO transactions_old")
        _recreate_table(
            """
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER,
                source_id INTEGER,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (source_id) REFERENCES sources(id)
            )
            """,
            "transactions_old",
            "transactions",
        )
        cursor.execute("DROP TABLE IF EXISTS transactions_old")
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER,
                source_id INTEGER,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (source_id) REFERENCES sources(id)
            )
            """
        )

    conn.commit()
    conn.close()
