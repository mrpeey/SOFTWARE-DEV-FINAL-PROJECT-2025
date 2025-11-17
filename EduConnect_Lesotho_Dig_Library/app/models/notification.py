from app import db
from datetime import datetime

class Notification(db.Model):
    """System notifications for users"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # NULL for system-wide
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum('info', 'warning', 'success', 'error'), default='info')
    is_read = db.Column(db.Boolean, default=False)
    is_system_wide = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=1)  # 1=low, 2=medium, 3=high
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        db.session.commit()
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'is_system_wide': self.is_system_wide,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }
    
    @staticmethod
    def create_system_notification(title, message, notification_type='info', priority=1, expires_at=None):
        """Create a system-wide notification"""
        notification = Notification(
            title=title,
            message=message,
            type=notification_type,
            is_system_wide=True,
            priority=priority,
            expires_at=expires_at
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'