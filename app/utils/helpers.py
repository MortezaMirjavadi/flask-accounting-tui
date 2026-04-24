import sqlite3
from flask import request, jsonify
from database import get_connection
import jdatetime

def row_to_dict(row):
    """Convert sqlite3.Row to dictionary."""
    return {key: row[key] for key in row.keys()}


def get_user_id_from_request():
    """Extract username from request and return user_id."""
    username = request.headers.get("X-Username", "").strip()
    if not username:
        username = request.args.get("username", "").strip()
    if not username:
        return None, (jsonify({"error": "Username is required"}), 400)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None, (jsonify({"error": "User not found"}), 404)
    return row["id"], None


def jalali_to_gregorian(date_str: str) -> str:
    """Convert Jalali date (YYYY-MM-DD) to Gregorian (YYYY-MM-DD)."""
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError("Date must be in YYYY-MM-DD format")
    year, month, day = map(int, parts)
    jalali_date = jdatetime.date(year, month, day)
    gregorian_date = jalali_date.togregorian()
    return gregorian_date.strftime("%Y-%m-%d")

def gregorian_to_jalali(date_str: str) -> str:
    """Convert Gregorian date (YYYY-MM-DD) to Jalali (YYYY-MM-DD)."""
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError("Date must be in YYYY-MM-DD format")
    year, month, day = map(int, parts)
    gregorian_date = __import__("datetime").date(year, month, day)
    jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
    return jalali_date.strftime("%Y-%m-%d")


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

