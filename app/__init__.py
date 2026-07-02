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
        # Bootstrap default superadmin if db is empty
        from app.routes.auth import bootstrap_superadmin
        bootstrap_superadmin()

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.tournament import tournament_bp
    from app.routes.category import category_bp
    from app.routes.export import export_bp
    from app.routes.auth import auth_bp
    from app.routes.leaderboard import leaderboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(tournament_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(leaderboard_bp)

    # Inject current_user into templates
    @app.context_processor
    def inject_user():
        from app.routes.auth import get_current_user
        return dict(current_user=get_current_user())

    return app
