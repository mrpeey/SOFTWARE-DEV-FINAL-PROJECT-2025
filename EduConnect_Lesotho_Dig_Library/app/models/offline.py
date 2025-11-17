from app import db
from datetime import datetime, timedelta
import json

class OfflineToken(db.Model):
    """Offline access tokens for low-bandwidth environments"""
    __tablename__ = 'offline_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(255), unique=True, nullable=False)
    resources_included = db.Column(db.JSON)  # List of book IDs accessible offline
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=False)
    last_sync = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    device_info = db.Column(db.Text)
    
    def is_expired(self):
        """Check if token has expired"""
        return datetime.utcnow() > self.expiry_date
    
    def is_valid(self):
        """Check if token is valid"""
        return self.is_active and not self.is_expired()
    
    def get_resources(self):
        """Get list of resource IDs"""
        if self.resources_included:
            return self.resources_included
        return []
    
    def add_resource(self, book_id):
        """Add a book to offline access"""
        resources = self.get_resources()
        if book_id not in resources:
            resources.append(book_id)
            self.resources_included = resources
            db.session.commit()
    
    def remove_resource(self, book_id):
        """Remove a book from offline access"""
        resources = self.get_resources()
        if book_id in resources:
            resources.remove(book_id)
            self.resources_included = resources
            db.session.commit()
    
    def update_sync(self):
        """Update last sync timestamp"""
        self.last_sync = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivate the token"""
        self.is_active = False
        db.session.commit()
    
    def extend_expiry(self, days=30):
        """Extend token expiry"""
        self.expiry_date = datetime.utcnow() + timedelta(days=days)
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired(),
            'is_valid': self.is_valid(),
            'resource_count': len(self.get_resources()),
            'device_info': self.device_info
        }
    
    def __repr__(self):
        return f'<OfflineToken {self.id}: User {self.user_id}>'

class DigitalDownload(db.Model):
    """Track digital downloads"""
    __tablename__ = 'digital_downloads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    download_date = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    file_size = db.Column(db.BigInteger)
    download_complete = db.Column(db.Boolean, default=True)
    offline_access_granted = db.Column(db.Boolean, default=False)
    offline_expiry_date = db.Column(db.Date)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'download_date': self.download_date.isoformat() if self.download_date else None,
            'file_size': self.file_size,
            'download_complete': self.download_complete,
            'offline_access_granted': self.offline_access_granted,
            'offline_expiry_date': self.offline_expiry_date.isoformat() if self.offline_expiry_date else None
        }
    
    def __repr__(self):
        return f'<DigitalDownload {self.id}: User {self.user_id} - Book {self.book_id}>'

class ReadingSession(db.Model):
    """Track reading sessions for analytics"""
    __tablename__ = 'reading_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    session_start = db.Column(db.DateTime, default=datetime.utcnow)
    session_end = db.Column(db.DateTime)
    pages_read = db.Column(db.Integer, default=0)
    reading_progress = db.Column(db.Numeric(5, 2), default=0.00)  # percentage
    device_type = db.Column(db.String(50))
    is_offline = db.Column(db.Boolean, default=False)
    
    def end_session(self, pages_read=None, progress=None):
        """End the reading session"""
        self.session_end = datetime.utcnow()
        if pages_read:
            self.pages_read = pages_read
        if progress:
            self.reading_progress = progress
        db.session.commit()
    
    def get_duration_minutes(self):
        """Get session duration in minutes"""
        if not self.session_end:
            return 0
        delta = self.session_end - self.session_start
        return int(delta.total_seconds() / 60)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'session_end': self.session_end.isoformat() if self.session_end else None,
            'duration_minutes': self.get_duration_minutes(),
            'pages_read': self.pages_read,
            'reading_progress': float(self.reading_progress) if self.reading_progress else 0.0,
            'device_type': self.device_type,
            'is_offline': self.is_offline
        }
    
    def __repr__(self):
        return f'<ReadingSession {self.id}: User {self.user_id} - Book {self.book_id}>'

class LiteracyProgress(db.Model):
    """Track digital literacy progress"""
    __tablename__ = 'literacy_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_category = db.Column(db.String(100), nullable=False)
    skill_name = db.Column(db.String(200), nullable=False)
    progress_percentage = db.Column(db.Numeric(5, 2), default=0.00)
    completed = db.Column(db.Boolean, default=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    resources_used = db.Column(db.JSON)  # Array of resource IDs used for learning
    
    def update_progress(self, percentage, resource_id=None):
        """Update progress percentage"""
        self.progress_percentage = percentage
        self.last_activity = datetime.utcnow()
        
        if percentage >= 100:
            self.completed = True
        
        if resource_id:
            resources = self.resources_used or []
            if resource_id not in resources:
                resources.append(resource_id)
                self.resources_used = resources
        
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'skill_category': self.skill_category,
            'skill_name': self.skill_name,
            'progress_percentage': float(self.progress_percentage) if self.progress_percentage else 0.0,
            'completed': self.completed,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'resources_used': self.resources_used or []
        }
    
    def __repr__(self):
        return f'<LiteracyProgress {self.id}: User {self.user_id} - {self.skill_name}>'