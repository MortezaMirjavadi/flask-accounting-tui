"""Custom widgets for the TUI."""

import io

import qrcode
from textual.widgets import Static


class QRCodeWidget(Static):
    """Widget to display a QR code as ASCII art in the terminal."""

    DEFAULT_CSS = """
    QRCodeWidget {
        width: auto;
        height: auto;
        content-align: center middle;
        text-align: center;
        padding: 0 1;
    }
    """

    def __init__(self, data: str = "", **kwargs):
        self._qr_data = data
        super().__init__("", **kwargs)
        if data:
            self.set_data(data)

    def set_data(self, data: str) -> None:
        """Update the QR code with new data."""
        self._qr_data = data
        if not data:
            self.update("")
            return
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(data)
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        f.seek(0)
        self.update(f.read())
