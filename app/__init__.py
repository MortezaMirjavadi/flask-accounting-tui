from flask import Flask
from app.config import Config
from app.extensions import init_extensions
from app.routes import register_blueprints


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions (database, etc.)
    init_extensions(app)
    
    # Register all blueprints
    register_blueprints(app)
    
    return app
