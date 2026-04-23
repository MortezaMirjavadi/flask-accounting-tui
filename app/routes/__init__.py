from app.routes.auth import bp as auth_bp
from app.routes.categories import bp as categories_bp
from app.routes.sources import bp as sources_bp
from app.routes.transactions import bp as transactions_bp
from app.routes.budget import bp as budget_bp
from app.routes.reports import bp as reports_bp
from app.routes.settings import bp as settings_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(sources_bp, url_prefix='/sources')
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(budget_bp, url_prefix='/budget')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
