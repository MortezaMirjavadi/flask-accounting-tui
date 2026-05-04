import psycopg2
from flask import request, jsonify
from database import get_connection, release_connection
import jdatetime

def row_to_dict(row):
    """Convert database row to dictionary."""
    if row is None:
        return None
    return dict(row)


def get_user_id_from_request():
    """Extract username from request and return user_id."""
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return None, (jsonify({"error": "Username is required"}), 400)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        
        if row is None:
            return None, (jsonify({"error": "User not found"}), 404)
        return row["id"], None
    finally:
        cursor.close()
        release_connection(conn)


def jalali_to_gregorian(date_str: str) -> str:
    """Convert Jalali date (YYYY-MM-DD) to Gregorian (YYYY-MM-DD).

    Valid Jalali years: 1300-1500 (covers ~1921-2071 Gregorian)
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date is required")

    date_str = date_str.strip()
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError("Date must be in YYYY-MM-DD format")

    try:
        year, month, day = map(int, parts)
    except ValueError:
        raise ValueError("Date must be numeric in YYYY-MM-DD format")

    # Validate year range (Jalali years 1300-1500 are reasonable)
    if year < 1300 or year > 1500:
        raise ValueError(f"Jalali year must be between 1300 and 1500, got {year}")

    # Validate month
    if month < 1 or month > 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")

    # Validate day (basic check, will let jalali library handle exact day limits)
    if day < 1 or day > 31:
        raise ValueError(f"Day must be between 1 and 31, got {day}")

    jalali_date = jdatetime.date(year, month, day)
    gregorian_date = jalali_date.togregorian()
    return gregorian_date.strftime("%Y-%m-%d")

def gregorian_to_jalali(date_str: str) -> str:
    """Convert Gregorian date (YYYY-MM-DD) to Jalali (YYYY-MM-DD)."""
    if isinstance(date_str, str):
        parts = date_str.split("-")
        if len(parts) != 3:
            raise ValueError("Date must be in YYYY-MM-DD format")
        year, month, day = map(int, parts)
        gregorian_date = __import__("datetime").date(year, month, day)
    else:
        # Handle date objects directly
        gregorian_date = date_str
    jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
    return jalali_date.strftime("%Y-%m-%d")


def gregorian_to_jalali_with_timestamp(timestamp_str: str) -> str:
    """Convert Gregorian timestamp to Jalali date + time string.

    Handles multiple formats:
    - ISO: 2026-05-01 12:46:30.004944
    - HTTP (RFC 7231): Fri, 01 May 2026 12:46:30 GMT
    """
    if not timestamp_str:
        return ""

    from datetime import datetime

    ts = timestamp_str.strip()

    # Try ISO format first: YYYY-MM-DD ...
    if ts[:4].isdigit() and ts[4] == "-":
        date_part = ts.split()[0]
        time_part = ts[len(date_part):].strip()
        jalali_date = gregorian_to_jalali(date_part)
        if time_part:
            return f"{jalali_date} {time_part}"
        return jalali_date

    # Try HTTP/RFC 7231 format: Fri, 01 May 2026 12:46:30 GMT
    try:
        # Parse with datetime.strptime for RFC 7231
        dt = datetime.strptime(ts, "%a, %d %b %Y %H:%M:%S %Z")
        jalali_date = gregorian_to_jalali(dt.date())
        time_part = dt.strftime("%H:%M:%S")
        return f"{jalali_date} {time_part}"
    except ValueError:
        pass

    # Fallback: try any format datetime can parse
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        jalali_date = gregorian_to_jalali(dt.date())
        time_part = dt.strftime("%H:%M:%S")
        return f"{jalali_date} {time_part}"
    except ValueError:
        pass

    # Last resort: return as-is
    return ts


def get_persian_month_name(month):
    """Get Persian month name from month number."""
    persian_months = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد",
        4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر",
        10: "دی", 11: "بهمن", 12: "اسفند"
    }
    return persian_months.get(month, "")


def format_toman(amount):
    """Format amount in Toman."""
    return f"{amount:,.0f} تومان"
