# PostgreSQL Migration Guide

This application has been migrated from SQLite to PostgreSQL. Follow these steps to set up and run the application.

## Prerequisites

1. **PostgreSQL Installation**
   - Install PostgreSQL 12 or higher
   - macOS: `brew install postgresql`
   - Ubuntu: `sudo apt-get install postgresql postgresql-contrib`
   - Windows: Download from https://www.postgresql.org/download/

2. **Python Dependencies**
   - Install the updated requirements: `pip install -r requirements.txt`

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Start PostgreSQL service (if not already running)
# macOS: brew services start postgresql
# Ubuntu: sudo systemctl start postgresql

# Create database
createdb terminal_accounting

# Or using psql:
psql -U postgres
CREATE DATABASE terminal_accounting;
\q
```

### 2. Configure Database Connection

Edit the `.env` file with your PostgreSQL credentials:

```bash
# Option 1: Use full connection string
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/terminal_accounting

# Option 2: Use individual components
DB_HOST=localhost
DB_PORT=5432
DB_NAME=terminal_accounting
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Initialize Database Schema

The application will automatically create tables on first run. You can also manually initialize:

```python
from database import init_db
init_db()
```

## Key Changes from SQLite

### Data Types
- `INTEGER` → `SERIAL` for auto-increment primary keys
- `REAL` → `NUMERIC(15, 2)` for monetary amounts (better precision)
- `TEXT` → `VARCHAR` or `TEXT`
- Date fields now use PostgreSQL `DATE` type
- Timestamp fields use PostgreSQL `TIMESTAMP` type

### SQL Syntax
- Parameter placeholders: `?` → `%s`
- `AUTOINCREMENT` → `SERIAL` or `GENERATED ALWAYS AS IDENTITY`
- `CURRENT_TIMESTAMP` remains the same
- `lastrowid` → `RETURNING id` clause

### Connection Management
- Connection pooling implemented using `psycopg2.pool.SimpleConnectionPool`
- Connections must be explicitly returned to pool using `release_connection(conn)`
- Row factory changed from `sqlite3.Row` to `psycopg2.extras.RealDictCursor`

## Migration from Existing SQLite Data

If you have existing SQLite data, you can migrate it:

### Option 1: Using pgloader (Recommended)

```bash
# Install pgloader
# macOS: brew install pgloader
# Ubuntu: sudo apt-get install pgloader

# Migrate data
pgloader ./data/accounting.db postgresql://postgres:password@localhost/terminal_accounting
```

### Option 2: Manual Export/Import

```bash
# Export from SQLite
sqlite3 ./data/accounting.db .dump > dump.sql

# Edit dump.sql to convert SQLite syntax to PostgreSQL
# Then import:
psql -U postgres -d terminal_accounting -f dump.sql
```

### Option 3: Python Script

```python
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# Connect to both databases
sqlite_conn = sqlite3.connect('./data/accounting.db')
sqlite_conn.row_factory = sqlite3.Row
pg_conn = psycopg2.connect("postgresql://postgres:password@localhost/terminal_accounting")

# Migrate each table
tables = ['users', 'categories', 'sources', 'transactions', 'budget_periods', 'budget_items', 'transfers', 'financial_events', 'financial_event_instances']

for table in tables:
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Get data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()
    
    if rows:
        columns = rows[0].keys()
        values = [tuple(row) for row in rows]
        
        # Insert into PostgreSQL
        cols = ', '.join(columns)
        query = f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(pg_cursor, query, values)
    
    pg_conn.commit()

sqlite_conn.close()
pg_conn.close()
```

## Running the Application

```bash
# Start the Flask API
python run_api.py

# Or start the TUI
python run_tui.py
```

## Testing

For testing, the application uses a separate test database:

```bash
# Create test database
createdb terminal_accounting_test

# Run tests
pytest
```

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -U postgres -d terminal_accounting
```

### Permission Issues

```bash
# Grant permissions
psql -U postgres
GRANT ALL PRIVILEGES ON DATABASE terminal_accounting TO your_user;
\q
```

### Reset Database

```bash
# Drop and recreate
dropdb terminal_accounting
createdb terminal_accounting
python -c "from database import init_db; init_db()"
```

## Performance Considerations

- Connection pooling is configured with min=1, max=20 connections
- Indexes are automatically created for frequently queried columns
- Use `EXPLAIN ANALYZE` to optimize slow queries
- Consider adding more indexes for large datasets

## Backup and Restore

```bash
# Backup
pg_dump -U postgres terminal_accounting > backup.sql

# Restore
psql -U postgres -d terminal_accounting < backup.sql
```

## Additional Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- psycopg2 Documentation: https://www.psycopg.org/docs/
- Connection Pooling: https://www.psycopg.org/docs/pool.html
