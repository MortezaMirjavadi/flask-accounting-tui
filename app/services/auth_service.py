from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection


class AuthService:
    @staticmethod
    def register_user(username, password):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return None, "Username already exists"
        
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return {"id": new_id, "username": username}, None
    
    @staticmethod
    def authenticate_user(username, password):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        conn.close()
        
        if row is None or not check_password_hash(row["password_hash"], password):
            return None, "Invalid username or password"
        
        return {"id": row["id"], "username": row["username"]}, None
    
    @staticmethod
    def get_user_by_username(username):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None, "User not found"
        
        return dict(row), None
