"""Load environment-specific .env file based on APP_ENV.

This module is standalone (not part of the app package) so it can be
imported before anything else without triggering circular imports.

When running as a PyInstaller bundle, .env files are looked up next
to the executable.  When running from source, they are looked up next
to this script.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


_env = os.environ.get("APP_ENV", "").strip().lower()

if _env in ("staging", "production"):
    _env_file = _base_dir() / f".env.{_env}"
else:
    _env_file = _base_dir() / ".env"

load_dotenv(_env_file, override=False)
