#!/usr/bin/env python3
"""Ultimate build script for macOS executable."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, **kwargs):
    """Run shell command."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def main():
    """Build standalone macOS application."""
    
    print("=" * 60)
    print("🏗️  Building Accounting System for macOS")
    print("=" * 60)
    
    # Paths
    project_root = Path(__file__).parent.resolve()
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    app_name = "AccountingSystem"
    app_bundle = dist_dir / f"{app_name}.app"
    
    # Clean
    print("\n🧹 Cleaning...")
    for d in [build_dir, dist_dir]:
        if d.exists():
            shutil.rmtree(d)
    
    # Create structure
    dist_dir.mkdir(parents=True)
    (dist_dir / "data").mkdir()
    
    # Method: Use Python's built-in zipapp for simple distribution
    print("\n📦 Method 1: Portable Python Package")
    
    # Create __main__.py for combined launcher
    combined_launcher = build_dir / "launcher"
    combined_launcher.mkdir(parents=True)
    
    (combined_launcher / "__main__.py").write_text('''
import os
import subprocess
import sys
import time

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    
    # Setup environment
    os.environ["DATABASE_PATH"] = os.path.join(base, "..", "..", "data", "accounting.db")
    os.environ["BASE_URL"] = "http://127.0.0.1:5000"
    
    # Ensure data dir exists
    os.makedirs(os.environ["DATABASE_PATH"], exist_ok=True)
    
    # Start API
    print("Starting API server...")
    api = subprocess.Popen([
        sys.executable, "-m", "app"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for API
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:5000/health", timeout=1)
            print("API ready!")
            break
        except:
            time.sleep(1)
    else:
        print("API failed to start")
        return 1
    
    # Start TUI
    print("Starting TUI...")
    tui = subprocess.call([sys.executable, "-m", "tui.main"])
    
    # Cleanup
    api.terminate()
    return 0

if __name__ == "__main__":
    sys.exit(main())
''')
    
    # Copy source
    for src in ["app", "tui", "database.py", "financial_calendar"]:
        src_path = project_root / src
        if src_path.exists():
            dst = combined_launcher / src
            if src_path.is_dir():
                shutil.copytree(src_path, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(src_path, dst)
    
    # Create requirements
    req_file = combined_launcher / "requirements.txt"
    req_file.write_text('''
flask>=2.0.0
werkzeug>=2.0.0
textual>=0.41.0
requests>=2.28.0
jdatetime>=4.0.0
python-dotenv>=1.0.0
''')
    
    # Create install script
    install_script = dist_dir / "INSTALL.command"
    install_script.write_text(f'''#!/bin/bash
cd "$(dirname "$0")"
echo "Installing Accounting System..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install from python.org"
    exit 1
fi

# Create virtual environment
python3 -m venv "{app_name}"
source "{app_name}/bin/activate"

# Install dependencies
pip install -r launcher/requirements.txt

# Create launcher script
cat > "{app_name}/Accounting System.command" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
source bin/activate
export DATABASE_PATH="$DIR/../data/accounting.db"
export BASE_URL=http://127.0.0.1:5000
python -m launcher
LAUNCHER
chmod +x "{app_name}/Accounting System.command"

# Create desktop shortcut
ln -sf "$PWD/{app_name}/Accounting System.command" "$HOME/Desktop/Accounting System"

echo ""
echo "✅ Installation complete!"
echo "Launch from: ~/Desktop/Accounting System"
echo ""
read -p "Press Enter to continue..."
''')
    os.chmod(install_script, 0o755)
    
    # Copy launcher to dist
    shutil.copytree(combined_launcher, dist_dir / "launcher")
    
    print("\n" + "=" * 60)
    print("✅ Build Complete!")
    print("=" * 60)
    print(f"\n📦 Output: {dist_dir}/")
    print("\n🚀 To distribute:")
    print("   1. Zip the 'dist' folder")
    print("   2. User runs: INSTALL.command")
    print("   3. Launches from: ~/Desktop/Accounting System")
    print("\n📁 User data will be stored in: ~/AccountingSystem/data/")


if __name__ == "__main__":
    main()
