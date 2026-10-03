"""Contact, Tag, and Label management services."""

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
                return None, "Contact not found"

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
    def list_contacts(user_id, search=None):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM contacts WHERE user_id = %s AND deleted_at IS NULL"
            params = [user_id]
            if search:
                query += " AND name ILIKE %s"
                params.append(f"%{search}%")
            query += " ORDER BY name"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
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
                return None, "Tag already exists"
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
                return None, "Tag not found"

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
                return None, "Tag name already exists"
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
    def list_tags(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT t.*,
                       COALESCE(tc.tx_count, 0)::int AS usage_count
                FROM tags t
                LEFT JOIN (
                    SELECT tag_id, COUNT(*) AS tx_count
                    FROM transaction_tags
                    GROUP BY tag_id
                ) tc ON t.id = tc.tag_id
                WHERE t.user_id = %s AND t.deleted_at IS NULL
                ORDER BY t.name
                """,
                (user_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
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
                return None, "Label already exists"
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
                return None, "Label not found"

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
                return None, "Label name already exists"
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
    def list_labels(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.*,
                       COALESCE(tlc.tx_count, 0)::int AS transaction_count,
                       COALESCE(slc.src_count, 0)::int AS source_count
                FROM labels l
                LEFT JOIN (
                    SELECT label_id, COUNT(*) AS tx_count
                    FROM transaction_labels GROUP BY label_id
                ) tlc ON l.id = tlc.label_id
                LEFT JOIN (
                    SELECT label_id, COUNT(*) AS src_count
                    FROM source_labels GROUP BY label_id
                ) slc ON l.id = slc.label_id
                WHERE l.user_id = %s AND l.deleted_at IS NULL
                ORDER BY l.name
                """,
                (user_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
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
    def set_source_labels(source_id, label_ids):
        """Replace all labels on a source."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM source_labels WHERE source_id = %s",
                (source_id,),
            )
            for label_id in label_ids:
                cursor.execute(
                    "INSERT INTO source_labels (source_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (source_id, label_id),
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
    def get_source_labels(source_id):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.id, l.name, l.color
                FROM labels l
                JOIN source_labels sl ON l.id = sl.label_id
                WHERE sl.source_id = %s AND l.deleted_at IS NULL
                ORDER BY l.name
                """,
                (source_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            cursor.close()
            release_connection(conn)
