import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'butha-buthe-library-secret-key-2024'
    
    # Database configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'library_user'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'library_password'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'butha_buthe_library'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI") or f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,  # Recycle connections every hour
        'pool_pre_ping': True,  # Verify connections before use
        'pool_timeout': 30,
        'max_overflow': 10
    }
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'epub', 'txt', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Pagination
    BOOKS_PER_PAGE = 12
    USERS_PER_PAGE = 20
    TRANSACTIONS_PER_PAGE = 25
    
    # Library specific settings
    DEFAULT_BORROWING_DAYS = 14
    MAX_RENEWALS = 2
    MAX_BOOKS_PER_USER = 5
    FINE_PER_DAY = 1.00  # Local currency
    OFFLINE_ACCESS_DAYS = 30
    
    # Email configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Analytics and logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', 'library.log')
    
    # Feature flags
    ALLOW_PUBLIC_REGISTRATION = True
    ENABLE_OFFLINE_ACCESS = True
    ENABLE_DIGITAL_LITERACY_TRACKING = True
    ENABLE_BOOK_REVIEWS = True
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Create upload directories if they don't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'books'), exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'covers'), exist_ok=True)
        
        # Create logs directory
        os.makedirs(os.path.dirname(app.config['LOG_FILE']), exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Use SQLite for easier development setup
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI") or 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'library.db')
    
    # Simplified engine options for SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_timeout': 30
    }
    
    # CSRF protection enabled
    WTF_CSRF_ENABLED = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Enhanced security for production
    WTF_CSRF_SSL_STRICT = True
    
    # Production database with connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 30
    }

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    MYSQL_DB = 'butha_buthe_library_test'
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/butha_buthe_library_test"

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
