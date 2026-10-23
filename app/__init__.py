from flask import Flask, request
from config import Config
from app.domain.models import db
from flask_compress import Compress
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os

migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    Compress(app)
    csrf.init_app(app)
    
    
    
    # Initialize JWT and Marshmallow
    app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY', 'super-secret')  # Use app secret key for JWT
    jwt = JWTManager(app)
    
    from app.domain.schemas import ma
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
                from app.web.controllers.auth import bootstrap_superadmin
                bootstrap_superadmin()
            except Exception as e:
                import logging
                logging.error(f'Error during db.create_all: {e}')

    # Register Blueprints
    from app.web.controllers.main import main_bp
    from app.web.controllers.tournament import tournament_bp
    from app.web.controllers.category import category_bp
    from app.web.controllers.export import export_bp
    from app.web.controllers.auth import auth_bp
    from app.web.controllers.leaderboard import leaderboard_bp
    from app.web.controllers.player import player_bp
    from app.web.controllers.academy import academy_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(tournament_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(academy_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(player_bp)
    
    
    
    from app.api import api_bp
    csrf.exempt(api_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")

    @app.template_filter('ist')
    def to_ist_filter(dt, format_str="%d %b %Y, %I:%M %p"):
        if not dt:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime(format_str)

    @app.template_filter('format_tennis_score')
    def format_tennis_score(score_str):
        if not score_str:
            return ""
        import re
        return re.sub(r'\((\d+)\)', r'<sup>\1</sup>', score_str)

    @app.template_filter('display_match_score')
    def display_match_score_filter(match):
        """
        Formats a match scoreline for display:
        - If score1 and score2 are numeric totals (e.g. team ties 17 and 4, or 8 and 13):
          Returns '17 – 4'
        - If score1 already contains '-' (e.g. '6-4, 6-3' or '6-1'):
          Formats with tiebreak superscripts if applicable: '6-4, 6-3'
        - If only score1 is present: returns score1
        - If neither: returns ''
        """
        if not match:
            return ""
        if isinstance(match, str):
            return match
        if isinstance(match, dict):
            s1 = match.get('score1')
            s2 = match.get('score2')
        else:
            s1 = getattr(match, 'score1', None)
            s2 = getattr(match, 'score2', None)

        s1_str = str(s1).strip() if s1 is not None else ""
        s2_str = str(s2).strip() if s2 is not None else ""

        if not s1_str and not s2_str:
            return ""

        import re
        if s1_str and s2_str and '-' not in s1_str and '-' not in s2_str:
            return f"{s1_str} \u2013 {s2_str}"
        elif s1_str and '-' in s1_str:
            return re.sub(r'\((\d+)\)', r'<sup>\1</sup>', s1_str)
        elif s1_str and s2_str:
            return f"{s1_str} \u2013 {s2_str}"
        return s1_str or s2_str

    @app.template_filter('participant_players')
    def participant_players_filter(participant):
        from app.services.utils.scheduler import extract_participant_players
        return extract_participant_players(participant)

    # Cache Control Middleware for static assets & Security Headers
    @app.after_request
    def add_cache_headers(response):
        # Global Security & Watermark Headers
        response.headers['X-Author'] = 'Built for Tennis by Rahil Mehta'
        response.headers['X-Powered-By'] = 'TourneyPro Engine'
        
        # Cache static files for 1 hour
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    # Inject current_user into templates
    @app.context_processor
    def inject_user():
        from app.web.controllers.auth import get_current_user
        return dict(current_user=get_current_user())

    import traceback
    import logging

    @app.errorhandler(Exception)
    def handle_exception(e):
        db.session.rollback()
        logging.error(f"Unhandled Exception: {str(e)}")
        logging.error(traceback.format_exc())
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        if request.path.startswith('/api/'):
            return {"success": False, "message": "An internal server error occurred."}, 500
        return (
            "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;padding:3rem;text-align:center;color:#18181b;max-width:600px;margin:4rem auto;border-radius:12px;background:#f4f4f5;box-shadow:0 4px 12px rgba(0,0,0,0.05);'>"
            "<h2 style='margin-bottom:0.75rem;color:#09090b;'>Something went wrong</h2>"
            "<p style='color:#71717a;line-height:1.6;'>An unexpected server error occurred while processing your request. The issue has been logged securely.</p>"
            "<a href='/' style='display:inline-block;margin-top:1.5rem;padding:0.65rem 1.4rem;background:#2563eb;color:#ffffff;border-radius:8px;text-decoration:none;font-weight:600;'>Return to Home</a>"
            "</div>",
            500
        )

    return app
