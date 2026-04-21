import jdatetime


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


def validate_category_payload(data: dict) -> dict:
    name = data.get("name", "").strip()
    cat_type = data.get("type", "").strip().lower()
    if not name:
        raise ValueError("Category name is required")
    if cat_type not in ("income", "cost"):
        raise ValueError("Category type must be 'income' or 'cost'")
    return {"name": name, "type": cat_type}


def validate_source_payload(data: dict) -> dict:
    name = data.get("name", "").strip()
    if not name:
        raise ValueError("Source name is required")
    
    amount = data.get("amount", 0)
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("Amount must be a number")
    
    return {"name": name, "amount": amount}


def validate_transaction_payload(data: dict) -> dict:
    date_str = data.get("date", "").strip()
    amount = data.get("amount")
    category_id = data.get("category_id")
    source_id = data.get("source_id")
    description = data.get("description", "").strip()

    if not date_str:
        raise ValueError("Date is required")
    # Convert Jalali to Gregorian for storage
    gregorian_date = jalali_to_gregorian(date_str)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Amount must be a positive number")

    if category_id is not None:
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            raise ValueError("category_id must be an integer")

    if source_id is not None:
        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            raise ValueError("source_id must be an integer")

    return {
        "date": gregorian_date,
        "amount": amount,
        "category_id": category_id,
        "source_id": source_id,
        "description": description,
    }


def validate_user_payload(data: dict) -> dict:
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username:
        raise ValueError("Username is required")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not password:
        raise ValueError("Password is required")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")
    return {"username": username, "password": password}


def validate_budget_period_payload(data: dict) -> dict:
    year = data.get("year")
    month = data.get("month")
    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValueError("Year must be an integer")
    if year < 1300:
        raise ValueError("Year must be >= 1300")
    try:
        month = int(month)
    except (TypeError, ValueError):
        raise ValueError("Month must be an integer")
    if month < 1 or month > 12:
        raise ValueError("Month must be 1-12")
    return {"year": year, "month": month}


def validate_budget_item_payload(data: dict) -> dict:
    category_id = data.get("category_id")
    planned_amount = data.get("planned_amount")
    notes = (data.get("notes") or "").strip()
    # notes_value = data.get("notes", "")
    # notes = notes_value.strip() if notes_value else ""
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("category_id must be an integer")
    try:
        planned_amount = float(planned_amount)
        if planned_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Planned amount must be positive")
    return {"category_id": category_id, "planned_amount": planned_amount, "notes": notes}
