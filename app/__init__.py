from flask import Flask
from config import Config
from app.models import db
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Ensure instance folder exists
    try:
        os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    except OSError:
        pass
        
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.tournament import tournament_bp
    from app.routes.category import category_bp
    from app.routes.export import export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(tournament_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(export_bp)

    return app
