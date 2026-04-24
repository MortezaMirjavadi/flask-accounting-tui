#!/usr/bin/env python3
"""Entry point for the Flask API server."""

from app import create_app


def main():
    """Run the Flask API server."""
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
