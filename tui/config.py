"""Application configuration and constants."""

import os

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

# Persian month names mapping
PERSIAN_MONTHS = [
    ("1 - Farvardin", 1),
    ("2 - Ordibehesht", 2),
    ("3 - Khordad", 3),
    ("4 - Tir", 4),
    ("5 - Mordad", 5),
    ("6 - Shahrivar", 6),
    ("7 - Mehr", 7),
    ("8 - Aban", 8),
    ("9 - Azar", 9),
    ("10 - Dey", 10),
    ("11 - Bahman", 11),
    ("12 - Esfand", 12),
]


def get_persian_month_name(month_num: int) -> str:
    """Get Persian month name from month number."""
    month_names = {
        1: "Farvardin", 2: "Ordibehesht", 3: "Khordad",
        4: "Tir", 5: "Mordad", 6: "Shahrivar",
        7: "Mehr", 8: "Aban", 9: "Azar",
        10: "Dey", 11: "Bahman", 12: "Esfand"
    }
    return month_names.get(month_num, str(month_num))
