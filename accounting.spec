# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Accounting System (macOS single-folder)."""

import os

block_cipher = None

# ---------------------------------------------------------------------------
# Hidden imports — modules loaded dynamically via importlib or at runtime
# ---------------------------------------------------------------------------
hidden_imports = [
    # Flask internals
    "flask",
    "flask.json",
    "jinja2",
    "werkzeug",
    "werkzeug.serving",
    "werkzeug.debug",
    # psycopg2
    "psycopg2",
    "psycopg2.extras",
    "psycopg2.pool",
    # Textual
    "textual",
    "textual.widgets",
    "textual.widgets._tree",
    "textual.widgets._data_table",
    "textual.widgets._select",
    "textual.widgets._input",
    "textual.widgets._button",
    "textual.widgets._checkbox",
    "textual.widgets._static",
    "textual.widgets._label",
    "textual.widgets._rule",
    "textual.widgets._header",
    "textual.widgets._footer",
    "textual.widgets._content_switcher",
    "textual.widgets._list_item",
    "textual.widgets._list_view",
    "textual.widgets._digits",
    "textual.widgets._text_area",
    "textual.containers",
    "textual.screen",
    "textual.app",
    "textual.binding",
    "textual.css",
    "textual.message",
    "textual.reactive",
    # App routes (loaded by register_blueprints)
    "app.routes",
    "app.routes.auth",
    "app.routes.categories",
    "app.routes.sources",
    "app.routes.transactions",
    "app.routes.budget",
    "app.routes.reports",
    "app.routes.settings",
    "app.routes.installments",
    "app.routes.checks",
    # App services
    "app.services",
    "app.services.auth_service",
    "app.models",
    "app.models.validators",
    "app.utils",
    "app.utils.helpers",
    "app.utils.decorators",
    # TUI screens (loaded dynamically by sidebar_menu)
    "tui.screens",
    "tui.screens.base",
    "tui.screens.auth",
    "tui.screens.transactions",
    "tui.screens.sources",
    "tui.screens.categories",
    "tui.screens.budget",
    "tui.screens.checks",
    "tui.screens.installments",
    "tui.screens.reports",
    "tui.screens.users",
    "tui.screens.settings",
    "tui.calendar_view",
    "tui.jalali_date_picker",
    # TUI widgets
    "tui.widgets",
    "tui.widgets.shared",
    "tui.widgets.custom",
    # TUI other
    "tui.api",
    "tui.api.client",
    "tui.config",
    "tui.sidebar_menu",
    "tui.app",
    "tui.main",
    # Third-party
    "jdatetime",
    "pyotp",
    "qrcode",
    "requests",
    "dotenv",
    "load_env",
    "database",
]

# ---------------------------------------------------------------------------
# Data files to bundle next to the executable
# ---------------------------------------------------------------------------
datas = []
for env_file in [".env", ".env.staging", ".env.production"]:
    if os.path.exists(env_file):
        datas.append((env_file, "."))

# ---------------------------------------------------------------------------
a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "pandas", "PyQt5", "PySide6", "PyQt6", "PySide2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AccountingSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AccountingSystem",
)
