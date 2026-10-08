"""API utility functions."""


def extract_items(data):
    """Extract list items from either a plain list or a paginated response dict."""
    if isinstance(data, dict) and "items" in data:
        return data["items"] or []
    return data or []


def format_toman(amount):
    """Format a number as Toman (Persian currency)."""
    try:
        return f"{float(amount):,.0f} Toman"
    except (TypeError, ValueError):
        return "0 Toman"


def handle_response(resp):
    """Handle API response and return (data, error) tuple."""
    if resp is None:
        return None, "Network error"
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    if not resp.ok:
        err_text = str(data)
        if err_text.strip().startswith("<"):
            err_text = f"Server error {resp.status_code}"
        return None, err_text
    return data, None
