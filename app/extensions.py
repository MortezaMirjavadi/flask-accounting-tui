from database import init_db, get_connection


def init_extensions(app):
    print("Initializing database...")
    init_db()
