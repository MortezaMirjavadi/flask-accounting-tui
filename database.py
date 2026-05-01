"""Database configuration and initialization."""

import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
from pathlib import Path


def get_database_url():
    """
    Get database URL from environment with smart defaults.
    
    Priority:
    1. DATABASE_URL environment variable (full connection string)
    2. Individual components (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    3. Default: postgresql://localhost:5432/terminal_accounting
    """
    # Check for full connection string first
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url
    
    # Build from individual components
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    database = os.environ.get("DB_NAME", "terminal_accounting")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql://{user}@{host}:{port}/{database}"


# Global database URL (computed once at import)
DATABASE_URL = get_database_url()

# Connection pool (initialized on first use)
_connection_pool = None


def get_connection_pool():
    """Get or create the connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # minconn
            20,  # maxconn
            DATABASE_URL
        )
    return _connection_pool


def get_connection():
    """Get database connection from pool with dict cursor."""
    pool = get_connection_pool()
    conn = pool.getconn()
    # Use RealDictCursor to get dict-like rows (similar to psycopg2.extras.RealDictCursor)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def release_connection(conn):
    """Return connection to pool."""
    pool = get_connection_pool()
    pool.putconn(conn)


def close_all_connections():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None


def _ensure_column(cursor, table_name, column_name, definition):
    """Add column to table if it doesn't exist."""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table_name, column_name))
    
    if cursor.fetchone() is None:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_updated_at_trigger(cursor, table_name):
    trigger_name = f"trg_{table_name}_set_updated_at"
    cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}")
    cursor.execute(
        f"""
        CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )


def init_db():
    """Initialize database tables if they don't exist."""
    print("initialize db is start...")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL CHECK(type IN ('income', 'cost')),
                UNIQUE(user_id, name),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
                UNIQUE(user_id, name),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date DATE NOT NULL,
                amount NUMERIC(15, 2) NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                source_id INTEGER REFERENCES sources(id),
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Budget periods table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_periods (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year, month)
            )
        """)
        
        # Budget items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_items (
                id SERIAL PRIMARY KEY,
                budget_period_id INTEGER NOT NULL REFERENCES budget_periods(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                planned_amount NUMERIC(15, 2) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(budget_period_id, category_id)
            )
        """)

        # Financial events definitions (recurring or single)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                amount NUMERIC(15, 2) NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                source_id INTEGER REFERENCES sources(id),
                frequency VARCHAR(50) NOT NULL DEFAULT 'once',
                repeat_interval INTEGER NOT NULL DEFAULT 1,
                start_date DATE NOT NULL,
                end_date DATE,
                occurrence_limit INTEGER,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)

        # Generated instances (pending, confirmed, skipped, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_event_instances (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES financial_events(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                due_date DATE NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                snoozed_from DATE,
                transaction_id INTEGER REFERENCES transactions(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transfers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                from_source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
                to_source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
                amount NUMERIC(15, 2) NOT NULL CHECK(amount > 0),
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK(from_source_id != to_source_id)
            )
        """)

        # Create indexes for transfers
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_user ON transfers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_from_source ON transfers(from_source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_to_source ON transfers(to_source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers(date)")

        # Ensure legacy tables contain soft-delete support
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
            _ensure_column(cursor, table_name, "deleted_at", "TIMESTAMP")

        for table_name in (
            "users",
            "categories",
            "sources",
            "transactions",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "transfers",
        ):
            _ensure_column(cursor, table_name, "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
            _ensure_column(cursor, table_name, "updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")

        for table_name in (
            "users",
            "categories",
            "sources",
            "transactions",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "transfers",
        ):
            _ensure_updated_at_trigger(cursor, table_name)

        for table_name in (
            "categories",
            "sources",
            "transactions",
            "transfers",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "users",
        ):
            cursor.execute(f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            cursor.execute(f"UPDATE {table_name} SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        # Create indexes for calendar and forecasting modules
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_financial_events_user_active
                ON financial_events(user_id, status, deleted_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_financial_events_date
                ON financial_events(user_id, start_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_financial_event_instances_user_due
                ON financial_event_instances(user_id, due_date, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_financial_event_instances_event
                ON financial_event_instances(event_id, due_date)
        """)
        
        conn.commit()
        print(f"[DB] Database initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"[DB] Error initializing database: {e}")
        raise
    finally:
        cursor.close()
        release_connection(conn)


# Verify configuration on module load
print(f"[DB] Database URL configured: {DATABASE_URL}")
