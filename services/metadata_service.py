"""Contact, Tag, and Label management services."""

import math
from database import get_connection, release_connection


# ── Contact Service ──────────────────────────────────────────────────

class ContactService:

    @staticmethod
    def create(user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Check for duplicate name
            cursor.execute(
                "SELECT id FROM contacts WHERE user_id = %s AND name = %s AND deleted_at IS NOT NULL",
                (user_id, data["name"]),
            )
            archived = cursor.fetchone()
            if archived:
                # Restore archived contact
                cursor.execute(
                    """
                    UPDATE contacts SET
                        phone = %s, email = %s, address = %s, notes = %s,
                        deleted_at = NULL
                    WHERE id = %s
                    RETURNING *
                    """,
                    (data.get("phone"), data.get("email"),
                     data.get("address"), data.get("notes"),
                     archived["id"]),
                )
                conn.commit()
                return dict(cursor.fetchone()), None

            cursor.execute(
                """
                INSERT INTO contacts (user_id, name, phone, email, address, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, data["name"], data.get("phone"),
                 data.get("email"), data.get("address"), data.get("notes")),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update(contact_id, user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM contacts WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (contact_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing:
                return None, "مخاطب یافت نشد"

            cursor.execute(
                """
                UPDATE contacts SET
                    name = %s, phone = %s, email = %s, address = %s, notes = %s
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING *
                """,
                (
                    data.get("name", existing["name"]),
                    data.get("phone", existing["phone"]),
                    data.get("email", existing["email"]),
                    data.get("address", existing["address"]),
                    data.get("notes", existing["notes"]),
                    contact_id, user_id,
                ),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def delete(contact_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE contacts SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (contact_id, user_id),
            )
            if not cursor.fetchone():
                return False, "Contact not found"
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def list_contacts(user_id, search=None, page=1, per_page=20):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            where_clause = " WHERE user_id = %s AND deleted_at IS NULL"
            params = [user_id]
            if search:
                where_clause += " AND name ILIKE %s"
                params.append(f"%{search}%")

            count_sql = "SELECT COUNT(*) as total FROM contacts" + where_clause
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            data_sql = "SELECT * FROM contacts" + where_clause + " ORDER BY name"
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
            rows = cursor.fetchall()

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_contact(contact_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM contacts WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (contact_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            release_connection(conn)


# ── Tag Service ─────────────────────────────────────────────────────

class TagService:

    @staticmethod
    def create(user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO tags (user_id, name, color)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (user_id, data["name"], data.get("color")),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            # Check for unique violation
            if "unique" in str(exc).lower():
                # Try restoring archived
                cursor2 = conn.cursor()
                try:
                    cursor2.execute(
                        "SELECT id FROM tags WHERE user_id = %s AND name = %s AND deleted_at IS NOT NULL",
                        (user_id, data["name"]),
                    )
                    archived = cursor2.fetchone()
                    if archived:
                        cursor2.execute(
                            "UPDATE tags SET color = %s, deleted_at = NULL WHERE id = %s RETURNING *",
                            (data.get("color"), archived["id"]),
                        )
                        conn.commit()
                        return dict(cursor2.fetchone()), None
                finally:
                    cursor2.close()
                return None, "برچسب قبلاً وجود دارد"
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update(tag_id, user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM tags WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (tag_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing:
                return None, "برچسب یافت نشد"

            cursor.execute(
                """
                UPDATE tags SET name = %s, color = %s
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING *
                """,
                (data.get("name", existing["name"]),
                 data.get("color", existing["color"]),
                 tag_id, user_id),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            if "unique" in str(exc).lower():
                return None, "نام برچسب قبلاً وجود دارد"
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def delete(tag_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE tags SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (tag_id, user_id),
            )
            if not cursor.fetchone():
                return False, "Tag not found"
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def list_tags(user_id, page=1, per_page=20):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            where_clause = " WHERE t.user_id = %s AND t.deleted_at IS NULL"
            params = [user_id]

            join_clause = (
                " FROM tags t"
                " LEFT JOIN ("
                "   SELECT tag_id, COUNT(*) AS tx_count FROM transaction_tags GROUP BY tag_id"
                " ) tc ON t.id = tc.tag_id"
            )

            count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            data_sql = (
                "SELECT t.*, COALESCE(tc.tx_count, 0)::int AS usage_count"
                + join_clause + where_clause + " ORDER BY t.name"
            )
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
            rows = cursor.fetchall()

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_tag(tag_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM tags WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (tag_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def set_transaction_tags(transaction_id, tag_ids):
        """Replace all tags on a transaction."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM transaction_tags WHERE transaction_id = %s",
                (transaction_id,),
            )
            for tag_id in tag_ids:
                cursor.execute(
                    "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (transaction_id, tag_id),
                )
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_transaction_tags(transaction_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT t.id, t.name, t.color
                FROM tags t
                JOIN transaction_tags tt ON t.id = tt.tag_id
                WHERE tt.transaction_id = %s AND t.deleted_at IS NULL
                ORDER BY t.name
                """,
                (transaction_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)


# ── Label Service ────────────────────────────────────────────────────

class LabelService:

    @staticmethod
    def create(user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO labels (user_id, name, color)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (user_id, data["name"], data.get("color")),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            if "unique" in str(exc).lower():
                cursor2 = conn.cursor()
                try:
                    cursor2.execute(
                        "SELECT id FROM labels WHERE user_id = %s AND name = %s AND deleted_at IS NOT NULL",
                        (user_id, data["name"]),
                    )
                    archived = cursor2.fetchone()
                    if archived:
                        cursor2.execute(
                            "UPDATE labels SET color = %s, deleted_at = NULL WHERE id = %s RETURNING *",
                            (data.get("color"), archived["id"]),
                        )
                        conn.commit()
                        return dict(cursor2.fetchone()), None
                finally:
                    cursor2.close()
                return None, "برچسب رنگی قبلاً وجود دارد"
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update(label_id, user_id, data):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM labels WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (label_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing:
                return None, "برچسب رنگی یافت نشد"

            cursor.execute(
                """
                UPDATE labels SET name = %s, color = %s
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING *
                """,
                (data.get("name", existing["name"]),
                 data.get("color", existing["color"]),
                 label_id, user_id),
            )
            conn.commit()
            return dict(cursor.fetchone()), None
        except Exception as exc:
            conn.rollback()
            if "unique" in str(exc).lower():
                return None, "نام برچسب رنگی قبلاً وجود دارد"
            return None, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def delete(label_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE labels SET deleted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (label_id, user_id),
            )
            if not cursor.fetchone():
                return False, "Label not found"
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def list_labels(user_id, page=1, per_page=20):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            where_clause = " WHERE l.user_id = %s AND l.deleted_at IS NULL"
            params = [user_id]

            join_clause = (
                " FROM labels l"
                " LEFT JOIN ("
                "   SELECT label_id, COUNT(*) AS tx_count FROM transaction_labels GROUP BY label_id"
                " ) tlc ON l.id = tlc.label_id"
                " LEFT JOIN ("
                "   SELECT label_id, COUNT(*) AS src_count FROM wallet_labels GROUP BY label_id"
                " ) slc ON l.id = slc.label_id"
            )

            count_sql = "SELECT COUNT(*) as total" + join_clause + where_clause
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            data_sql = (
                "SELECT l.*, COALESCE(tlc.tx_count, 0)::int AS transaction_count,"
                " COALESCE(slc.src_count, 0)::int AS wallet_count"
                + join_clause + where_clause + " ORDER BY l.name"
            )
            offset = (page - 1) * per_page
            cursor.execute(data_sql + " LIMIT %s OFFSET %s", params + [per_page, offset])
            rows = cursor.fetchall()

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_label(label_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM labels WHERE id = %s AND user_id = %s AND deleted_at IS NULL",
                (label_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def set_transaction_labels(transaction_id, label_ids):
        """Replace all labels on a transaction."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM transaction_labels WHERE transaction_id = %s",
                (transaction_id,),
            )
            for label_id in label_ids:
                cursor.execute(
                    "INSERT INTO transaction_labels (transaction_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (transaction_id, label_id),
                )
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def set_wallet_labels(wallet_id, label_ids):
        """Replace all labels on a wallet."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM wallet_labels WHERE wallet_id = %s",
                (wallet_id,),
            )
            for label_id in label_ids:
                cursor.execute(
                    "INSERT INTO wallet_labels (wallet_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (wallet_id, label_id),
                )
            conn.commit()
            return True, None
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_transaction_labels(transaction_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.id, l.name, l.color
                FROM labels l
                JOIN transaction_labels tl ON l.id = tl.label_id
                WHERE tl.transaction_id = %s AND l.deleted_at IS NULL
                ORDER BY l.name
                """,
                (transaction_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_wallet_labels(wallet_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.id, l.name, l.color
                FROM labels l
                JOIN wallet_labels sl ON l.id = sl.label_id
                WHERE sl.wallet_id = %s AND l.deleted_at IS NULL
                ORDER BY l.name
                """,
                (wallet_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)
