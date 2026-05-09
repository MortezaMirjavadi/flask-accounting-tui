#!/usr/bin/env python3
"""Entry point for the Flask API server."""

import load_env  # noqa: F401 — must be first
import os
from app import create_app


def main():
    """Run the Flask API server."""
    app = create_app()
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
