import os
# Load dotenv if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'baseline-society-jwt-secret-key-32-chars-minimum-prod'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 60 minutes
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 86400  # 30 days
    # Database file in 'instance' folder at root
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        db_url = db_url.strip().strip("'\"")
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif db_url.startswith('postgresql://') and not db_url.startswith('postgresql+'):
            db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        
    SQLALCHEMY_DATABASE_URI = db_url or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'tournaments.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if db_url and db_url.startswith('postgresql'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'connect_args': {
                'prepare_threshold': None
            }
        }
    # Session & Cookie Security (OWASP ASVS SEC-023, SEC-024, SEC-025, SEC-083)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production' or bool(os.environ.get('VERCEL'))
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days max session lifetime

    # CSRF Configuration - keep tokens valid for the full duration of the session
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Valid for lifetime of session (prevents premature 1-hour expiration)

    # Upload folder in 'app/web/static/uploads'
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'web', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Email & SMTP Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't', 'yes']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'The Baseline Society <confirmation@thebaselinesociety.com>'
    MAIL_CONFIRMATION_EMAIL = os.environ.get('MAIL_CONFIRMATION_EMAIL') or 'confirmation@thebaselinesociety.com'
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'false').lower() in ['true', '1', 't', 'yes']
    SUPERADMIN_EMAIL = os.environ.get('SUPERADMIN_EMAIL') or 'rahilmehta.ict19@gmail.com'

