# PostgreSQL Migration - Quick Start Guide

## ⚡ Fast Setup (5 minutes)

### 1. Install PostgreSQL
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# Verify installation
pg_isready
```

### 2. Create Database
```bash
createdb terminal_accounting
```

### 3. Configure Connection
Edit `.env` file:
```bash
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/terminal_accounting
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Application
```bash
# The app will auto-create tables on first run
python run_api.py
```

## 🔍 Quick Verification

```bash
# Test database connection
psql -U postgres -d terminal_accounting

# Inside psql:
\dt                    # List tables
\d users              # Describe users table
SELECT * FROM users;  # Query users
\q                    # Quit
```

## 🐛 Quick Troubleshooting

**Connection refused?**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

**Authentication failed?**
```bash
# Reset password
psql -U postgres
ALTER USER postgres PASSWORD 'newpassword';
\q

# Update .env with new password
```

**Database doesn't exist?**
```bash
createdb terminal_accounting
```

## 📊 Key Changes from SQLite

| Aspect | SQLite | PostgreSQL |
|--------|--------|------------|
| Connection | `sqlite3.connect()` | Connection pool |
| Parameters | `?` | `%s` |
| Auto-increment | `lastrowid` | `RETURNING id` |
| Money type | `REAL` | `NUMERIC(15,2)` |
| Date type | `TEXT` | `DATE` |

## 📚 Full Documentation

- **Setup Guide**: `MIGRATION_TO_POSTGRESQL.md`
- **Technical Details**: `POSTGRESQL_MIGRATION_SUMMARY.md`
- **Verification**: Run `python3 verify_migration.py`

## ✅ Success Indicators

- ✓ `python3 verify_migration.py` passes
- ✓ `psql -U postgres -d terminal_accounting` connects
- ✓ Application starts without errors
- ✓ Can create users and perform CRUD operations

## 🆘 Need Help?

1. Check PostgreSQL logs: `tail -f /usr/local/var/log/postgresql.log`
2. Review full migration guide: `MIGRATION_TO_POSTGRESQL.md`
3. Verify migration: `python3 verify_migration.py`
