from app import db
from datetime import datetime, timedelta

class BookReservation(db.Model):
    """Book reservations for when books are not available"""
    __tablename__ = 'book_reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    reserved_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('active', 'fulfilled', 'cancelled', 'expired'), default='active')
    notified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    fulfilled_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    def __init__(self, **kwargs):
        super(BookReservation, self).__init__(**kwargs)
        if self.expires_at is None:
            # Reservations expire after 7 days
            self.expires_at = datetime.utcnow() + timedelta(days=7)
    
    def is_expired(self):
        """Check if reservation has expired"""
        return datetime.utcnow() > self.expires_at
    
    def cancel(self, notes=None):
        """Cancel the reservation"""
        self.status = 'cancelled'
        if notes:
            self.notes = notes
        db.session.commit()
    
    def fulfill(self, notes=None):
        """Mark reservation as fulfilled"""
        self.status = 'fulfilled'
        self.fulfilled_at = datetime.utcnow()
        if notes:
            self.notes = notes
        db.session.commit()
    
    def mark_notified(self):
        """Mark that user has been notified"""
        self.notified = True
        db.session.commit()
    
    def extend_expiry(self, days=7):
        """Extend reservation expiry"""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'reserved_date': self.reserved_date.isoformat() if self.reserved_date else None,
            'status': self.status,
            'notified': self.notified,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'fulfilled_at': self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            'is_expired': self.is_expired(),
            'notes': self.notes
        }
    
    @staticmethod
    def cleanup_expired():
        """Mark expired reservations"""
        expired_count = BookReservation.query.filter(
            BookReservation.status == 'active',
            BookReservation.expires_at < datetime.utcnow()
        ).update({'status': 'expired'})
        
        db.session.commit()
        return expired_count
    
    def __repr__(self):
        return f'<BookReservation {self.id}: User {self.user_id} - Book {self.book_id}>'