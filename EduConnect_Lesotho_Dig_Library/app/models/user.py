from app import db
from app.models.user_favorites import user_favorites
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import hashlib
import secrets

class UserRole(db.Model):
    """User roles for role-based access control"""
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<UserRole {self.role_name}>'

class User(UserMixin, db.Model):
    """User model with role-based access and library features"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))
    address = db.Column(db.Text)
    district = db.Column(db.String(50), default='Butha-Buthe', index=True)
    profile_image = db.Column(db.String(500))  # Path to profile image
    role_id = db.Column(db.Integer, db.ForeignKey('user_roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    borrowing_transactions = db.relationship('BorrowingTransaction', foreign_keys='BorrowingTransaction.user_id', backref='user', lazy='dynamic')
    digital_downloads = db.relationship('DigitalDownload', backref='user', lazy='dynamic')
    offline_tokens = db.relationship('OfflineToken', backref='user', lazy='dynamic')
    reading_sessions = db.relationship('ReadingSession', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    book_reservations = db.relationship('BookReservation', backref='user', lazy='dynamic')
    book_reviews = db.relationship('BookReview', backref='user', lazy='dynamic')
    literacy_progress = db.relationship('LiteracyProgress', backref='user', lazy='dynamic')

    # Favorites relationship (many-to-many with Book)
    favorites = db.relationship('Book', secondary='user_favorites', backref='favorited_by', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role_id is None:
            # Default role for new users
            default_role = UserRole.query.filter_by(role_name='public').first()
            if default_role:
                self.role_id = default_role.id
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def can(self, permission):
        """Check if user has a specific permission"""
        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_system'],
            'librarian': ['read', 'write', 'manage_books', 'manage_borrowing'],
            'student': ['read', 'borrow', 'download'],
            'public': ['read', 'borrow_limited'],
            'researcher': ['read', 'borrow', 'download', 'extended_access']
        }
        
        user_permissions = role_permissions.get(self.role.role_name, [])
        return permission in user_permissions
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role.role_name == 'admin'
    
    def is_librarian(self):
        """Check if user is librarian or admin"""
        return self.role.role_name in ['admin', 'librarian']
    
    def get_current_borrowings(self):
        """Get currently borrowed books"""
        from app.models.borrowing import BorrowingTransaction
        return self.borrowing_transactions.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).all()
    
    def get_borrowing_count(self):
        """Get count of currently borrowed books"""
        return len(self.get_current_borrowings())
    
    def can_borrow_more(self):
        """Check if user can borrow more books"""
        # Admin users can always borrow
        if self.is_admin():
            return True
            
        # Check subscription status for non-admin users
        current_subscription = self.get_current_subscription()
        if not current_subscription:
            return False
            
        max_books = current_subscription.plan.max_books
        return self.get_borrowing_count() < max_books
    
    def has_overdue_books(self):
        """Check if user has overdue books"""
        from app.models.borrowing import BorrowingTransaction
        return self.borrowing_transactions.filter_by(status='overdue').count() > 0
    
    def get_total_fines(self):
        """Get total unpaid fines"""
        from app.models.borrowing import BorrowingTransaction
        total = db.session.query(db.func.sum(BorrowingTransaction.fine_amount)).filter(
            BorrowingTransaction.user_id == self.id,
            BorrowingTransaction.fine_paid == False
        ).scalar()
        return total or 0.0
    
    def can_access_digital_resources(self):
        """Check if user can access digital resources"""
        # Check if user has fines or restrictions
        if self.has_overdue_books() and self.get_total_fines() > 0:
            return False
        return True
    
    def generate_offline_token(self, resources=None, days=30):
        """Generate offline access token"""
        from app.models.offline import OfflineToken
        
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        offline_token = OfflineToken(
            user_id=self.id,
            token_hash=token_hash,
            resources_included=resources or [],
            expiry_date=datetime.utcnow() + timedelta(days=days)
        )
        
        db.session.add(offline_token)
        db.session.commit()
        
        return token
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_reading_statistics(self):
        """Get user reading statistics"""
        from app.models.offline import ReadingSession
        from app.models.borrowing import BorrowingTransaction
        
        stats = {}
        
        # Total books borrowed
        stats['total_borrowed'] = self.borrowing_transactions.count()
        
        # Books currently borrowed
        stats['current_borrowed'] = self.get_borrowing_count()
        
        # Total reading time (in minutes) - calculated in Python for database compatibility
        sessions = ReadingSession.query.filter(
            ReadingSession.user_id == self.id,
            ReadingSession.session_end.isnot(None)
        ).all()
        
        total_time = 0
        for session in sessions:
            if session.session_start and session.session_end:
                duration = session.session_end - session.session_start
                total_time += duration.total_seconds() / 60  # Convert to minutes
        
        stats['total_reading_time'] = int(total_time)
        
        # Digital downloads
        stats['total_downloads'] = self.digital_downloads.count()
        
        # Favorite category
        from app.models.book import Book, Category
        favorite_category = db.session.query(Category.name).join(
            Book, Category.id == Book.category_id
        ).join(
            BorrowingTransaction, Book.id == BorrowingTransaction.book_id
        ).filter(
            BorrowingTransaction.user_id == self.id
        ).group_by(Category.id).order_by(
            db.func.count(BorrowingTransaction.id).desc()
        ).first()
        
        stats['favorite_category'] = favorite_category[0] if favorite_category else 'N/A'
        
        return stats
    
    def get_current_subscription(self):
        """Get user's current active subscription"""
        from app.models.subscription import UserSubscription
        return UserSubscription.query.filter_by(
            user_id=self.id,
            is_active=True
        ).filter(
            UserSubscription.end_date > datetime.utcnow()
        ).first()
    
    def has_active_subscription(self):
        """Check if user has an active subscription"""
        # Admin users don't need subscriptions
        if self.is_admin():
            return True
        
        subscription = self.get_current_subscription()
        return subscription is not None and not subscription.is_expired
    
    def can_access_digital_content(self):
        """Check if user can access digital content (downloads)"""
        # Admin users can always access
        if self.is_admin():
            return True
        
        # Users with active subscriptions can access
        if self.has_active_subscription():
            return True
        
        # For expired subscriptions, no access even with pending bills
        return False
    
    def can_borrow_physical_books(self):
        """Check if user can borrow physical books (stricter than digital access)"""
        # Admin users can always borrow
        if self.is_admin():
            return True
        
        # Regular users need active subscription to borrow physical books
        return self.has_active_subscription()
    
    def get_subscription_status(self):
        """Get detailed subscription status"""
        # Admin users don't need subscriptions
        if self.is_admin():
            return {
                'status': 'admin',
                'message': 'Admin access - no subscription required',
                'can_borrow': True,
                'can_download': True
            }
            
        subscription = self.get_current_subscription()
        if not subscription:
            return {
                'status': 'no_subscription',
                'message': 'No active subscription',
                'can_borrow': False,
                'can_download': False
            }
        
        if subscription.is_expired:
            # Check if user has been billed for renewal
            from app.models.subscription import BillingRecord
            pending_renewal = BillingRecord.query.filter_by(
                user_id=self.id,
                billing_type='subscription',
                status='pending'
            ).filter(
                BillingRecord.created_at >= subscription.end_date
            ).first()
            
            if pending_renewal:
                return {
                    'status': 'expired_with_pending_renewal',
                    'message': f'Subscription expired. Please pay renewal bill to restore access.',
                    'can_borrow': False,
                    'can_download': False,
                    'expired_date': subscription.end_date,
                    'pending_bill_amount': float(pending_renewal.amount)
                }
            else:
                return {
                    'status': 'expired',
                    'message': 'Subscription has expired',
                    'can_borrow': False,
                    'can_download': False,
                    'expired_date': subscription.end_date
                }
        
        return {
            'status': 'active',
            'message': f'Active until {subscription.end_date.strftime("%Y-%m-%d")}',
            'can_borrow': True,
            'can_download': True,
            'plan_name': subscription.plan.name,
            'days_remaining': subscription.days_remaining,
            'max_books': subscription.plan.max_books
        }
    
    def get_pending_bills(self):
        """Get user's pending bills"""
        from app.models.subscription import BillingRecord
        return BillingRecord.query.filter_by(
            user_id=self.id,
            status='pending'
        ).all()
    
    def get_total_outstanding_amount(self):
        """Get total amount owed by user"""
        from app.models.subscription import BillingRecord
        total = db.session.query(db.func.sum(BillingRecord.amount)).filter_by(
            user_id=self.id,
            status='pending'
        ).scalar()
        return total or 0.0
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'district': self.district,
            'role': self.role.role_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def get_profile_image_url(self):
        """Return the correct static URL for the user's profile image."""
        if self.profile_image:
            # Ensure path starts with 'uploads/profiles/' if not already
            if not self.profile_image.startswith('uploads/profiles/'):
                return 'uploads/profiles/' + self.profile_image
            return self.profile_image
        return 'images/default_profile.png'
    
    def __repr__(self):
        return f'<User {self.username}>'
