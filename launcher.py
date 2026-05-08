#!/usr/bin/env python3
"""
Single entry point for the standalone Accounting System.

Starts the Flask API in a background thread and launches the TUI
in the main thread.  When the TUI exits the API thread stops
automatically (daemon=True).
"""

import load_env  # noqa: F401 — must be first

import sys
import threading
import time
import urllib.request
import urllib.error


def _run_api(host: str, port: int) -> None:
    """Run the Flask API server (called in a daemon thread)."""
    from app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=False, use_reloader=False)


def _wait_for_api(host: str, port: int, timeout: float = 30.0) -> bool:
    """Poll until the API responds or timeout is reached."""
    url = f"http://{host}:{port}/auth/me?username=__healthcheck__"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            resp.read()
            return True
        except urllib.error.HTTPError as exc:
            # 404/400 from /auth/me means the API is up, just no such user
            if exc.code in (400, 404):
                return True
            time.sleep(0.3)
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.3)
    return False


def main() -> None:
    import os

    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "5000"))

    # Start API in a daemon thread
    api_thread = threading.Thread(target=_run_api, args=(host, port), daemon=True)
    api_thread.start()

    print(f"Starting API on {host}:{port} ...")
    if not _wait_for_api(host, port):
        print("ERROR: API failed to start within 30 seconds.", file=sys.stderr)
        sys.exit(1)
    print("API ready.")

    # Launch TUI in the main thread
    from tui.app import AccountingApp

    app = AccountingApp()
    app.run()


if __name__ == "__main__":
    main()
