#!/usr/bin/env python3
"""Verify PostgreSQL migration completeness."""

import os
import sys
from pathlib import Path

def check_file_for_patterns(filepath, patterns):
    """Check if file contains any of the given patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            found = []
            for pattern in patterns:
                if pattern in content:
                    found.append(pattern)
            return found
    except Exception as e:
        return []

def main():
    print("=" * 60)
    print("PostgreSQL Migration Verification")
    print("=" * 60)
    
    # Patterns that should NOT exist in migrated code
    sqlite_patterns = [
        'import sqlite3',
        'sqlite3.connect',
        'sqlite3.Row',
        'sqlite3.IntegrityError',
        '.lastrowid',
        'AUTOINCREMENT',
        'PRAGMA',
    ]
    
    # Files to check
    python_files = []
    for pattern in ['**/*.py']:
        python_files.extend(Path('.').glob(pattern))
    
    # Exclude certain directories
    exclude_dirs = {'venv', '.venv', 'env', '__pycache__', '.git', 'node_modules', 'build', 'dist'}
    python_files = [f for f in python_files if not any(ex in f.parts for ex in exclude_dirs)]
    python_files = [f for f in python_files if f.name != 'verify_migration.py']
    
    issues_found = False
    
    print("\nChecking for SQLite remnants...\n")
    
    for filepath in python_files:
        found = check_file_for_patterns(filepath, sqlite_patterns)
        if found:
            issues_found = True
            print(f"⚠️  {filepath}")
            for pattern in found:
                print(f"   - Found: {pattern}")
    
    if not issues_found:
        print("✓ No SQLite remnants found!")
    
    print("\n" + "=" * 60)
    print("Checking for PostgreSQL imports...\n")
    
    # Check that key files have psycopg2
    key_files = [
        'database.py',
        'app/services/auth_service.py',
        'app/routes/categories.py',
        'app/routes/sources.py',
        'app/routes/transactions.py',
    ]
    
    all_good = True
    for filepath in key_files:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
                if 'psycopg2' in content or 'from database import' in content:
                    print(f"✓ {filepath}")
                else:
                    print(f"⚠️  {filepath} - Missing psycopg2 import")
                    all_good = False
    
    print("\n" + "=" * 60)
    print("Checking configuration files...\n")
    
    # Check .env
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.read()
            if 'DATABASE_URL' in env_content or 'DB_HOST' in env_content:
                print("✓ .env has PostgreSQL configuration")
            else:
                print("⚠️  .env missing PostgreSQL configuration")
                all_good = False
    
    # Check requirements.txt
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            req_content = f.read()
            if 'psycopg2' in req_content:
                print("✓ requirements.txt includes psycopg2")
            else:
                print("⚠️  requirements.txt missing psycopg2")
                all_good = False
    
    print("\n" + "=" * 60)
    
    if not issues_found and all_good:
        print("\n✅ Migration verification PASSED!")
        print("\nNext steps:")
        print("1. Install PostgreSQL: brew install postgresql (macOS)")
        print("2. Create database: createdb terminal_accounting")
        print("3. Update .env with your PostgreSQL credentials")
        print("4. Install dependencies: pip install -r requirements.txt")
        print("5. Run the application")
        return 0
    else:
        print("\n⚠️  Migration verification found issues!")
        print("Please review the warnings above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
