from app import db
from datetime import datetime

class BookReview(db.Model):
    """Book reviews and ratings"""
    __tablename__ = 'book_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='rating_range'),
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_review'),
    )
    
    def approve(self):
        """Approve the review"""
        self.is_approved = True
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'profile_image': self.user.profile_image if self.user and self.user.profile_image else None,
            'book_id': self.book_id,
            'rating': self.rating,
            'review_text': self.review_text,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<BookReview {self.id}: User {self.user_id} - Book {self.book_id}>'