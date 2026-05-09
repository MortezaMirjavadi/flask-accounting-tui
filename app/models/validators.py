from app.utils.helpers import jalali_to_gregorian

def validate_user_payload(data):
    """Validate user registration/login payload."""
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    display_name = data.get("display_name", "").strip() or None
    email = data.get("email", "").strip() or None

    if email and "@" not in email:
        raise ValueError("Invalid email address")

    return {
        "username": username,
        "password": password,
        "display_name": display_name,
        "email": email,
    }


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


def validate_installment_plan_payload(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Invalid payload")

    title = (data.get("title") or "").strip()
    total_amount = data.get("total_amount")
    installment_count = data.get("installment_count")
    installment_amount = data.get("installment_amount")
    start_date = (data.get("start_date") or "").strip()
    due_day_of_month = data.get("due_day_of_month")
    category_id = data.get("category_id")
    source_id = data.get("source_id")
    status = (data.get("status") or "active").strip().lower()

    if not title:
        raise ValueError("title is required")

    try:
        total_amount = float(total_amount)
        if total_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid positive total_amount is required")

    try:
        installment_count = int(installment_count)
        if installment_count <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("installment_count must be greater than zero")

    if not start_date:
        raise ValueError("start_date is required")

    if due_day_of_month is None or due_day_of_month == "":
        due_day_of_month = int(start_date.split("-")[2]) if isinstance(start_date, str) else None
    else:
        try:
            due_day_of_month = int(due_day_of_month)
            if not 1 <= due_day_of_month <= 31:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("due_day_of_month must be an integer between 1 and 31")

    try:
        category_id = int(category_id)
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid category_id is required")

    if source_id is not None:
        try:
            source_id = int(source_id)
            if source_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("source_id must be a positive integer")

    if installment_amount is not None:
        try:
            installment_amount = float(installment_amount)
            if installment_amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("installment_amount must be greater than zero")

    if status not in ("active", "completed", "canceled"):
        raise ValueError("status must be active, completed, or canceled")

    return {
        "title": title,
        "total_amount": total_amount,
        "installment_count": installment_count,
        "installment_amount": installment_amount,
        "start_date": start_date,
        "due_day_of_month": due_day_of_month,
        "category_id": category_id,
        "source_id": source_id,
        "status": status,
    }


def validate_installment_payment_payload(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Invalid payload")

    installment_ids = data.get("installment_ids")
    paid_date = (data.get("paid_date") or "").strip()

    if installment_ids is None:
        raise ValueError("installment_ids is required")
    if isinstance(installment_ids, int):
        installment_ids = [installment_ids]
    if not isinstance(installment_ids, list) or len(installment_ids) == 0:
        raise ValueError("installment_ids must be a non-empty integer list")
    cleaned_ids = []
    for item in installment_ids:
        if item is None:
            raise ValueError("installment_ids must contain integers")
        try:
            item_id = int(item)
        except (TypeError, ValueError):
            raise ValueError("installment_ids must contain integers")
        if item_id <= 0:
            raise ValueError("installment_ids must contain positive integers")
        cleaned_ids.append(item_id)

    if paid_date:
        paid_date = jalali_to_gregorian(paid_date)
    else:
        paid_date = None

    return {"installment_ids": cleaned_ids, "paid_date": paid_date}


def validate_check_payload(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Invalid payload")

    check_type = (data.get("type") or "").strip().lower()
    if check_type not in ("issued", "received"):
        raise ValueError("type must be 'issued' or 'received'")

    check_number = (data.get("check_number") or "").strip() or None
    bank_name = (data.get("bank_name") or "").strip() or None
    amount = data.get("amount")
    issue_date = (data.get("issue_date") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    category_id = data.get("category_id")
    source_id = data.get("source_id")
    description = (data.get("description") or "").strip() or None

    if not issue_date:
        raise ValueError("issue_date is required")
    if not due_date:
        raise ValueError("due_date is required")

    issue_date = jalali_to_gregorian(issue_date)
    due_date = jalali_to_gregorian(due_date)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid positive amount is required")

    try:
        category_id = int(category_id)
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Valid category_id is required")

    if source_id is not None:
        try:
            source_id = int(source_id)
            if source_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("source_id must be a positive integer")

    if due_date < issue_date:
        raise ValueError("due_date cannot be earlier than issue_date")

    return {
        "check_number": check_number,
        "bank_name": bank_name,
        "amount": amount,
        "issue_date": issue_date,
        "due_date": due_date,
        "type": check_type,
        "source_id": source_id,
        "category_id": category_id,
        "description": description,
    }
