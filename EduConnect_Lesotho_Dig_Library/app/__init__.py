from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    from config.config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Add custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        from markupsafe import Markup
        if text is None:
            return ''
        return Markup(str(text).replace('\n', '<br>\n'))
    
    @app.template_filter('filesize')
    def filesize_filter(value):
        """Convert bytes to human readable file size"""
        if value is None:
            return ''
        try:
            bytes_value = int(value)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} TB"
        except (ValueError, TypeError):
            return str(value)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.books import books_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.subscription import subscription_bp
    from app.routes.summarize_search import summarize_search_bp
    from app.routes.ai_chat import ai_chat_bp
    from app.routes.offline import offline_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(books_bp, url_prefix='/books')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(subscription_bp)
    app.register_blueprint(summarize_search_bp)
    app.register_blueprint(ai_chat_bp)
    app.register_blueprint(offline_bp)
    # ...existing code...
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        from flask import render_template, flash
        flash('File too large. Maximum size is 100MB.', 'error')
        return render_template('errors/413.html'), 413
    
    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/library.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('EduConnect Lesotho Digital Library startup')
    
    # Context processors for templates
    @app.context_processor
    def inject_globals():
        from app.models.notification import Notification
        from flask_login import current_user
        from flask_wtf.csrf import generate_csrf
        from datetime import timedelta
        
        unread_notifications = 0
        if current_user.is_authenticated:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        
        def get_category_bg_and_overlay(category):
            # Example logic: choose background and overlay color based on category name
            name = getattr(category, 'name', '').lower()
            if 'academic' in name:
                bg = '/static/images/bg_academic.jpg'
                overlay = 'rgba(44, 62, 80, 0.6)'
            elif 'literature' in name:
                bg = '/static/images/bg_literature.jpg'
                overlay = 'rgba(123, 31, 162, 0.5)'
            elif 'science' in name or 'technology' in name:
                bg = '/static/images/bg_science.jpg'
                overlay = 'rgba(0, 150, 136, 0.5)'
            elif 'history' in name or 'culture' in name:
                bg = '/static/images/bg_history.jpg'
                overlay = 'rgba(255, 193, 7, 0.5)'
            elif 'health' in name or 'medicine' in name:
                bg = '/static/images/bg_health.jpg'
                overlay = 'rgba(233, 30, 99, 0.5)'
            else:
                bg = '/static/images/bg_default.jpg'
                overlay = 'rgba(33, 150, 243, 0.4)'
            return f'{bg}|{overlay}'

        return {
            'unread_notifications': unread_notifications,
            'library_name': app.config.get('LIBRARY_NAME', 'EduConnect Lesotho Digital Library'),
            'csrf_token': generate_csrf,
            'timedelta': timedelta,
            'get_category_bg_and_overlay': get_category_bg_and_overlay
        }
    
    # Template filters
    @app.template_filter('datetime')
    def datetime_filter(datetime_obj, format='%Y-%m-%d %H:%M'):
        """Format datetime objects in templates"""
        if datetime_obj is None:
            return ""
        return datetime_obj.strftime(format)
    
    @app.template_filter('filesize')
    def filesize_filter(size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    return app