from app.routes.auth import bp as auth_bp
from app.routes.categories import bp as categories_bp
from app.routes.sources import bp as sources_bp
from app.routes.wallets import bp as wallets_bp
from app.routes.transactions import bp as transactions_bp
from app.routes.budget import bp as budget_bp
from app.routes.reports import bp as reports_bp
from app.routes.settings import bp as settings_bp
from app.routes.installments import bp as installments_bp
from app.routes.checks import bp as checks_bp
from app.routes.debts import bp as debts_bp
from app.routes.metadata import bp as metadata_bp
from app.routes.calendar import bp as calendar_bp
from app.routes.alerts import bp as alerts_bp
from app.routes.exchange_rates import bp as exchange_rates_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(sources_bp, url_prefix='/api/sources')
    app.register_blueprint(wallets_bp, url_prefix='/api/wallets')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(budget_bp, url_prefix='/api/budget')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(installments_bp, url_prefix='/api/installments')
    app.register_blueprint(checks_bp, url_prefix='/api/checks')
    app.register_blueprint(debts_bp, url_prefix='/api/debts')
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(exchange_rates_bp, url_prefix='/api/exchange-rates')
