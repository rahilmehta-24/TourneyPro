from flask import Flask, request, session, flash, redirect, url_for
from config import Config
from app.domain.models import db
from flask_compress import Compress
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, CSRFError
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
    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'baseline-society-jwt-secret-key-32-chars-minimum-prod'
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
                # Ensure newly added columns exist on existing tables in SQLite/Postgres
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                if 'registrations' in tables:
                    reg_cols = [c['name'] for c in inspector.get_columns('registrations')]
                    if 'payment_method' not in reg_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE registrations ADD COLUMN payment_method VARCHAR(50)"))
                if 'participants' in tables:
                    part_cols = [c['name'] for c in inspector.get_columns('participants')]
                    if 'payment_status' not in part_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE participants ADD COLUMN payment_status VARCHAR(20) DEFAULT 'paid'"))
                    if 'payment_method' not in part_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE participants ADD COLUMN payment_method VARCHAR(50)"))
                if 'categories' in tables:
                    cat_cols = [c['name'] for c in inspector.get_columns('categories')]
                    if 'draw_published' not in cat_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE categories ADD COLUMN draw_published BOOLEAN DEFAULT FALSE"))
                    if 'group_structure_mode' not in cat_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE categories ADD COLUMN group_structure_mode VARCHAR(20) DEFAULT 'auto'"))
                if 'matches' in tables:
                    match_cols = [c['name'] for c in inspector.get_columns('matches')]
                    if 'lock_version' not in match_cols:
                        with db.engine.begin() as conn:
                            conn.execute(text("ALTER TABLE matches ADD COLUMN lock_version INTEGER DEFAULT 1"))

                from app.web.controllers.auth import bootstrap_superadmin
                bootstrap_superadmin()
            except Exception as e:
                import logging
                logging.error(f'Error during db.create_all / column check: {e}')

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

        if s1_str == "W/O" or s2_str == "W/O":
            return "W/O"

        import re
        if s1_str and s2_str and '-' not in s1_str and '-' not in s2_str:
            return f"{s1_str} \u2013 {s2_str}"
        elif s1_str and '-' in s1_str:
            formatted = re.sub(r'\((\d+)\)', r'<sup>\1</sup>', s1_str)
            if ('RET' in s1_str or 'RET' in s2_str) and 'RET' not in formatted:
                formatted = f"{formatted}, RET"
            return formatted
        elif s1_str and s2_str:
            return f"{s1_str} \u2013 {s2_str}"
        return s1_str or s2_str

    @app.template_filter('participant_players')
    def participant_players_filter(participant):
        from app.services.utils.scheduler import extract_participant_players
        return extract_participant_players(participant)

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if not s:
            return ""
        import markupsafe
        return markupsafe.Markup(markupsafe.escape(s).replace('\n', '<br>\n'))

    @app.before_request
    def ensure_session_permanent():
        session.permanent = True

    # Cache Control Middleware for static assets & Security Headers (OWASP ASVS SEC-081, SEC-084, SEC-086, SEC-087)
    @app.after_request
    def add_security_and_cache_headers(response):
        # HTTP Security Headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https: ws: wss:; "
            "frame-ancestors 'self';"
        )
        
        # Strip server signature headers (SEC-060, SEC-094)
        response.headers.pop('X-Powered-By', None)
        response.headers.pop('Server', None)

        # Enforce HSTS on production / Vercel HTTPS deployments (SEC-081)
        if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # CORS restrictions for API routes (SEC-084)
        if request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            trusted_origins = os.environ.get(
                'TRUSTED_ORIGINS',
                'http://localhost:3000,http://localhost:5001,http://127.0.0.1:3000,http://127.0.0.1:5001,http://localhost:8081,http://localhost:19006'
            ).split(',')
            trusted_origins = [o.strip() for o in trusted_origins if o.strip()]
            
            if origin:
                is_trusted = (
                    origin in trusted_origins or
                    origin.startswith('http://localhost:') or
                    origin.startswith('http://127.0.0.1:') or
                    origin.startswith('exp://')
                )
                if is_trusted:
                    response.headers['Access-Control-Allow-Origin'] = origin
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'

        # Cache static files for 1 hour; prevent proxies/CDN/browsers from caching dynamic HTML with CSRF tokens
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        elif not request.path.startswith('/api/'):
            if 'Cache-Control' not in response.headers:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        return response

    # Inject current_user into templates
    @app.context_processor
    def inject_user():
        from app.web.controllers.auth import get_current_user
        return dict(current_user=get_current_user())

    import traceback
    import logging

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        db.session.rollback()
        logging.warning(f"CSRF validation failed: {getattr(e, 'description', str(e))}")
        if request.path.startswith('/api/'):
            return {"success": False, "message": "Security token has expired or is invalid. Please refresh the page."}, 400
        flash("Your session security token has expired. Please try submitting again.", "warning")
        referrer = request.referrer
        if referrer and (referrer.startswith(request.host_url) or referrer.startswith('/')):
            return redirect(referrer)
        return redirect(url_for('main.index'))

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
            "<div style='font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;padding:3rem;text-align:center;color:#0B2B20;max-width:600px;margin:4rem auto;border-radius:14px;background:#FDFBF6;border:1px solid #DDD4BF;border-top:4px solid #B5593A;box-shadow:0 10px 28px rgba(11,43,32,0.12);'>"
            "<h2 style='margin-bottom:0.75rem;color:#0B2B20;'>Something went wrong</h2>"
            "<p style='color:#2F4A3E;line-height:1.6;'>An unexpected server error occurred while processing your request. The issue has been logged securely.</p>"
            "<a href='/' style='display:inline-block;margin-top:1.5rem;padding:0.65rem 1.4rem;background:#0F3D2E;color:#FDFBF6;border-radius:8px;text-decoration:none;font-weight:600;'>Return to Home</a>"
            "</div>",
            500
        )

    return app
