from app import db
from app.models.user_favorites import user_favorites
from datetime import datetime

class Category(db.Model):
    """Book categories for organization"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    books = db.relationship('Book', backref='category', lazy='dynamic')
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    def get_book_count(self):
        """Get count of active books in this category"""
        return self.books.filter_by(is_active=True).count()
    
    def get_all_books(self, include_children=True):
        """Get all books in this category and optionally its children"""
        books = self.books.filter_by(is_active=True)
        
        if include_children:
            for child in self.children:
                books = books.union(child.get_all_books(include_children=True))
        
        return books
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'is_active': self.is_active,
            'book_count': self.get_book_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Book(db.Model):
    """Book model for both physical and digital resources"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    author = db.Column(db.String(300), nullable=False, index=True)
    isbn = db.Column(db.String(20), unique=True, index=True)
    publisher = db.Column(db.String(200))
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(50))
    pages = db.Column(db.Integer)
    language = db.Column(db.String(50), default='English')
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_digital = db.Column(db.Boolean, default=False, index=True)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)  # in bytes
    file_format = db.Column(db.String(20))  # PDF, EPUB, etc.
    cover_image = db.Column(db.String(500))
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Full-text search index
    __searchable__ = ['title', 'author', 'description']
    
    # Relationships
    borrowing_transactions = db.relationship('BorrowingTransaction', backref='book', lazy='dynamic')
    digital_downloads = db.relationship('DigitalDownload', backref='book', lazy='dynamic')
    reading_sessions = db.relationship('ReadingSession', backref='book', lazy='dynamic')
    book_reservations = db.relationship('BookReservation', backref='book', lazy='dynamic')
    book_reviews = db.relationship('BookReview', backref='book', lazy='dynamic')
    creator = db.relationship('User', backref='created_books', foreign_keys=[created_by])
    
    def is_available(self):
        """Check if book is available for borrowing"""
        if self.is_digital:
            return True  # Digital books are always available
        return self.available_copies > 0
    
    def can_be_borrowed_by(self, user):
        """Check if book can be borrowed by a specific user"""
        if not self.is_active:
            return False, "Book is not available"
    
        @staticmethod
        def update_cover_image(book_id, image_path):
            """Update the cover_image field for a book by ID"""
            from app import db
            book = Book.query.get(book_id)
            if book:
                book.cover_image = image_path
                db.session.commit()
                return True
            return False
        
        # Admin users can always borrow (skip subscription checks)
        if user.is_admin():
            if not self.is_digital and not self.is_available():
                return False, "Book is currently not available"
            return True, "Can borrow"
        
        # Check subscription status for borrowing physical books
        if not user.can_borrow_physical_books():
            subscription_status = user.get_subscription_status()
            if subscription_status['status'] == 'expired_with_pending_renewal':
                return False, "Subscription expired. Please pay pending bill to continue borrowing books."
            elif subscription_status['status'] == 'expired':
                return False, "Subscription expired. Please renew to continue borrowing books."
            else:
                return False, "You need an active subscription to borrow books"
        
        subscription_status = user.get_subscription_status()
        if subscription_status['status'] not in ['active', 'admin']:
            return False, f"Subscription issue: {subscription_status['message']}"
        
        if not user.can_borrow_more():
            current_subscription = user.get_current_subscription()
            max_books = current_subscription.plan.max_books if current_subscription else 1
            return False, f"You have reached your borrowing limit ({max_books} books)"
        
        if user.has_overdue_books():
            return False, "You have overdue books. Please return them first"
        
        # Check outstanding bills (only prevent borrowing if amount is significant)
        outstanding_amount = user.get_total_outstanding_amount()
        if outstanding_amount > 50:  # Allow small amounts, block larger debts
            return False, f"You have outstanding bills (LSL {outstanding_amount:.2f}). Please clear them first"
        
        if not self.is_digital and not self.is_available():
            return False, "Book is currently not available"
        
        # Check if user already has this book
        current_borrowing = user.borrowing_transactions.filter_by(
            book_id=self.id,
            status='borrowed'
        ).first()
        
        if current_borrowing:
            return False, "You already have this book borrowed"
        
        return True, "Can borrow"
    
    def can_be_downloaded_by(self, user):
        """Check if digital book can be downloaded by a specific user"""
        from flask import current_app
        
        current_app.logger.info(f"Download check for book {self.id} ({self.title}) by user {user.username}")
        current_app.logger.info(f"Book is_active: {self.is_active}, is_digital: {self.is_digital}")
        
        if not self.is_active:
            current_app.logger.warning(f"Download blocked: Book is not active")
            return False, "Book is not available"
        
        if not self.is_digital:
            current_app.logger.warning(f"Download blocked: Book is not marked as digital")
            return False, "This book is not available for download"
        
        # Only admin users can download without subscription
        user_role = user.role.role_name if hasattr(user, 'role') and user.role else 'unknown'
        current_app.logger.info(f"User role: {user_role}")

        if hasattr(user, 'role') and user.role and user.role.role_name == 'admin':
            current_app.logger.info(f"Download allowed: User is {user_role}")
            return True, "Can download"

        # All other users require active subscription
        if not user.can_access_digital_content():
            subscription_status = user.get_subscription_status()
            if subscription_status['status'] == 'expired':
                return False, "Subscription expired. Please renew to download books."
            else:
                return False, "You need an active subscription or pending renewal to download books"

        return True, "Can download with active subscription"
    
    def get_average_rating(self):
        """Get average rating from reviews"""
        avg_rating = db.session.query(db.func.avg(BookReview.rating)).filter(
            BookReview.book_id == self.id,
            BookReview.is_approved == True
        ).scalar()
        return round(avg_rating, 1) if avg_rating else 0.0
    
    @property
    def average_rating(self):
        """Property to access average rating (for template compatibility)"""
        return self.get_average_rating()
    
    def get_review_count(self):
        """Get count of approved reviews"""
        return self.book_reviews.filter_by(is_approved=True).count()
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        db.session.commit()
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        db.session.commit()
    
    def get_file_size_formatted(self):
        """Get formatted file size"""
        if not self.file_size:
            return "Unknown"
        
        size_bytes = self.file_size
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def get_popularity_score(self):
        """Calculate popularity score based on various metrics"""
        return (self.view_count * 1) + (self.download_count * 2) + (self.borrowing_transactions.count() * 3)
    
    def update_availability(self):
        """Update available copies based on current borrowings"""
        if self.is_digital:
            return  # Digital books don't have limited copies
        
        borrowed_count = self.borrowing_transactions.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count()
        
        self.available_copies = max(0, self.total_copies - borrowed_count)
        db.session.commit()
    
    def to_dict(self, include_file_info=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'publisher': self.publisher,
            'publication_year': self.publication_year,
            'edition': self.edition,
            'pages': self.pages,
            'language': self.language,
            'description': self.description,
            'category': self.category.name if self.category else None,
            'category_id': self.category_id,
            'is_digital': self.is_digital,
            'is_featured': self.is_featured,
            'total_copies': self.total_copies,
            'available_copies': self.available_copies,
            'is_available': self.is_available(),
            'average_rating': self.get_average_rating(),
            'review_count': self.get_review_count(),
            'view_count': self.view_count,
            'download_count': self.download_count,
            'popularity_score': self.get_popularity_score(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'cover_image': self.cover_image
        }
        
        if include_file_info and self.is_digital:
            data.update({
                'file_format': self.file_format,
                'file_size': self.file_size,
                'file_size_formatted': self.get_file_size_formatted()
            })
        
        return data
    
    @staticmethod
    def search(query, category_id=None, is_digital=None, language=None, limit=50):
        """Search books with various filters"""
        books = Book.query.filter_by(is_active=True)
        
        if query:
            # Simple text search (can be enhanced with full-text search)
            search_filter = db.or_(
                Book.title.ilike(f'%{query}%'),
                Book.author.ilike(f'%{query}%'),
                Book.description.ilike(f'%{query}%')
            )
            books = books.filter(search_filter)
        
        if category_id:
            books = books.filter_by(category_id=category_id)
        
        if is_digital is not None:
            books = books.filter_by(is_digital=is_digital)
        
        if language:
            books = books.filter_by(language=language)
        
        return books.limit(limit).all()
    
    def __repr__(self):
        return f'<Book {self.title}>'

# Import other models to avoid circular imports
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview