#!/usr/bin/env python3
"""Seed the database with sample Persian data for demo/testing."""

import load_env  # noqa: F401
import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from database import get_connection, release_connection, init_db
import jdatetime


def seed():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # ── Users ──────────────────────────────────────────────────────────────
    print("Creating users...")
    pw = generate_password_hash("123")
    users = [
        ("morteza", pw, "مرتضی", True, True, True),
        ("admin", pw, "مدیر سیستم", True, True, True),
        ("demo", pw, "کاربر نمونه", False, True, True),
    ]
    for u in users:
        cur.execute(
            """INSERT INTO users (username, password_hash, display_name, is_admin, is_approved, is_active)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (username) DO UPDATE SET password_hash=EXCLUDED.password_hash""",
            u,
        )
    conn.commit()

    # Get morteza's user_id
    cur.execute("SELECT id FROM users WHERE username = 'morteza'")
    uid = cur.fetchone()["id"]

    # ── Categories (tree structure) ─────────────────────────────────────
    print("Creating categories...")
    # Root categories with their children
    category_tree = [
        ("حقوق", "income", []),
        ("درآمد", "income", ["درآمد پروژه", "فروش کالا"]),
        ("هدیه", "income", []),
        ("سود بانکی", "income", []),
        ("خوراک", "cost", ["رستوران", "سوپرمارکت", "نانوایی"]),
        ("حمل و نقل", "cost", ["تاکسی", "بنزین", "مترو"]),
        ("پوشاک", "cost", ["لباس", "کفش"]),
        ("بهداشت و درمان", "cost", ["داروخانه", "ویزیت دکتر"]),
        ("سرگرمی", "cost", ["سینما", "کتاب"]),
        ("قبوض", "cost", ["برق", "گاز", "آب", "تلفن"]),
        ("آموزش", "cost", ["کلاس زبان", "دوره آنلاین"]),
        ("مسکن", "cost", ["اجاره", "شارژ"]),
        ("لوازم خانه", "cost", []),
        ("موبایل و اینترنت", "cost", []),
    ]
    cat_ids = {}
    for root_name, root_type, children in category_tree:
        cur.execute(
            """INSERT INTO categories (name, type, user_id) VALUES (%s, %s, %s)
               ON CONFLICT DO NOTHING RETURNING id""",
            (root_name, root_type, uid),
        )
        row = cur.fetchone()
        if row:
            cat_ids[root_name] = row["id"]
        conn.commit()

        # Fetch root ID if it already existed
        if root_name not in cat_ids:
            cur.execute("SELECT id FROM categories WHERE user_id = %s AND name = %s AND deleted_at IS NULL", (uid, root_name))
            row = cur.fetchone()
            if row:
                cat_ids[root_name] = row["id"]

        root_id = cat_ids.get(root_name)
        if root_id and children:
            for child_name in children:
                cur.execute(
                    """INSERT INTO categories (name, type, user_id, parent_id) VALUES (%s, %s, %s, %s)
                       ON CONFLICT DO NOTHING RETURNING id""",
                    (child_name, root_type, uid, root_id),
                )
                row = cur.fetchone()
                if row:
                    cat_ids[child_name] = row["id"]
            conn.commit()

    # Fetch any remaining category IDs
    cur.execute("SELECT id, name FROM categories WHERE user_id = %s AND deleted_at IS NULL", (uid,))
    for row in cur.fetchall():
        cat_ids[row["name"]] = row["id"]

    # ── Wallets + Accounts ────────────────────────────────────────────────────
    print("Creating wallets...")
    wallets = [
        ("کیف پول نقدی", "IRR", "personal", [("نقد", "cash", 50000000)]),
        ("بانک ملت", "IRR", "bank", [("حساب جاری ملت", "bank", 250000000), ("کارت ملت", "card", 15000000)]),
        ("بانک سامان", "IRR", "bank", [("حساب سامان", "bank", 120000000)]),
        ("کیف پول دلاری", "USD", "personal", [("دلار نقدی", "cash", 500)]),
    ]
    wallet_ids = {}
    for name, cur_code, wtype, accounts in wallets:
        cur.execute(
            """INSERT INTO wallets (name, currency, wallet_type, user_id)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT DO NOTHING RETURNING id""",
            (name, cur_code, wtype, uid),
        )
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT id FROM wallets WHERE user_id = %s AND name = %s", (uid, name))
            row = cur.fetchone()
        if row:
            wid = row["id"]
            wallet_ids[name] = wid
            for i, (acc_name, acc_type, acc_amount) in enumerate(accounts):
                cur.execute(
                    """INSERT INTO accounts (wallet_id, name, account_type, amount, is_default, sort_order)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (wid, acc_name, acc_type, acc_amount, i == 0, i),
                )
    conn.commit()

    cur.execute("SELECT id, name FROM wallets WHERE user_id = %s", (uid,))
    for row in cur.fetchall():
        wallet_ids[row["name"]] = row["id"]

    # ── Tags ───────────────────────────────────────────────────────────────
    print("Creating tags...")
    tags = ["ضروری", "ماهانه", "آنلاین", "حضوری", "تخفیف", "گران", "ارزان"]
    tag_ids = {}
    for t in tags:
        cur.execute(
            """INSERT INTO tags (name, user_id) VALUES (%s, %s)
               ON CONFLICT DO NOTHING RETURNING id""",
            (t, uid),
        )
        row = cur.fetchone()
        if row:
            tag_ids[t] = row["id"]
    conn.commit()
    cur.execute("SELECT id, name FROM tags WHERE user_id = %s", (uid,))
    for row in cur.fetchall():
        tag_ids[row["name"]] = row["id"]

    # ── Labels ─────────────────────────────────────────────────────────────
    print("Creating labels...")
    labels = ["شخصی", "کاری", "خانوادگی", "اضطراری"]
    label_ids = {}
    for l in labels:
        cur.execute(
            """INSERT INTO labels (name, user_id) VALUES (%s, %s)
               ON CONFLICT DO NOTHING RETURNING id""",
            (l, uid),
        )
        row = cur.fetchone()
        if row:
            label_ids[l] = row["id"]
    conn.commit()
    cur.execute("SELECT id, name FROM labels WHERE user_id = %s", (uid,))
    for row in cur.fetchall():
        label_ids[row["name"]] = row["id"]

    # ── Contacts ───────────────────────────────────────────────────────────
    print("Creating contacts...")
    contacts = [
        ("علی رضایی", "09121234567", "ali@example.com"),
        ("زهرا محمدی", "09351234567", "zahra@example.com"),
        ("شرکت خدماتی پارس", "02188776655", "info@parsco.ir"),
    ]
    for cn, phone, email in contacts:
        cur.execute(
            """INSERT INTO contacts (name, phone, email, user_id)
               VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (cn, phone, email, uid),
        )
    conn.commit()

    # ── Transactions (past 6 months) ──────────────────────────────────────
    print("Creating transactions...")
    today_j = jdatetime.date.today()
    descriptions = {
        "خوراک": ["خرید از سوپرمارکت", "میوه و سبزیجات", "لبنیات", "نان"],
        "حمل و نقل": ["تاکسی", "بنزین", "بلیط اتوبوس", "پارکینگ"],
        "پوشاک": ["خرید لباس", "کفش", "کیف"],
        "بهداشت و درمان": ["داروخانه", "ویزیت دکتر", "آزمایشگاه"],
        "سرگرمی": ["سینما", "کتاب", "بازی"],
        "قبوض": ["برق", "گاز", "آب", "تلفن"],
        "آموزش": ["کلاس زبان", "دوره آنلاین", "کتاب آموزشی"],
        "مسکن": ["اجاره ماهانه", "شارژ ساختمان"],
        "رستوران": ["رستوران", "کافه", "فست‌فود"],
        "هدیه و کمک": ["هدیه تولد", "کمک خیریه"],
        "تعمیرات": ["تعمیر خودرو", "تعمیر لوازم خانه"],
        "بیمه": ["بیمه خودرو", "بیمه عمر"],
        "سفر": ["بلیط هواپیما", "هتل", "سوغاتی"],
        "لوازم خانه": ["لوازم آشپزخانه", "مبلمان"],
        "موبایل و اینترنت": ["شارژ موبایل", "قبض اینترنت"],
        "حقوق": ["حقوق ماهانه"],
        "درآمد": ["درآمد پروژه", "فروش کالا"],
        "هدیه": ["هدیه نقدی"],
        "سود بانکی": ["سود سپرده"],
        "فروش": ["فروش آنلاین"],
    }
    w_ids = list(wallet_ids.values())
    tx_count = 0

    for month_offset in range(6):
        m = today_j.month - month_offset
        y = today_j.year
        while m <= 0:
            m += 12
            y -= 1
        # Income transactions
        income_cat_names = [name for name, ctype, _ in category_tree if ctype == "income"]
        for _ in range(random.randint(2, 4)):
            cat_name = random.choice(income_cat_names)
            cat_id = cat_ids.get(cat_name)
            if not cat_id:
                continue
            day = random.randint(1, 28)
            try:
                j_date = jdatetime.date(y, m, day)
                g_date = j_date.togregorian().strftime("%Y-%m-%d")
            except ValueError:
                continue
            amount = random.choice([5000000, 15000000, 25000000, 8000000, 35000000])
            desc = random.choice(descriptions.get(cat_name, ["درآمد"]))
            w_id = random.choice(w_ids)
            cur.execute(
                """INSERT INTO transactions (date, amount, category_id, wallet_id, description, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (g_date, amount, cat_id, w_id, desc, uid),
            )
            tx_count += 1

        # Cost transactions
        cost_cat_names = [name for name, ctype, _ in category_tree if ctype == "cost"]
        for _ in range(random.randint(8, 15)):
            cat_name = random.choice(cost_cat_names)
            cat_id = cat_ids.get(cat_name)
            if not cat_id:
                continue
            day = random.randint(1, 28)
            try:
                j_date = jdatetime.date(y, m, day)
                g_date = j_date.togregorian().strftime("%Y-%m-%d")
            except ValueError:
                continue
            amount = random.choice([50000, 120000, 250000, 500000, 800000, 1500000, 3000000])
            desc = random.choice(descriptions.get(cat_name, ["خرید"]))
            w_id = random.choice(w_ids)
            cur.execute(
                """INSERT INTO transactions (date, amount, category_id, wallet_id, description, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (g_date, amount, cat_id, w_id, desc, uid),
            )
            tx_count += 1

    conn.commit()
    print(f"  Created {tx_count} transactions")

    # ── Budget periods ─────────────────────────────────────────────────────
    print("Creating budget periods...")
    for i in range(3):
        m = today_j.month - i
        y = today_j.year
        while m <= 0:
            m += 12
            y -= 1
        cur.execute(
            """INSERT INTO budget_periods (year, month, user_id)
               VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
            (y, m, uid),
        )
    conn.commit()

    print("Seed completed successfully!")
    print(f"  Users: {len(users)}")
    print(f"  Categories: {len(cat_ids)}")
    print(f"  Wallets: {len(wallets)}")
    print(f"  Tags: {len(tags)}")
    print(f"  Labels: {len(labels)}")
    print(f"  Contacts: {len(contacts)}")
    print(f"  Transactions: {tx_count}")
    print(f"  Budget periods: 3")
    release_connection(conn)


if __name__ == "__main__":
    seed()
