"""Load environment-specific .env file based on APP_ENV."""

import os
from pathlib import Path
from dotenv import load_dotenv

_env = os.environ.get("APP_ENV", "").strip().lower()

if _env in ("staging", "production"):
    _env_file = Path(__file__).resolve().parent.parent / f".env.{_env}"
else:
    _env_file = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(_env_file, override=False)
