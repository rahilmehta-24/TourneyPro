from flask import Flask, request
from config import Config
from app.models import db
from flask_compress import Compress
from flask_jwt_extended import JWTManager
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    Compress(app)
    
    
    
    # Initialize JWT and Marshmallow
    app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY', 'super-secret')  # Use app secret key for JWT
    jwt = JWTManager(app)
    
    from app.schemas import ma
    ma.init_app(app)

    # Ensure instance folder exists
    try:
        os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    except OSError:
        pass

    # Create upload folder
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError:
        pass

    with app.app_context():
        # In serverless environments, avoid running DB queries on boot to prevent cold-start timeouts
        if not os.environ.get('VERCEL'):
            try:
                db.create_all()
                from app.routes.auth import bootstrap_superadmin
                bootstrap_superadmin()
            except Exception as e:
                import logging
                logging.error(f'Error during db.create_all: {e}')

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
    
    
    
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    @app.template_filter('format_tennis_score')
    def format_tennis_score(score_str):
        if not score_str:
            return ""
        import re
        return re.sub(r'\((\d+)\)', r'<sup>\1</sup>', score_str)

    # Cache Control Middleware for static assets
    @app.after_request
    def add_cache_headers(response):
        # Cache static files for 1 hour
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    # Inject current_user into templates
    @app.context_processor
    def inject_user():
        from app.routes.auth import get_current_user
        return dict(current_user=get_current_user())

    import traceback
    import logging

    @app.errorhandler(Exception)
    def handle_exception(e):
        db.session.rollback()
        logging.error(f"Unhandled Exception: {str(e)}")
        logging.error(traceback.format_exc())
        return f"Internal Server Error: {str(e)}<br><br>Traceback:<br><pre>{traceback.format_exc()}</pre>", 500

    return app
