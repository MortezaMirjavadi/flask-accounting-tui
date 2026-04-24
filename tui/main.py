"""Entry point for the TUI application."""

from tui.app import AccountingApp


def main():
    """Run the accounting TUI application."""
    app = AccountingApp()
    app.run()


if __name__ == "__main__":
    main()
