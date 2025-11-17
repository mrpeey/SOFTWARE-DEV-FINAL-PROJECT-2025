from app import db
from datetime import datetime, date, timedelta

class BorrowingTransaction(db.Model):
    """Borrowing transactions for tracking book loans"""
    __tablename__ = 'borrowing_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    borrowed_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)
    returned_date = db.Column(db.DateTime)
    status = db.Column(db.Enum('pending', 'borrowed', 'returned', 'overdue', 'renewed', 'rejected'), default='pending')
    renewal_count = db.Column(db.Integer, default=0)
    fine_amount = db.Column(db.Numeric(10, 2), default=0.00)
    fine_paid = db.Column(db.Boolean, default=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    librarian = db.relationship('User', foreign_keys=[librarian_id], backref='managed_transactions')
    
    def __init__(self, **kwargs):
        super(BorrowingTransaction, self).__init__(**kwargs)
        if self.due_date is None:
            from flask import current_app
            borrowing_days = current_app.config.get('DEFAULT_BORROWING_DAYS', 14)
            self.due_date = date.today() + timedelta(days=borrowing_days)
    
    def is_overdue(self):
        """Check if the book is overdue"""
        return self.status in ['borrowed', 'overdue'] and self.due_date < date.today()
    
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue():
            return 0
        return (date.today() - self.due_date).days
    
    def calculate_fine(self):
        """Calculate fine for overdue book"""
        if not self.is_overdue():
            return 0.00
        
        from flask import current_app
        fine_per_day = float(current_app.config.get('FINE_PER_DAY', 1.00))
        return self.days_overdue() * fine_per_day
    
    def update_fine(self):
        """Update fine amount"""
        if self.is_overdue():
            self.fine_amount = self.calculate_fine()
            if self.status != 'overdue':
                self.status = 'overdue'
            db.session.commit()
    
    def can_renew(self):
        """Check if book can be renewed"""
        from flask import current_app
        max_renewals = current_app.config.get('MAX_RENEWALS', 2)
        
        if self.renewal_count >= max_renewals:
            return False, f"Maximum renewals ({max_renewals}) reached"
        
        if self.status == 'overdue':
            return False, "Cannot renew overdue books"
        
        if self.user.has_overdue_books():
            return False, "Cannot renew while having overdue books"
        
        # Check if there are reservations for this book
        from app.models.reservation import BookReservation
        reservations = BookReservation.query.filter_by(
            book_id=self.book_id,
            status='active'
        ).count()
        
        if reservations > 0:
            return False, "Book has pending reservations"
        
        return True, "Can renew"
    
    def renew(self, librarian_id):
        """Renew the book"""
        can_renew, message = self.can_renew()
        if not can_renew:
            return False, message
        
        from flask import current_app
        borrowing_days = current_app.config.get('DEFAULT_BORROWING_DAYS', 14)
        
        self.due_date = date.today() + timedelta(days=borrowing_days)
        self.renewal_count += 1
        self.status = 'renewed'
        self.librarian_id = librarian_id
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True, "Book renewed successfully"
    
    def return_book(self, librarian_id, notes=None):
        """Return the book"""
        try:
            if self.status == 'returned':
                return False, "Book already returned"
            if not self.book:
                from flask import current_app
                current_app.logger.error(f"Return failed: Book object is None for transaction {self.id}")
                return False, "Book object missing"
            if not self.book.is_digital:
                if self.book.available_copies is None:
                    from flask import current_app
                    current_app.logger.error(f"Return failed: available_copies is None for book {self.book_id}")
                    return False, "Book available_copies missing"
                self.book.available_copies += 1
            self.returned_date = datetime.utcnow()
            self.status = 'returned'
            self.librarian_id = librarian_id
            if notes:
                self.notes = notes
            if self.is_overdue():
                self.update_fine()
            db.session.commit()
            self._notify_reservations()
            return True, "Book returned successfully"
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error processing return for transaction {self.id}: {str(e)}")
            return False, f"Error processing return: {str(e)}"
    
    def _notify_reservations(self):
        """Notify users with reservations that book is available"""
        from app.models.reservation import BookReservation
        from app.models.notification import Notification
        
        reservations = BookReservation.query.filter_by(
            book_id=self.book_id,
            status='active'
        ).order_by(BookReservation.reserved_date).all()
        
        if reservations and self.book.is_available():
            # Notify the first person in the reservation queue
            reservation = reservations[0]
            notification = Notification(
                user_id=reservation.user_id,
                title="Book Available",
                message=f"The book '{self.book.title}' is now available for borrowing.",
                type='info'
            )
            db.session.add(notification)
            db.session.commit()
    
    def get_duration_days(self):
        """Get borrowing duration in days"""
        end_date = self.returned_date or datetime.utcnow()
        return (end_date.date() - self.borrowed_date.date()).days
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.get_full_name() if self.user else None,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'book_author': self.book.author if self.book else None,
            'borrowed_date': self.borrowed_date.isoformat() if self.borrowed_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'returned_date': self.returned_date.isoformat() if self.returned_date else None,
            'status': self.status,
            'renewal_count': self.renewal_count,
            'fine_amount': float(self.fine_amount),
            'fine_paid': self.fine_paid,
            'is_overdue': self.is_overdue(),
            'days_overdue': self.days_overdue(),
            'duration_days': self.get_duration_days(),
            'notes': self.notes
        }
    
    @staticmethod
    def get_overdue_transactions():
        """Get all overdue transactions"""
        return BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue']),
            BorrowingTransaction.due_date < date.today()
        ).all()
    
    @staticmethod
    def update_overdue_status():
        """Update status of overdue books and calculate fines"""
        overdue_transactions = BorrowingTransaction.get_overdue_transactions()
        
        for transaction in overdue_transactions:
            transaction.update_fine()
        
        return len(overdue_transactions)
    
    def __repr__(self):
        return f'<BorrowingTransaction {self.id}: User {self.user_id} - Book {self.book_id}>'