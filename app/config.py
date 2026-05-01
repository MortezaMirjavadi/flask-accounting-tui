import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # PostgreSQL configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'terminal_accounting')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    
    # Add other configuration as needed


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    # For testing, use a separate test database
    DB_NAME = 'terminal_accounting_test'
