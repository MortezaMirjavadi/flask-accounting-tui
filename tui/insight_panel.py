"""Insights modal used by the financial calendar TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class InsightPanel(ModalScreen[bool]):
    """Display forecast insights in a focused side-style modal."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, insights: list[str], title: str = "Forecast Insights", **kwargs):
        super().__init__(**kwargs)
        self.insights = insights
        self.title = title

    def compose(self) -> ComposeResult:
        with Static(id="insight_modal"):
            yield Label(f"[bold]{self.title}[/bold]")
            if not self.insights:
                yield Static("No insights available for this period.")
            else:
                for idx, text in enumerate(self.insights, start=1):
                    yield Static(f"{idx}. {text}")
            yield Button("Close", variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:  # pragma: no cover - UI path
        self.dismiss(True)

    def action_dismiss(self):
        self.dismiss(True)
