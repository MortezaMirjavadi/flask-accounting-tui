import pyotp
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, release_connection


class AuthService:
    @staticmethod
    def register_user(username, password):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return None, "Username already exists"
            
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, password_hash),
            )
            new_id = cursor.fetchone()['id']
            conn.commit()
            
            return {"id": new_id, "username": username}, None
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
                "SELECT id, username, password_hash, totp_enabled FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()

            if row is None or not check_password_hash(row["password_hash"], password):
                return None, "Invalid username or password"

            return {"id": row["id"], "username": row["username"], "totp_enabled": row.get("totp_enabled", False)}, None
        finally:
            cursor.close()
            release_connection(conn)
    
    @staticmethod
    def get_user_by_username(username):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, username, created_at, totp_enabled FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            
            if row is None:
                return None, "User not found"
            
            return dict(row), None
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
            return None, "Invalid verification code"
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
                return None, "2FA not enabled for this user"
            totp = pyotp.TOTP(row["totp_secret"])
            if not totp.verify(code):
                return None, "Invalid verification code"
            return {"message": "Verified"}, None
        finally:
            cursor.close()
            release_connection(conn)
