import math
import pyotp
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, release_connection


class AuthService:
    @staticmethod
    def register_user(username, password, display_name=None, email=None):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return None, "نام کاربری قبلاً ثبت شده است"

            # First user in the system is auto-approved and auto-promoted to admin
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            is_first_user = cursor.fetchone()["cnt"] == 0
            is_approved = True if is_first_user else False
            is_admin = True if is_first_user else False

            password_hash = generate_password_hash(password)
            cursor.execute(
                """INSERT INTO users (username, password_hash, display_name, email, is_approved, is_admin)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (username, password_hash, display_name, email, is_approved, is_admin),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()

            return {
                "id": new_id,
                "username": username,
                "is_approved": is_approved,
                "is_admin": is_admin,
            }, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def authenticate_user(username, password):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id, username, password_hash, totp_enabled, is_approved, is_admin, is_active FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()

            if row is None or not check_password_hash(row["password_hash"], password):
                return None, "نام کاربری یا رمز عبور اشتباه است"

            if not row["is_approved"]:
                return None, "حساب شما در انتظار تایید مدیر است"

            if not row.get("is_active", True):
                return None, "حساب شما غیرفعال شده است"

            return {
                "id": row["id"],
                "username": row["username"],
                "totp_enabled": row.get("totp_enabled", False),
                "is_admin": row.get("is_admin", False),
            }, None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_user_by_username(username):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id, username, created_at, totp_enabled, is_admin, is_approved, display_name, email FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()

            if row is None:
                return None, "کاربر یافت نشد"

            return dict(row), None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_pending_users(page=1, per_page=20):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            count_sql = "SELECT COUNT(*) as total FROM users WHERE is_approved = FALSE"
            cursor.execute(count_sql)
            total = cursor.fetchone()["total"]

            offset = (page - 1) * per_page
            cursor.execute(
                "SELECT id, username, display_name, email, created_at FROM users WHERE is_approved = FALSE ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )
            rows = [dict(row) for row in cursor.fetchall()]

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }, None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def approve_user(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET is_approved = TRUE WHERE id = %s AND is_approved = FALSE RETURNING id, username",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد یا قبلاً تایید شده است"
            conn.commit()
            return {"id": row["id"], "username": row["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def reject_user(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM users WHERE id = %s AND is_approved = FALSE AND is_admin = FALSE RETURNING id, username",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد، قبلاً تایید شده، یا مدیر است"
            conn.commit()
            return {"id": row["id"], "username": row["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def is_user_admin(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return False
            return row["is_admin"]
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_all_users(page=1, per_page=20):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            count_sql = "SELECT COUNT(*) as total FROM users"
            cursor.execute(count_sql)
            total = cursor.fetchone()["total"]

            offset = (page - 1) * per_page
            cursor.execute(
                """SELECT id, username, display_name, email, is_admin, is_approved, is_active, created_at
                   FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (per_page, offset)
            )
            rows = [dict(row) for row in cursor.fetchall()]

            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            return {
                "items": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }, None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def activate_user(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET is_active = TRUE WHERE id = %s AND is_active = FALSE RETURNING id, username",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد یا قبلاً فعال است"
            conn.commit()
            return {"id": row["id"], "username": row["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def deactivate_user(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET is_active = FALSE WHERE id = %s AND is_active = TRUE AND is_admin = FALSE RETURNING id, username",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد، قبلاً غیرفعال است، یا مدیر است"
            conn.commit()
            return {"id": row["id"], "username": row["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def create_user_by_admin(username, password, display_name=None, email=None,
                             is_admin=False, is_active=True):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return None, "نام کاربری قبلاً ثبت شده است"

            password_hash = generate_password_hash(password)
            cursor.execute(
                """INSERT INTO users (username, password_hash, display_name, email,
                                      is_approved, is_admin, is_active)
                   VALUES (%s, %s, %s, %s, TRUE, %s, %s) RETURNING id""",
                (username, password_hash, display_name, email, is_admin, is_active),
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()

            return {
                "id": new_id,
                "username": username,
                "is_approved": True,
                "is_admin": is_admin,
                "is_active": is_active,
            }, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def get_user_by_id(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """SELECT id, username, display_name, email, is_admin, is_approved, is_active, created_at
                   FROM users WHERE id = %s""",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد"
            return dict(row), None
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def update_user(user_id, display_name=None, email=None, is_admin=None,
                    is_approved=None, is_active=None, password=None):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id, is_admin FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد"

            updates = []
            params = []

            if display_name is not None:
                updates.append("display_name = %s")
                params.append(display_name)
            if email is not None:
                updates.append("email = %s")
                params.append(email)
            if is_admin is not None:
                updates.append("is_admin = %s")
                params.append(is_admin)
            if is_approved is not None:
                updates.append("is_approved = %s")
                params.append(is_approved)
            if is_active is not None:
                updates.append("is_active = %s")
                params.append(is_active)
            if password:
                updates.append("password_hash = %s")
                params.append(generate_password_hash(password))

            if not updates:
                return {"id": user_id, "message": "No changes"}, None

            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id, username"
            cursor.execute(sql, params)
            result = cursor.fetchone()
            conn.commit()

            return {"id": result["id"], "username": result["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def delete_user(user_id):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id, username, is_admin FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None, "کاربر یافت نشد"
            if row["is_admin"]:
                return None, "امکان حذف کاربر مدیر وجود ندارد"

            cursor.execute("DELETE FROM users WHERE id = %s AND is_admin = FALSE RETURNING id, username", (user_id,))
            deleted = cursor.fetchone()
            if deleted is None:
                return None, "امکان حذف کاربر مدیر وجود ندارد"
            conn.commit()
            return {"id": deleted["id"], "username": deleted["username"]}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def setup_totp(username):
        """Generate a TOTP secret and provisioning URI (does not save yet)."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name="Terminal Accounting")
        return {"secret": secret, "uri": uri}, None

    @staticmethod
    def enable_totp(username, secret, code):
        """Verify the OTP code, then save the secret and enable 2FA."""
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            return None, "کد تأیید نامعتبر است"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET totp_secret = %s, totp_enabled = TRUE WHERE username = %s",
                (secret, username),
            )
            conn.commit()
            return {"message": "2FA enabled successfully"}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def disable_totp(username):
        """Clear the TOTP secret and disable 2FA."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET totp_secret = NULL, totp_enabled = FALSE WHERE username = %s",
                (username,),
            )
            conn.commit()
            return {"message": "2FA disabled"}, None
        except Exception as e:
            conn.rollback()
            return None, str(e)
        finally:
            cursor.close()
            release_connection(conn)

    @staticmethod
    def verify_totp(username, code):
        """Verify a TOTP code against the user's stored secret."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT totp_secret, totp_enabled FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            if not row or not row.get("totp_enabled") or not row.get("totp_secret"):
                return None, "احراز هویت دو مرحله‌ای برای این کاربر فعال نیست"
            totp = pyotp.TOTP(row["totp_secret"])
            if not totp.verify(code):
                return None, "کد تأیید نامعتبر است"
            return {"message": "Verified"}, None
        finally:
            cursor.close()
            release_connection(conn)
