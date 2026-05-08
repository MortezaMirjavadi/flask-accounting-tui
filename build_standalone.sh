#!/bin/bash
# Build standalone macOS distribution using PyInstaller.
#
# Usage:
#   ./build_standalone.sh
#
# Output:
#   dist/AccountingSystem/   — single-folder bundle
#   dist/AccountingSystem/AccountingSystem  — executable
#
# The .env, .env.staging, .env.production files are copied next to
# the executable so the user can edit them without touching source.
#
# Prerequisites:
#   pip install pyinstaller

set -euo pipefail
cd "$(dirname "$0")"

echo "=== Building standalone Accounting System ==="

# Clean previous build
rm -rf build dist

# Run PyInstaller
pyinstaller accounting.spec --noconfirm

# Copy .env files to dist (spec datas may not preserve them at root)
for f in .env .env.staging .env.production; do
    [ -f "$f" ] && cp "$f" "dist/AccountingSystem/"
done

echo ""
echo "=== Build complete ==="
echo ""
echo "Distribution: dist/AccountingSystem/"
echo "Executable:   dist/AccountingSystem/AccountingSystem"
echo ""
echo "To run:"
echo "  cd dist/AccountingSystem"
echo "  ./AccountingSystem"
echo ""
echo "To switch environment, edit .env next to the executable"
echo "or set APP_ENV=staging or APP_ENV=production before running."
