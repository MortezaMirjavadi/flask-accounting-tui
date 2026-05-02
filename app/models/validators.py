from app.utils.helpers import jalali_to_gregorian

def validate_user_payload(data):
    """Validate user registration/login payload."""
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")
    
    return {"username": username, "password": password}


def validate_category_payload(data):
    """Validate category payload."""
    name = data.get("name", "").strip()
    cat_type = data.get("type", "").strip().lower()
    
    if not name:
        raise ValueError("Category name is required")
    if cat_type not in ("income", "cost"):
        raise ValueError("Category type must be 'income' or 'cost'")
    
    return {"name": name, "type": cat_type}


def validate_source_payload(data):
    """Validate source payload."""
    name = data.get("name", "").strip()
    amount = data.get("amount")
    
    if not name:
        raise ValueError("Source name is required")
    try:
        amount = float(amount)
        if amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid non-negative amount is required")
    
    return {"name": name, "amount": amount}


def validate_transaction_payload(data):
    """Validate transaction payload."""
    date = data.get("date", "").strip()
    amount = data.get("amount")
    category_id = data.get("category_id")
    source_id = data.get("source_id")
    description = data.get("description", "").strip()
    
    if not date:
        raise ValueError("Date is required")

    gregorian_date = jalali_to_gregorian(date)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid positive amount is required")
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("Valid category_id is required")

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
        "description": description
    }


def validate_budget_period_payload(data):
    """Validate budget period payload."""
    year = data.get("year")
    month = data.get("month")
    
    try:
        year = int(year)
        if year < 1300 or year > 1500:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid year (1300-1500) is required")
    
    try:
        month = int(month)
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid month (1-12) is required")
    
    return {"year": year, "month": month}


def validate_budget_item_payload(data):
    """Validate budget item payload."""
    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError("Invalid payload")

    category_id = data.get("category_id")
    planned_amount = data.get("planned_amount")
    notes = (data.get("notes", "") or "").strip() or None
    
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("Valid category_id is required")
    
    try:
        planned_amount = float(planned_amount)
        if planned_amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid non-negative planned_amount is required")
    
    return {
        "category_id": category_id,
        "planned_amount": planned_amount,
        "notes": notes
    }
