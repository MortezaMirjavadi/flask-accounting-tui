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
    3. Default: postgresql://localhost:5432/terminal_accounting_staging
    """
    # Check for full connection string first
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url
    
    # Build from individual components
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    database = os.environ.get("DB_NAME", "terminal_accounting_staging")
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


def _rename_column_if_exists(cursor, table_name, old_column, new_column):
    """Rename a column if it exists."""
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table_name, old_column))
    if cursor.fetchone() is not None:
        cursor.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_column} TO {new_column}")


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
        
        # ── Migration: rename sources -> wallets for existing databases ────
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables WHERE table_name = 'sources'
            )
        """)
        has_sources = cursor.fetchone()['exists']
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables WHERE table_name = 'wallets'
            )
        """)
        has_wallets = cursor.fetchone()['exists']

        if has_sources and not has_wallets:
            # Rename main table
            cursor.execute("ALTER TABLE sources RENAME TO wallets")

            # Rename FK columns in dependent tables
            _rename_column_if_exists(cursor, "transactions", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "installment_plans", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "checks", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "financial_events", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "debts", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "debt_payments", "source_id", "wallet_id")
            _rename_column_if_exists(cursor, "transfers", "from_source_id", "from_wallet_id")
            _rename_column_if_exists(cursor, "transfers", "to_source_id", "to_wallet_id")

            # Rename junction table source_labels -> wallet_labels
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables WHERE table_name = 'source_labels'
                )
            """)
            if cursor.fetchone()['exists']:
                cursor.execute("ALTER TABLE source_labels RENAME TO wallet_labels")
                _rename_column_if_exists(cursor, "wallet_labels", "source_id", "wallet_id")

            print("[DB] Migrated 'sources' -> 'wallets'")

        # Wallets table (formerly sources) — wallets are containers, balances live on accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
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
                wallet_id INTEGER REFERENCES wallets(id),
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transaction items (line items)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_items (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                quantity NUMERIC(10, 2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
                unit VARCHAR(50),
                unit_price NUMERIC(15, 2),
                total_price NUMERIC(15, 2) NOT NULL CHECK (total_price >= 0),
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_items_transaction ON transaction_items(transaction_id)")

        # Installment plans and individual installment records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS installment_plans (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                total_amount NUMERIC(15, 2) NOT NULL CHECK (total_amount >= 0),
                installment_count INTEGER NOT NULL CHECK (installment_count > 0),
                installment_amount NUMERIC(15, 2) NOT NULL CHECK (installment_amount >= 0),
                start_date DATE NOT NULL,
                due_day_of_month INTEGER NOT NULL CHECK (due_day_of_month BETWEEN 1 AND 31),
                category_id INTEGER NOT NULL REFERENCES categories(id),
                wallet_id INTEGER REFERENCES wallets(id),
                status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'canceled')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS installments (
                id SERIAL PRIMARY KEY,
                plan_id INTEGER NOT NULL REFERENCES installment_plans(id) ON DELETE CASCADE,
                installment_number INTEGER NOT NULL CHECK (installment_number > 0),
                amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
                due_date DATE NOT NULL,
                paid_date DATE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'overdue')),
                transaction_id INTEGER REFERENCES transactions(id),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(plan_id, installment_number)
            )
        """)

        # Checks (issued/received)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                check_number VARCHAR(100),
                bank_name VARCHAR(255),
                amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
                issue_date DATE NOT NULL,
                due_date DATE NOT NULL,
                type VARCHAR(20) NOT NULL CHECK (type IN ('issued', 'received')),
                wallet_id INTEGER REFERENCES wallets(id),
                category_id INTEGER NOT NULL REFERENCES categories(id),
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'cleared', 'bounced', 'canceled')),
                transaction_id INTEGER REFERENCES transactions(id),
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
                wallet_id INTEGER REFERENCES wallets(id),
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
                from_wallet_id INTEGER REFERENCES wallets(id) ON DELETE RESTRICT,
                to_wallet_id INTEGER REFERENCES wallets(id) ON DELETE RESTRICT,
                amount NUMERIC(15, 2) NOT NULL CHECK(amount > 0),
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for transfers
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_user ON transfers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_from_wallet ON transfers(from_wallet_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_to_wallet ON transfers(to_wallet_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers(date)")

        # ── Debts & Receivables ────────────────────────────────────

        # Main debts table (receivables + payables)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                type VARCHAR(20) NOT NULL CHECK(type IN ('receivable', 'payable')),
                counterparty_name VARCHAR(255) NOT NULL,
                counterparty_type VARCHAR(50) NOT NULL DEFAULT 'person'
                    CHECK(counterparty_type IN ('person','company','bank','merchant','family','friend','other')),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                original_amount NUMERIC(15, 2) NOT NULL CHECK(original_amount > 0),
                remaining_amount NUMERIC(15, 2) NOT NULL CHECK(remaining_amount >= 0),
                currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
                issue_date DATE NOT NULL,
                due_date DATE,
                status VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK(status IN ('draft','active','partially_paid','settled','overdue','cancelled','written_off')),
                priority VARCHAR(20) NOT NULL DEFAULT 'normal'
                    CHECK(priority IN ('low','normal','high','urgent')),
                reference_type VARCHAR(50),
                reference_id INTEGER,
                wallet_id INTEGER REFERENCES wallets(id),
                has_interest BOOLEAN NOT NULL DEFAULT FALSE,
                interest_type VARCHAR(20) CHECK(interest_type IN ('simple','compound','fixed')),
                interest_rate NUMERIC(8, 4),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_user ON debts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_user_status ON debts(user_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_user_type ON debts(user_id, type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_due_date ON debts(due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_counterparty ON debts(user_id, counterparty_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_reference ON debts(reference_type, reference_id)")

        # Debt payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debt_payments (
                id SERIAL PRIMARY KEY,
                debt_id INTEGER NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
                transaction_id INTEGER REFERENCES transactions(id),
                amount NUMERIC(15, 2) NOT NULL CHECK(amount > 0),
                payment_date DATE NOT NULL,
                payment_method VARCHAR(50) DEFAULT 'cash',
                wallet_id INTEGER REFERENCES wallets(id),
                note TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debt_payments_debt ON debt_payments(debt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debt_payments_date ON debt_payments(payment_date)")

        # Debt status history for audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debt_status_history (
                id SERIAL PRIMARY KEY,
                debt_id INTEGER NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
                old_status VARCHAR(20),
                new_status VARCHAR(20) NOT NULL,
                changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_debt_status_history_debt ON debt_status_history(debt_id)")

        # ── Contacts ───────────────────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                email VARCHAR(255),
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id)")

        # ── Tags ───────────────────────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(100) NOT NULL,
                color VARCHAR(20),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id)")

        # ── Labels ─────────────────────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(100) NOT NULL,
                color VARCHAR(20),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_user ON labels(user_id)")

        # ── Junction: transaction_tags ──────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_tags (
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (transaction_id, tag_id)
            )
        """)

        # ── Junction: transaction_labels ────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_labels (
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
                PRIMARY KEY (transaction_id, label_id)
            )
        """)

        # ── Junction: wallet_labels ─────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_labels (
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
                PRIMARY KEY (wallet_id, label_id)
            )
        """)

        # ── Accounts (sources inside wallets) ─────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                account_type VARCHAR(30) NOT NULL DEFAULT 'cash'
                    CHECK(account_type IN ('cash','bank','card','savings','wallet','other')),
                bank_type VARCHAR(50) DEFAULT 'cash',
                amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
                currency VARCHAR(3) NOT NULL DEFAULT 'IRR',
                icon VARCHAR(50),
                description TEXT,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_id, name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_wallet ON accounts(wallet_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_wallet_active ON accounts(wallet_id, deleted_at)")

        # ── Migration: remove currency from accounts (inherited from wallet) ──
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'accounts' AND column_name = 'currency'
        """)
        if cursor.fetchone() is not None:
            cursor.execute("ALTER TABLE accounts DROP COLUMN currency")
            print("[DB] Dropped 'currency' column from accounts (inherited from wallet)")

        # Wallet members (shared wallet access)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_members (
                id SERIAL PRIMARY KEY,
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL DEFAULT 'viewer' CHECK(role IN ('owner','editor','viewer')),
                joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                invited_by INTEGER REFERENCES users(id),
                UNIQUE(wallet_id, user_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_members_user ON wallet_members(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_members_wallet ON wallet_members(wallet_id)")

        # ── Wallet invitations ────────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_invitations (
                id SERIAL PRIMARY KEY,
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                inviter_id INTEGER NOT NULL REFERENCES users(id),
                invitee_id INTEGER NOT NULL REFERENCES users(id),
                role VARCHAR(20) NOT NULL DEFAULT 'viewer' CHECK(role IN ('editor','viewer')),
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','revoked')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_id, invitee_id, status)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_invitations_invitee ON wallet_invitations(invitee_id, status)")

        # ── Wallet activity log ───────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_activity_log (
                id SERIAL PRIMARY KEY,
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                action VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50),
                entity_id INTEGER,
                details JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_activity_wallet ON wallet_activity_log(wallet_id, created_at)")

        # ── Exchange rates (manual) ───────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                from_currency VARCHAR(3) NOT NULL,
                to_currency VARCHAR(3) NOT NULL,
                rate NUMERIC(18, 8) NOT NULL CHECK(rate > 0),
                effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, from_currency, to_currency, effective_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange_rates_user_currencies ON exchange_rates(user_id, from_currency, to_currency)")

        # ── User preferences ──────────────────────────────────────────

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                preferred_currency VARCHAR(3) NOT NULL DEFAULT 'IRR',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure legacy tables contain soft-delete support
        for table_name, column_name, definition in (
            ("transactions", "reference_type", "TEXT"),
            ("transactions", "reference_id", "INTEGER"),
        ):
            _ensure_column(cursor, table_name, column_name, definition)

        for table_name in (
            "categories",
            "wallets",
            "transactions",
            "transaction_items",
            "installment_plans",
            "installments",
            "checks",
            "transfers",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "debts",
            "debt_payments",
            "contacts",
            "tags",
            "labels",
            "accounts",
            "wallet_invitations",
        ):
            _ensure_column(cursor, table_name, "deleted_at", "TIMESTAMP")

        # ── Categories: add parent_id for tree structure ────────────────
        _ensure_column(cursor, "categories", "parent_id", "INTEGER REFERENCES categories(id) ON DELETE SET NULL")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)")

        # ── Debts: add category_id so payments can register transactions ──
        _ensure_column(cursor, "debts", "category_id", "INTEGER REFERENCES categories(id) ON DELETE SET NULL")

        for table_name in (
            "users",
            "categories",
            "wallets",
            "transactions",
            "transaction_items",
            "installment_plans",
            "installments",
            "checks",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "transfers",
            "debts",
            "debt_payments",
            "debt_status_history",
            "contacts",
            "tags",
            "labels",
            "accounts",
            "wallet_members",
            "wallet_invitations",
            "wallet_activity_log",
            "exchange_rates",
            "user_preferences",
        ):
            _ensure_column(cursor, table_name, "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
            _ensure_column(cursor, table_name, "updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")

        for table_name in (
            "users",
            "categories",
            "wallets",
            "transactions",
            "transaction_items",
            "installment_plans",
            "installments",
            "checks",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "transfers",
            "debts",
            "debt_payments",
            "debt_status_history",
            "contacts",
            "tags",
            "labels",
            "accounts",
            "wallet_members",
            "wallet_invitations",
            "wallet_activity_log",
            "exchange_rates",
            "user_preferences",
        ):
            _ensure_updated_at_trigger(cursor, table_name)

        # 2FA (TOTP) support for users
        _ensure_column(cursor, "users", "totp_secret", "VARCHAR(255)")
        _ensure_column(cursor, "users", "totp_enabled", "BOOLEAN NOT NULL DEFAULT FALSE")

        # Registration approval and admin role
        _ensure_column(cursor, "users", "is_admin", "BOOLEAN NOT NULL DEFAULT FALSE")
        _ensure_column(cursor, "users", "is_approved", "BOOLEAN NOT NULL DEFAULT FALSE")
        _ensure_column(cursor, "users", "is_active", "BOOLEAN NOT NULL DEFAULT TRUE")
        _ensure_column(cursor, "users", "display_name", "VARCHAR(255)")
        _ensure_column(cursor, "users", "email", "VARCHAR(255)")
        _ensure_column(cursor, "wallets", "currency", "VARCHAR(3) NOT NULL DEFAULT 'IRR'")
        _ensure_column(cursor, "wallets", "wallet_type", "VARCHAR(20) NOT NULL DEFAULT 'personal'")
        _ensure_column(cursor, "wallets", "icon", "VARCHAR(50)")
        _ensure_column(cursor, "wallets", "description", "TEXT")
        _ensure_column(cursor, "wallets", "variant", "VARCHAR(30)")

        # Accounts columns on transactions/transfers
        _ensure_column(cursor, "transactions", "account_id", "INTEGER REFERENCES accounts(id)")
        _ensure_column(cursor, "transactions", "is_private", "BOOLEAN NOT NULL DEFAULT FALSE")
        _ensure_column(cursor, "transfers", "from_account_id", "INTEGER REFERENCES accounts(id)")
        _ensure_column(cursor, "transfers", "to_account_id", "INTEGER REFERENCES accounts(id)")

        # Migration: transfers are now between accounts within a wallet, not between wallets
        # Make wallet columns nullable (derived from accounts) and fix CHECK constraint
        cursor.execute("""
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'transfers'::regclass AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%from_wallet_id%to_wallet_id%'
        """)
        old_check = cursor.fetchone()
        if old_check:
            cursor.execute(f"ALTER TABLE transfers DROP CONSTRAINT {old_check['conname']}")
            print(f"[DB] Dropped old transfers CHECK constraint: {old_check['conname']}")

        # Make wallet columns nullable
        cursor.execute("ALTER TABLE transfers ALTER COLUMN from_wallet_id DROP NOT NULL")
        cursor.execute("ALTER TABLE transfers ALTER COLUMN to_wallet_id DROP NOT NULL")

        # Add account-level CHECK constraint
        cursor.execute("""
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'transfers'::regclass AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%from_account_id%to_account_id%'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE transfers ADD CONSTRAINT transfers_different_accounts CHECK(from_account_id IS NULL OR to_account_id IS NULL OR from_account_id != to_account_id)")
            print("[DB] Added transfers CHECK(from_account_id != to_account_id)")

        # Indexes for new columns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_from_account ON transfers(from_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_to_account ON transfers(to_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_private ON transactions(wallet_id, is_private) WHERE is_private = TRUE")

        for table_name in (
            "categories",
            "wallets",
            "transactions",
            "transaction_items",
            "transfers",
            "budget_periods",
            "budget_items",
            "financial_events",
            "financial_event_instances",
            "users",
            "debts",
            "debt_payments",
            "debt_status_history",
            "contacts",
            "tags",
            "labels",
            "accounts",
            "wallet_members",
            "wallet_invitations",
            "wallet_activity_log",
            "exchange_rates",
            "user_preferences",
        ):
            cursor.execute(f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            cursor.execute(f"UPDATE {table_name} SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        # Seed wallet_members for existing wallets (owner role)
        cursor.execute("""
            INSERT INTO wallet_members (wallet_id, user_id, role)
            SELECT w.id, w.user_id, 'owner' FROM wallets w
            WHERE NOT EXISTS (
                SELECT 1 FROM wallet_members wm WHERE wm.wallet_id = w.id AND wm.user_id = w.user_id
            )
        """)

        # ── Migration: create default accounts for existing wallets ──
        # Only run if wallets still has bank_type and amount columns (legacy)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'wallets' AND column_name IN ('bank_type', 'amount')
        """)
        legacy_cols = {row['column_name'] for row in cursor.fetchall()}

        if 'bank_type' in legacy_cols and 'amount' in legacy_cols:
            cursor.execute("""
                INSERT INTO accounts (wallet_id, name, account_type, bank_type, amount, icon, description, is_default, sort_order)
                SELECT
                    w.id,
                    w.name,
                    CASE WHEN w.bank_type = 'cash' THEN 'cash' ELSE 'bank' END,
                    w.bank_type,
                    w.amount,
                    w.icon,
                    w.description,
                    TRUE,
                    0
                FROM wallets w
                WHERE w.deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM accounts a WHERE a.wallet_id = w.id AND a.is_default = TRUE
                  )
            """)

            # Drop legacy columns from wallets (balances now live on accounts)
            cursor.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS amount")
            cursor.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS bank_type")
            print("[DB] Dropped legacy 'amount' and 'bank_type' columns from wallets")

        # Back-fill transactions.account_id from default accounts
        cursor.execute("""
            UPDATE transactions t
            SET account_id = a.id
            FROM accounts a
            WHERE a.wallet_id = t.wallet_id
              AND a.is_default = TRUE
              AND t.account_id IS NULL
              AND t.wallet_id IS NOT NULL
        """)

        # Back-fill transfers.from_account_id
        cursor.execute("""
            UPDATE transfers t
            SET from_account_id = a.id
            FROM accounts a
            WHERE a.wallet_id = t.from_wallet_id
              AND a.is_default = TRUE
              AND t.from_account_id IS NULL
              AND t.from_wallet_id IS NOT NULL
        """)

        # Back-fill transfers.to_account_id
        cursor.execute("""
            UPDATE transfers t
            SET to_account_id = a.id
            FROM accounts a
            WHERE a.wallet_id = t.to_wallet_id
              AND a.is_default = TRUE
              AND t.to_account_id IS NULL
              AND t.to_wallet_id IS NOT NULL
        """)

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

        # Indexes for commitments
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installment_plans_user_status ON installment_plans(user_id, status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_installments_plan_status_due ON installments(plan_id, status, due_date)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checks_user_status_due ON checks(user_id, status, due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_reference ON transactions(reference_type, reference_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_reference_id_only ON transactions(reference_id)")
        
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
