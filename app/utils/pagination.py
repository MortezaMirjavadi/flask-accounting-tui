"""Shared pagination utilities for API routes."""

import math
from flask import request, jsonify


def parse_pagination():
    """Extract page and per_page from request query params.

    Returns:
        (page, per_page) — both 1-indexed, clamped to sane defaults.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > 100:
        per_page = 100

    return page, per_page


def paginated_query(cursor, count_sql, data_sql, params, serialize_fn, page, per_page):
    """Run a count query + data query with LIMIT/OFFSET and return a jsonify response.

    Args:
        cursor: psycopg2 RealDictCursor
        count_sql: SQL for counting total rows (e.g. "SELECT COUNT(*) FROM ... WHERE ...")
        data_sql: SQL for fetching data (e.g. "SELECT * FROM ... WHERE ... ORDER BY ...")
        params: parameters for both queries (must be same length for count_sql)
        serialize_fn: callable that converts a row dict to a serializable dict
        page: 1-indexed page number
        per_page: items per page

    Returns:
        Flask jsonify response with shape:
        { "items": [...], "total": N, "page": P, "per_page": PP, "total_pages": TP }
    """
    # Count total rows
    cursor.execute(count_sql, params)
    total = cursor.fetchone()["total"]

    # Fetch page of data
    offset = (page - 1) * per_page
    cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
    rows = cursor.fetchall()

    total_pages = math.ceil(total / per_page) if per_page > 0 else 0

    return jsonify({
        "items": [serialize_fn(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })
