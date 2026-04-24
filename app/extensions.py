from database import init_db, get_connection


def init_extensions(app):
    @app.before_request
    def ensure_db():
        init_db()
