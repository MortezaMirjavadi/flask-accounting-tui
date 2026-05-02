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
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            
            if row is None or not check_password_hash(row["password_hash"], password):
                return None, "Invalid username or password"
            
            return {"id": row["id"], "username": row["username"]}, None
        finally:
            cursor.close()
            release_connection(conn)
    
    @staticmethod
    def get_user_by_username(username):
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, username, created_at FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            
            if row is None:
                return None, "User not found"
            
            return dict(row), None
        finally:
            cursor.close()
            release_connection(conn)
