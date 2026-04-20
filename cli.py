import argparse
import json
import sys

import requests

BASE_URL = "http://127.0.0.1:5000"


def pretty_print(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def handle_response(resp):
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    if not resp.ok:
        pretty_print({"error": data, "status_code": resp.status_code})
        sys.exit(1)
    pretty_print(data)


# ---------------------------------------------------------------------------
# Category commands
# ---------------------------------------------------------------------------

def category_list(args):
    resp = requests.get(f"{BASE_URL}/categories")
    handle_response(resp)


def category_add(args):
    payload = {"name": args.name, "type": args.type}
    resp = requests.post(f"{BASE_URL}/categories", json=payload)
    handle_response(resp)


def category_delete(args):
    resp = requests.delete(f"{BASE_URL}/categories/{args.id}")
    handle_response(resp)


# ---------------------------------------------------------------------------
# Transaction commands
# ---------------------------------------------------------------------------

def transaction_list(args):
    params = {}
    if getattr(args, "category_id", None) is not None:
        params["category_id"] = args.category_id
    resp = requests.get(f"{BASE_URL}/transactions", params=params)
    handle_response(resp)


def transaction_add(args):
    payload = {
        "date": args.date,
        "amount": args.amount,
        "category_id": args.category_id,
        "description": args.description or "",
    }
    resp = requests.post(f"{BASE_URL}/transactions", json=payload)
    handle_response(resp)


def transaction_summary(args):
    resp = requests.get(f"{BASE_URL}/transactions/summary")
    handle_response(resp)


def transaction_report(args):
    if args.type == "category":
        resp = requests.get(f"{BASE_URL}/transactions/report/category")
    elif args.type == "monthly":
        resp = requests.get(f"{BASE_URL}/transactions/report/monthly")
    else:
        print("Invalid report type. Use 'category' or 'monthly'.")
        sys.exit(1)
    handle_response(resp)


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Terminal Accounting CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # category
    cat_parser = subparsers.add_parser("category", help="Manage categories")
    cat_subparsers = cat_parser.add_subparsers(dest="cat_action", required=True)

    cat_list = cat_subparsers.add_parser("list", help="List categories")
    cat_list.set_defaults(func=category_list)

    cat_add = cat_subparsers.add_parser("add", help="Add a category")
    cat_add.add_argument("--name", required=True, help="Category name")
    cat_add.add_argument("--type", required=True, choices=["income", "cost"], help="Category type")
    cat_add.set_defaults(func=category_add)

    cat_del = cat_subparsers.add_parser("delete", help="Delete a category")
    cat_del.add_argument("--id", type=int, required=True, help="Category ID")
    cat_del.set_defaults(func=category_delete)

    # transaction
    tx_parser = subparsers.add_parser("transaction", help="Manage transactions")
    tx_subparsers = tx_parser.add_subparsers(dest="tx_action", required=True)

    tx_list = tx_subparsers.add_parser("list", help="List transactions")
    tx_list.add_argument("--category_id", type=int, default=None, help="Filter by category ID")
    tx_list.set_defaults(func=transaction_list)

    tx_add = tx_subparsers.add_parser("add", help="Add a transaction")
    tx_add.add_argument("--date", required=True, help="Jalali date (YYYY-MM-DD)")
    tx_add.add_argument("--amount", type=float, required=True, help="Amount")
    tx_add.add_argument("--category_id", type=int, required=True, help="Category ID")
    tx_add.add_argument("--description", default="", help="Description")
    tx_add.set_defaults(func=transaction_add)

    tx_summary = tx_subparsers.add_parser("summary", help="Show summary")
    tx_summary.set_defaults(func=transaction_summary)

    tx_report = tx_subparsers.add_parser("report", help="Show reports")
    tx_report.add_argument("--type", required=True, choices=["category", "monthly"], help="Report type")
    tx_report.set_defaults(func=transaction_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
