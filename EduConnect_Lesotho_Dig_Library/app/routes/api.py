
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app import db
from app.models.book import Book, Category
from app.models.user import User
from app.models.borrowing import BorrowingTransaction
from app.models.offline import OfflineToken, DigitalDownload
from app.models.review import BookReview
import hashlib
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)

@api_bp.route('/notifications/check', methods=['GET'])
@login_required
def check_notifications():
    """API endpoint to check notifications (placeholder)"""
    # You can replace this with real notification logic later
    return jsonify({
        'has_notifications': False,
        'count': 0,
        'notifications': []
    })

@api_bp.route('/books')
@login_required
def get_books():
    """API endpoint to get books"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 100)
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category', type=int)
    is_digital = request.args.get('digital')
    
    query = Book.query.filter_by(is_active=True)
    
    if search:
        search_filter = db.or_(
            Book.title.ilike(f'%{search}%'),
            Book.author.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if is_digital == 'true':
        query = query.filter_by(is_digital=True)
    elif is_digital == 'false':
        query = query.filter_by(is_digital=False)
    
    books = query.order_by(Book.title).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'books': [book.to_dict() for book in books.items],
        'pagination': {
            'page': books.page,
            'pages': books.pages,
            'per_page': books.per_page,
            'total': books.total,
            'has_next': books.has_next,
            'has_prev': books.has_prev
        }
    })

@api_bp.route('/books/<int:book_id>')
@login_required
def get_book(book_id):
    """API endpoint to get a specific book"""
    book = Book.query.get_or_404(book_id)
    
    if not book.is_active:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(book.to_dict(include_file_info=True))

@api_bp.route('/categories')
def get_categories():
    """API endpoint to get categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    return jsonify({
        'categories': [category.to_dict() for category in categories]
    })

@api_bp.route('/user/profile')
@login_required
def get_user_profile():
    """API endpoint to get current user profile"""
    return jsonify(current_user.to_dict())

@api_bp.route('/user/borrowings')
@login_required
def get_user_borrowings():
    """API endpoint to get user's borrowing history"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    status = request.args.get('status', '')
    
    query = current_user.borrowing_transactions
    
    if status:
        query = query.filter_by(status=status)
    
    transactions = query.order_by(
        db.desc(BorrowingTransaction.borrowed_date)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'pagination': {
            'page': transactions.page,
            'pages': transactions.pages,
            'per_page': transactions.per_page,
            'total': transactions.total
        }
    })

@api_bp.route('/user/statistics')
@login_required
def get_user_statistics():
    """API endpoint to get user reading statistics"""
    stats = current_user.get_reading_statistics()
    return jsonify(stats)

@api_bp.route('/offline/verify', methods=['POST'])
def verify_offline_token():
    """API endpoint to verify offline access token"""
    data = request.get_json()
    token = data.get('token', '')
    
    if not token:
        return jsonify({'valid': False, 'error': 'Token required'}), 400
    
    # Hash the token
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Find the token
    offline_token = OfflineToken.query.filter_by(
        token_hash=token_hash,
        is_active=True
    ).first()
    
    if not offline_token:
        return jsonify({'valid': False, 'error': 'Invalid token'}), 404
    
    if not offline_token.is_valid():
        return jsonify({'valid': False, 'error': 'Token expired'}), 410
    
    # Update last sync
    offline_token.update_sync()
    
    # Get accessible books
    book_ids = offline_token.get_resources()
    books = Book.query.filter(
        Book.id.in_(book_ids),
        Book.is_active == True,
        Book.is_digital == True
    ).all()
    
    return jsonify({
        'valid': True,
        'user_id': offline_token.user_id,
        'expires_at': offline_token.expiry_date.isoformat(),
        'books': [book.to_dict(include_file_info=True) for book in books],
        'last_sync': offline_token.last_sync.isoformat() if offline_token.last_sync else None
    })

@api_bp.route('/offline/download/<int:book_id>')
def offline_download_book(book_id):
    """API endpoint for offline book download"""
    token = request.args.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    # Verify token
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    offline_token = OfflineToken.query.filter_by(
        token_hash=token_hash,
        is_active=True
    ).first()
    
    if not offline_token or not offline_token.is_valid():
        return jsonify({'error': 'Invalid or expired token'}), 403
    
    # Check if book is in accessible resources
    if book_id not in offline_token.get_resources():
        return jsonify({'error': 'Book not accessible with this token'}), 403
    
    book = Book.query.get_or_404(book_id)
    
    if not book.is_digital or not book.file_path:
        return jsonify({'error': 'Book not available for download'}), 404
    
    # Record download
    download_record = DigitalDownload(
        user_id=offline_token.user_id,
        book_id=book.id,
        ip_address=request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
        user_agent=request.headers.get('User-Agent'),
        file_size=book.file_size,
        offline_access_granted=True
    )
    
    try:
        db.session.add(download_record)
        book.increment_download_count()
        db.session.commit()
        
        # Return file information for client-side download
        return jsonify({
            'success': True,
            'book': book.to_dict(include_file_info=True),
            'download_url': url_for('books.download_book', book_id=book_id, token=token, _external=True)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Offline download error: {str(e)}')
        return jsonify({'error': 'Download failed'}), 500

@api_bp.route('/search/suggestions')
def search_suggestions():
    """API endpoint for search suggestions"""
    query = request.args.get('q', '').strip()
    limit = min(request.args.get('limit', 10, type=int), 20)
    
    if len(query) < 2:
        return jsonify([])
    
    # Get suggestions from titles and authors
    suggestions = []
    
    # Title suggestions
    titles = db.session.query(Book.title).filter(
        Book.title.ilike(f'%{query}%'),
        Book.is_active == True
    ).distinct().limit(limit // 2).all()
    
    for title in titles:
        suggestions.append({
            'text': title[0],
            'type': 'title'
        })
    
    # Author suggestions
    authors = db.session.query(Book.author).filter(
        Book.author.ilike(f'%{query}%'),
        Book.is_active == True
    ).distinct().limit(limit // 2).all()
    
    for author in authors:
        suggestions.append({
            'text': author[0],
            'type': 'author'
        })
    
    return jsonify(suggestions[:limit])

@api_bp.route('/stats/library')
def library_stats():
    """API endpoint for library statistics"""
    stats = {
        'total_books': Book.query.filter_by(is_active=True).count(),
        'digital_books': Book.query.filter_by(is_active=True, is_digital=True).count(),
        'physical_books': Book.query.filter_by(is_active=True, is_digital=False).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'active_borrowings': BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count(),
        'total_downloads': DigitalDownload.query.count(),
        'categories': Category.query.filter_by(is_active=True).count()
    }
    
    return jsonify(stats)

@api_bp.route('/health')
def health_check():
    """API health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'EduConnect Lesotho Digital Library API',
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'EduConnect Lesotho Digital Library API'
        }), 500

@api_bp.route('/books/<int:book_id>/reviews')
def get_book_reviews(book_id):
    """Get reviews for a specific book"""
    try:
        book = Book.query.get_or_404(book_id)
        reviews = BookReview.query.filter_by(
            book_id=book_id,
            is_approved=True
        ).order_by(BookReview.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'reviews': [review.to_dict() for review in reviews],
            'count': len(reviews)
        })
    except Exception as e:
        current_app.logger.error(f'Error loading reviews for book {book_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to load reviews'
        }), 500

@api_bp.route('/books/<int:book_id>/reviews', methods=['POST'])
@login_required
def add_book_review(book_id):
    """Add a review for a book"""
    try:
        book = Book.query.get_or_404(book_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        rating = data.get('rating')
        review_text = data.get('review_text', '').strip()
        
        # Validation
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({
                'success': False,
                'error': 'Rating must be between 1 and 5'
            }), 400
        
        # Check if user already reviewed this book
        existing_review = BookReview.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()
        
        if existing_review:
            # Update existing review
            existing_review.rating = rating
            existing_review.review_text = review_text
            existing_review.updated_at = datetime.utcnow()
            existing_review.is_approved = True  # Instantly visible
        else:
            # Create new review
            existing_review = BookReview(
                user_id=current_user.id,
                book_id=book_id,
                rating=rating,
                review_text=review_text,
                is_approved=True
            )
            db.session.add(existing_review)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Review submitted successfully and is pending approval',
            'review': existing_review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding review for book {book_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to add review'
        }), 500

@api_bp.route('/books/<int:book_id>/related')
def get_related_books(book_id):
    """Get related books based on category"""
    try:
        book = Book.query.get_or_404(book_id)
        
        # Get books in the same category, excluding the current book
        related_books = Book.query.filter(
            Book.category_id == book.category_id,
            Book.id != book_id,
            Book.is_active == True
        ).order_by(db.func.random()).limit(6).all()
        
        return jsonify({
            'success': True,
            'books': [{
                'id': b.id,
                'title': b.title,
                'author': b.author,
                'cover_image': b.cover_image
            } for b in related_books]
        })
        
    except Exception as e:
        current_app.logger.error(f'Error loading related books for book {book_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to load related books'
        }), 500

@api_bp.errorhandler(404)
def api_not_found(error):
    """API 404 error handler"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found.'
    }), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """API 500 error handler"""
    db.session.rollback()
    return jsonify({
        'error': 'Internal server error',
        'message': 'An internal error occurred. Please try again later.'
    }), 500

# Edit/update a review
@api_bp.route('/books/<int:book_id>/reviews/<int:review_id>', methods=['PUT'])
@login_required
def edit_book_review(book_id, review_id):
    """Edit/update a review for a book"""
    try:
        review = BookReview.query.filter_by(id=review_id, book_id=book_id, user_id=current_user.id).first_or_404()
        data = request.get_json()
        rating = data.get('rating')
        review_text = data.get('review_text', '').strip()
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
        review.rating = rating
        review.review_text = review_text
        review.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review updated successfully', 'review': review.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error editing review {review_id} for book {book_id}: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to edit review'}), 500


# Delete a review
@api_bp.route('/books/<int:book_id>/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def delete_book_review(book_id, review_id):
    """Delete a review for a book"""
    try:
        review = BookReview.query.filter_by(id=review_id, book_id=book_id, user_id=current_user.id).first_or_404()
        db.session.delete(review)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting review {review_id} for book {book_id}: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to delete review'}), 500

# Toggle favorite status for a book
@api_bp.route('/books/<int:book_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite_book(book_id):
    """Add or remove a book from user's favorites"""
    try:
        user = current_user
        book = Book.query.get_or_404(book_id)
        # Assume User model has a favorites relationship (many-to-many)
        if hasattr(user, 'favorites'):
            if book in user.favorites:
                user.favorites.remove(book)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Book removed from favorites.'})
            else:
                user.favorites.append(book)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Book added to favorites.'})
        else:
            return jsonify({'success': False, 'message': 'Favorites feature not available for this user.'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error toggling favorite for book {book_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'Error updating favorites.'}), 500