from app.utils.helpers import jalali_to_gregorian

def validate_user_payload(data):
    """Validate user registration/login payload."""
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or len(username) < 3:
        raise ValueError("نام کاربری باید حداقل ۳ کاراکتر باشد")
    if not password or len(password) < 6:
        raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد")

    display_name = data.get("display_name", "").strip() or None
    email = data.get("email", "").strip() or None

    if email and "@" not in email:
        raise ValueError("آدرس ایمیل نامعتبر است")

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
        raise ValueError("نام دسته‌بندی الزامی است")
    if cat_type not in ("income", "cost"):
        raise ValueError("نوع دسته‌بندی باید 'income' یا 'cost' باشد")

    return {"name": name, "type": cat_type}


def validate_source_payload(data):
    """Validate source payload (backward compat alias for wallet)."""
    return validate_wallet_payload(data)


def validate_wallet_payload(data):
    """Validate wallet payload."""
    name = (data.get("name") or "").strip()
    currency = (data.get("currency") or "IRR").strip().upper()
    wallet_type = (data.get("wallet_type") or "personal").strip().lower()
    variant = data.get("variant")

    if not name:
        raise ValueError("نام کیف پول الزامی است")

    supported_currencies = ("IRR", "USD", "EUR", "GBP", "AED")
    if currency not in supported_currencies:
        raise ValueError(f"ارز '{currency}' پشتیبانی نمی‌شود")

    if wallet_type not in ("personal", "shared"):
        raise ValueError("نوع کیف پول باید personal یا shared باشد")

    valid_variants = ("family", "team", "travel", "business", "savings")
    if variant is not None and variant not in valid_variants:
        raise ValueError(f"نوع کیف پول باید یکی از {', '.join(valid_variants)} باشد")

    return {"name": name, "currency": currency, "wallet_type": wallet_type, "variant": variant}


def validate_transaction_payload(data):
    """Validate transaction payload."""
    date = data.get("date", "").strip()
    amount = data.get("amount")
    category_id = data.get("category_id")
    # Accept both source_id (legacy) and wallet_id
    wallet_id = data.get("wallet_id") or data.get("source_id")
    description = data.get("description", "").strip()

    if not date:
        raise ValueError("تاریخ الزامی است")

    gregorian_date = jalali_to_gregorian(date)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ معتبر و مثبت الزامی است")
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("شناسه دسته‌بندی معتبر الزامی است")

    if wallet_id is not None:
        try:
            wallet_id = int(wallet_id)
        except (TypeError, ValueError):
            raise ValueError("شناسه کیف پول باید عدد صحیح باشد")

    return {
        "date": gregorian_date,
        "amount": amount,
        "category_id": category_id,
        "wallet_id": wallet_id,
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
        raise ValueError("سال معتبر (۱۳۰۰-۱۵۰۰) الزامی است")

    try:
        month = int(month)
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("ماه معتبر (۱-۱۲) الزامی است")

    return {"year": year, "month": month}


def validate_budget_item_payload(data):
    """Validate budget item payload."""
    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError("داده نامعتبر است")

    category_id = data.get("category_id")
    planned_amount = data.get("planned_amount")
    notes = (data.get("notes", "") or "").strip() or None

    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("شناسه دسته‌بندی معتبر الزامی است")

    try:
        planned_amount = float(planned_amount)
        if planned_amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ برنامه‌ریزی شده معتبر و غیرمنفی الزامی است")

    return {
        "category_id": category_id,
        "planned_amount": planned_amount,
        "notes": notes
    }


def validate_installment_plan_payload(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("داده نامعتبر است")

    title = (data.get("title") or "").strip()
    total_amount = data.get("total_amount")
    installment_count = data.get("installment_count")
    installment_amount = data.get("installment_amount")
    start_date = (data.get("start_date") or "").strip()
    due_day_of_month = data.get("due_day_of_month")
    category_id = data.get("category_id")
    wallet_id = data.get("wallet_id") or data.get("source_id")
    status = (data.get("status") or "active").strip().lower()

    if not title:
        raise ValueError("عنوان الزامی است")

    try:
        total_amount = float(total_amount)
        if total_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ کل معتبر و مثبت الزامی است")

    try:
        installment_count = int(installment_count)
        if installment_count <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("تعداد اقساط باید بزرگتر از صفر باشد")

    if not start_date:
        raise ValueError("تاریخ شروع الزامی است")

    if due_day_of_month is None or due_day_of_month == "":
        due_day_of_month = int(start_date.split("-")[2]) if isinstance(start_date, str) else None
    else:
        try:
            due_day_of_month = int(due_day_of_month)
            if not 1 <= due_day_of_month <= 31:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("روز سررسید باید عدد صحیح بین ۱ تا ۳۱ باشد")

    try:
        category_id = int(category_id)
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("شناسه دسته‌بندی معتبر الزامی است")

    if wallet_id is not None:
        try:
            wallet_id = int(wallet_id)
            if wallet_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("شناسه کیف پول باید عدد صحیح مثبت باشد")

    if installment_amount is not None:
        try:
            installment_amount = float(installment_amount)
            if installment_amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("مبلغ قسط باید بزرگتر از صفر باشد")

    if status not in ("active", "completed", "canceled"):
        raise ValueError("وضعیت باید فعال، تکمیل شده یا لغو شده باشد")

    return {
        "title": title,
        "total_amount": total_amount,
        "installment_count": installment_count,
        "installment_amount": installment_amount,
        "start_date": start_date,
        "due_day_of_month": due_day_of_month,
        "category_id": category_id,
        "wallet_id": wallet_id,
        "status": status,
    }


def validate_installment_payment_payload(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("داده نامعتبر است")

    installment_ids = data.get("installment_ids")
    paid_date = (data.get("paid_date") or "").strip()

    if installment_ids is None:
        raise ValueError("شناسه اقساط الزامی است")
    if isinstance(installment_ids, int):
        installment_ids = [installment_ids]
    if not isinstance(installment_ids, list) or len(installment_ids) == 0:
        raise ValueError("شناسه اقساط باید لیست غیرخالی از اعداد صحیح باشد")
    cleaned_ids = []
    for item in installment_ids:
        if item is None:
            raise ValueError("شناسه اقساط باید شامل اعداد صحیح باشد")
        try:
            item_id = int(item)
        except (TypeError, ValueError):
            raise ValueError("شناسه اقساط باید شامل اعداد صحیح باشد")
        if item_id <= 0:
            raise ValueError("شناسه اقساط باید شامل اعداد صحیح مثبت باشد")
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
        raise ValueError("داده نامعتبر است")

    check_type = (data.get("type") or "").strip().lower()
    if check_type not in ("issued", "received"):
        raise ValueError("نوع باید 'issued' یا 'received' باشد")

    check_number = (data.get("check_number") or "").strip() or None
    bank_name = (data.get("bank_name") or "").strip() or None
    amount = data.get("amount")
    issue_date = (data.get("issue_date") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    category_id = data.get("category_id")
    wallet_id = data.get("wallet_id") or data.get("source_id")
    description = (data.get("description") or "").strip() or None

    if not issue_date:
        raise ValueError("تاریخ صدور الزامی است")
    if not due_date:
        raise ValueError("تاریخ سررسید الزامی است")

    issue_date = jalali_to_gregorian(issue_date)
    due_date = jalali_to_gregorian(due_date)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ معتبر و مثبت الزامی است")

    try:
        category_id = int(category_id)
        if category_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("شناسه دسته‌بندی معتبر الزامی است")

    if wallet_id is not None:
        try:
            wallet_id = int(wallet_id)
            if wallet_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("شناسه کیف پول باید عدد صحیح مثبت باشد")

    if due_date < issue_date:
        raise ValueError("تاریخ سررسید نمی‌تواند قبل از تاریخ صدور باشد")

    return {
        "check_number": check_number,
        "bank_name": bank_name,
        "amount": amount,
        "issue_date": issue_date,
        "due_date": due_date,
        "type": check_type,
        "wallet_id": wallet_id,
        "category_id": category_id,
        "description": description,
    }


def validate_transaction_item_payload(data):
    """Validate a single transaction item payload."""
    if data is None or not isinstance(data, dict):
        raise ValueError("داده قلم نامعتبر است")

    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("نام قلم الزامی است")

    quantity = data.get("quantity")
    if quantity is None:
        quantity = 1
    try:
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("تعداد باید عدد مثبت باشد")

    unit = (data.get("unit") or "").strip() or None

    total_price = data.get("total_price")
    try:
        total_price = float(total_price)
        if total_price < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("قیمت کل معتبر و غیرمنفی الزامی است")

    unit_price = data.get("unit_price")
    if unit_price is not None:
        try:
            unit_price = float(unit_price)
            if unit_price < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("قیمت واحد باید عدد غیرمنفی باشد")
    else:
        unit_price = round(total_price / quantity, 2) if quantity > 0 else total_price

    notes = (data.get("notes") or "").strip() or None

    return {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "total_price": total_price,
        "notes": notes,
    }


def validate_transaction_items_payload(items_data):
    """Validate a list of transaction items."""
    if items_data is None:
        return []
    if not isinstance(items_data, list):
        raise ValueError("اقلام باید لیست باشد")

    validated = []
    for i, item in enumerate(items_data):
        try:
            validated.append(validate_transaction_item_payload(item))
        except ValueError as exc:
            raise ValueError(f"قلم {i + 1}: {exc}")
    return validated


def validate_debt_payload(data):
    """Validate a debt/receivable creation payload."""
    if data is None or not isinstance(data, dict):
        raise ValueError("داده نامعتبر است")

    debt_type = (data.get("type") or "").strip().lower()
    if debt_type not in ("receivable", "payable"):
        raise ValueError("نوع باید 'receivable' یا 'payable' باشد")

    counterparty_name = (data.get("counterparty_name") or "").strip()
    if not counterparty_name:
        raise ValueError("نام طرف حساب الزامی است")

    counterparty_type = (data.get("counterparty_type") or "person").strip().lower()
    valid_types = ("person", "company", "bank", "merchant", "family", "friend", "other")
    if counterparty_type not in valid_types:
        raise ValueError(f"نوع طرف حساب باید یکی از موارد زیر باشد: {', '.join(valid_types)}")

    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("عنوان الزامی است")

    description = (data.get("description") or "").strip() or None

    try:
        original_amount = float(data.get("original_amount"))
        if original_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ اولیه باید عدد مثبت باشد")

    issue_date = (data.get("issue_date") or "").strip()
    if not issue_date:
        raise ValueError("تاریخ صدور الزامی است")
    issue_date = jalali_to_gregorian(issue_date)

    due_date = (data.get("due_date") or "").strip() or None
    if due_date:
        due_date = jalali_to_gregorian(due_date)
        if due_date < issue_date:
            raise ValueError("تاریخ سررسید نمی‌تواند قبل از تاریخ صدور باشد")

    priority = (data.get("priority") or "normal").strip().lower()
    if priority not in ("low", "normal", "high", "urgent"):
        raise ValueError("اولویت باید کم، عادی، زیاد یا فوری باشد")

    wallet_id = data.get("wallet_id") or data.get("source_id")
    if wallet_id is not None:
        try:
            wallet_id = int(wallet_id)
            if wallet_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("شناسه کیف پول باید عدد صحیح مثبت باشد")

    reference_type = (data.get("reference_type") or "").strip() or None
    reference_id = data.get("reference_id")
    if reference_id is not None:
        try:
            reference_id = int(reference_id)
        except (TypeError, ValueError):
            raise ValueError("شناسه مرجع باید عدد صحیح باشد")

    has_interest = bool(data.get("has_interest", False))
    interest_type = (data.get("interest_type") or "").strip() or None
    interest_rate = data.get("interest_rate")

    if has_interest:
        if interest_type not in ("simple", "compound", "fixed"):
            raise ValueError("نوع سود باید ساده، مرکب یا ثابت باشد")
        try:
            interest_rate = float(interest_rate)
            if interest_rate < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("نرخ سود باید عدد غیرمنفی باشد")
    else:
        interest_type = None
        interest_rate = None

    return {
        "type": debt_type,
        "counterparty_name": counterparty_name,
        "counterparty_type": counterparty_type,
        "title": title,
        "description": description,
        "original_amount": original_amount,
        "issue_date": issue_date,
        "due_date": due_date,
        "priority": priority,
        "wallet_id": wallet_id,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "has_interest": has_interest,
        "interest_type": interest_type,
        "interest_rate": interest_rate,
    }


def validate_debt_payment_payload(data):
    """Validate a debt payment payload."""
    if data is None or not isinstance(data, dict):
        raise ValueError("داده نامعتبر است")

    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("مبلغ باید عدد مثبت باشد")

    payment_date = (data.get("payment_date") or "").strip()
    if not payment_date:
        raise ValueError("تاریخ پرداخت الزامی است")
    payment_date = jalali_to_gregorian(payment_date)

    payment_method = (data.get("payment_method") or "cash").strip().lower()

    wallet_id = data.get("wallet_id") or data.get("source_id")
    if wallet_id is not None:
        try:
            wallet_id = int(wallet_id)
            if wallet_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("شناسه کیف پول باید عدد صحیح مثبت باشد")

    note = (data.get("note") or "").strip() or None

    return {
        "amount": amount,
        "payment_date": payment_date,
        "payment_method": payment_method,
        "wallet_id": wallet_id,
        "note": note,
    }
