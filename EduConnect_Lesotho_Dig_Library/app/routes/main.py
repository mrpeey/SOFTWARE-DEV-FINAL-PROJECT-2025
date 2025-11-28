from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.user import User
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta

main_bp = Blueprint('main', __name__)

# ...existing code...

@main_bp.route('/book/', endpoint='book_list')
@login_required
def book_list():
    # Get all active books for the current user (customize as needed) 
    books = Book.query.filter_by(is_active=True).order_by(Book.title).all()
    return render_template('books/my_books.html', books=books)

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.user import User
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/book/<int:book_id>/review/<int:review_id>/edit', methods=['POST'])
@login_required
def edit_review(book_id, review_id):
    review = BookReview.query.get_or_404(review_id) 
    if review.user_id != current_user.id:
        flash('You can only edit your own review.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    review_text = request.form.get('review_text', '').strip()
    rating = request.form.get('rating', type=int)
    if not review_text or not rating or rating < 1 or rating > 5:
        flash('Please provide a valid review and rating (1-5).', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    review.review_text = review_text
    review.rating = rating
    review.updated_at = datetime.utcnow()
    review.is_approved = True
    try:
        db.session.commit()
        flash('Your review has been updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating review.', 'error')
        current_app.logger.error(f'Review edit error: {str(e)}')
    return redirect(url_for('main.book_detail', book_id=book_id))

@main_bp.route('/book/<int:book_id>/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(book_id, review_id):
    review = BookReview.query.get_or_404(review_id) 
    if review.user_id != current_user.id:
        flash('You can only delete your own review.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    try:
        db.session.delete(review)
        db.session.commit()
        flash('Your review has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting review.', 'error')
        current_app.logger.error(f'Review delete error: {str(e)}')
    return redirect(url_for('main.book_detail', book_id=book_id))

@main_bp.route('/')
def index():
    """Homepage with featured books and recent additions"""
    import random 
    # Get featured books
    featured_books = Book.query.filter_by(
        is_featured=True, 
        is_active=True
    ).limit(3).all()
    # Get recent additions
    recent_books = Book.query.filter_by(
        is_active=True 
    ).order_by(db.desc(Book.created_at)).limit(8).all()
    # Get popular books
    popular_books = Book.query.filter_by(
        is_active=True
    ).order_by(db.desc(Book.view_count + Book.download_count)).limit(6).all()
    # Assign SVG placeholders
    svg_placeholders = [
        'uploads/books/cover_placeholder1.svg',
        'uploads/books/cover_placeholder2.svg',
        'uploads/books/cover_placeholder3.svg'
    ]
    for book_list in [featured_books, recent_books, popular_books]:
        for book in book_list:
            if not book.cover_image:
                book.svg_placeholder = random.choice(svg_placeholders)
            else:
                book.svg_placeholder = None
    # Get categories with book counts
    categories = db.session.query(
        Category.id,
        Category.name,
        db.func.count(Book.id).label('book_count')
    ).join(Book).filter(
        Category.is_active == True,
        Book.is_active == True
    ).group_by(Category.id).all()
    # Get library statistics
    stats = {
        'total_books': Book.query.filter_by(is_active=True).count(),
        'digital_books': Book.query.filter_by(is_active=True, is_digital=True).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'active_borrowings': BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count()
    }
    return render_template('main/index.html',
                         featured_books=featured_books,
                         recent_books=recent_books,
                         popular_books=popular_books,
                         categories=categories,
                         stats=stats)

@main_bp.route('/search')
@login_required
def search():
    """Search books and resources"""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    is_digital = request.args.get('digital')
    language = request.args.get('language', '').strip()
    sort_by = request.args.get('sort', 'relevance')
    page = request.args.get('page', 1, type=int)
    
    # Convert digital filter
    if is_digital == 'true':
        is_digital = True
    elif is_digital == 'false':
        is_digital = False
    else:
        is_digital = None
    
    # Build query
    books_query = Book.query.filter_by(is_active=True)
    
    # Apply filters
    if query:
        search_filter = db.or_(
            Book.title.ilike(f'%{query}%'),
            Book.author.ilike(f'%{query}%'),
            Book.description.ilike(f'%{query}%')
        )
        books_query = books_query.filter(search_filter)
    
    if category_id:
        books_query = books_query.filter_by(category_id=category_id)
    
    if is_digital is not None:
        books_query = books_query.filter_by(is_digital=is_digital)
    
    if language:
        books_query = books_query.filter_by(language=language)
    
    # Apply sorting
    if sort_by == 'title':
        books_query = books_query.order_by(Book.title)
    elif sort_by == 'author':
        books_query = books_query.order_by(Book.author)
    elif sort_by == 'date_added':
        books_query = books_query.order_by(db.desc(Book.created_at))
    elif sort_by == 'popularity':
        books_query = books_query.order_by(
            db.desc(Book.view_count + Book.download_count)
        )
    elif sort_by == 'rating':
        # Complex query for average rating
        books_query = books_query.outerjoin(BookReview).group_by(Book.id).order_by(
            db.desc(db.func.avg(BookReview.rating))
        )
    else:  # relevance (default)
        if query:
            # Simple relevance scoring
            books_query = books_query.order_by(
                db.case(
                    (Book.title.ilike(f'%{query}%'), 3),
                    else_=1
                ).desc(),
                Book.view_count.desc()
            )
        else:
            books_query = books_query.order_by(db.desc(Book.created_at))
    
    # Paginate results
    per_page = current_app.config.get('BOOKS_PER_PAGE', 12)
    pagination = books_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    books = pagination.items
    
    # Get categories for filter dropdown
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    # Get available languages
    languages = db.session.query(Book.language).filter_by(is_active=True).distinct().all()
    languages = [lang[0] for lang in languages if lang[0]]
    
    return render_template('main/search.html',
                         books=books,
                         pagination=pagination,
                         categories=categories,
                         languages=languages,
                         query=query,
                         category_id=category_id,
                         is_digital=is_digital,
                         language=language,
                         sort_by=sort_by)

@main_bp.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    # Removed is_active check to allow viewing inactive books

    # Increment view count
    book.increment_view_count()

    # Get approved reviews
    reviews = book.book_reviews.filter_by(is_approved=True).order_by(
        db.desc(BookReview.created_at)
    ).all()

    # Check if current user can borrow
    can_borrow = False
    borrow_message = ""
    user_review = None

    if current_user.is_authenticated:
        can_borrow, borrow_message = book.can_be_borrowed_by(current_user)
        # Check if user has already reviewed this book
        user_review = BookReview.query.filter_by(
            user_id=current_user.id,
            book_id=book.id
        ).first()

    # Get similar books (same category, excluding current book)
    similar_books = Book.query.filter(
        Book.category_id == book.category_id,
        Book.id != book.id,
        Book.is_active == True
    ).order_by(db.func.random()).limit(6).all()

    return render_template('main/book_detail.html',
                         book=book,
                         reviews=reviews,
                         can_borrow=can_borrow,
                         borrow_message=borrow_message,
                         user_review=user_review,
                         similar_books=similar_books)

@main_bp.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def submit_review(book_id):
    book = Book.query.get_or_404(book_id)
    review_text = request.form.get('review_text', '').strip()
    rating = request.form.get('rating', type=int)

    # Validate input
    if not review_text or not rating or rating < 1 or rating > 5:
        flash('Please provide a valid review and rating (1-5).', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))

    existing_review = BookReview.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing_review:
        # Update existing review
        existing_review.review_text = review_text
        existing_review.rating = rating
        existing_review.updated_at = datetime.utcnow()
        existing_review.is_approved = True
        try:
            db.session.commit()
            flash('Your review has been updated and is now visible.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your review.', 'error')
            current_app.logger.error(f'Review update error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))
    else:
        # Create new review
        new_review = BookReview(
            user_id=current_user.id,
            book_id=book_id,
            review_text=review_text,
            rating=rating,
            is_approved=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        try:
            db.session.add(new_review)
            db.session.commit()
            flash('Your review has been submitted and is now visible.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting your review.', 'error')
            current_app.logger.error(f'Review submission error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))

@main_bp.route('/categories')
@login_required
def categories():
    """List all categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    
    return render_template('main/categories.html', categories=categories)

@main_bp.route('/category/<int:category_id>')
@login_required
def category_books(category_id):
    import random
    """Books in a specific category"""
    category = Category.query.get_or_404(category_id)
    
    if not category.is_active:
        flash('This category is not available.', 'error')
        return redirect(url_for('main.categories'))
    
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'title')
    
    # Build query
    books_query = category.books.filter_by(is_active=True)
    
    # Apply sorting
    if sort_by == 'title':
        books_query = books_query.order_by(Book.title)
    elif sort_by == 'author':
        books_query = books_query.order_by(Book.author)
    elif sort_by == 'date_added':
        books_query = books_query.order_by(db.desc(Book.created_at))
    elif sort_by == 'popularity':
        books_query = books_query.order_by(
            db.desc(Book.view_count + Book.download_count)
        )
    else:
        books_query = books_query.order_by(Book.title)
    
    # Paginate
    per_page = current_app.config.get('BOOKS_PER_PAGE', 12)
    pagination = books_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    books = pagination.items
    svg_placeholders = [
        'uploads/books/cover_placeholder1.svg',
        'uploads/books/cover_placeholder2.svg',
        'uploads/books/cover_placeholder3.svg'
    ]
    for book in books:
        if not book.cover_image:
            book.svg_placeholder = random.choice(svg_placeholders)
        else:
            book.svg_placeholder = None
    
    return render_template('main/category_books.html',
                         category=category,
                         books=books,
                         pagination=pagination,
                         sort_by=sort_by)

@main_bp.route('/about')
@login_required
def about():
    """About page"""
    return render_template('main/about.html')

@main_bp.route('/contact')
@login_required
def contact():
    """Contact page"""
    return render_template('main/contact.html')

@main_bp.route('/digital-literacy')
@login_required
def digital_literacy():
    """Digital literacy resources"""
    # Get digital literacy books/resources
    literacy_books = Book.query.filter(
        Book.is_active == True,
        Book.category.has(Category.name.ilike('%digital%literacy%'))
    ).order_by(Book.created_at.desc()).all()

    # Select the most recently added book as recommended_book if available
    recommended_book = literacy_books[0] if literacy_books else None

    return render_template('main/digital_literacy.html', literacy_books=literacy_books, recommended_book=recommended_book)

@main_bp.route('/offline-access')
@login_required
def offline_access():
    """Offline access information and downloads"""
    if not current_user.can_access_digital_resources():
        flash('You cannot access digital resources due to overdue books or unpaid fines.', 'error')
        return redirect(url_for('main.index'))
    
    # Get user's current offline tokens
    from app.models.offline import OfflineToken
    current_tokens = current_user.offline_tokens.filter_by(is_active=True).all()
    
    # Get available digital books for offline access
    digital_books = Book.query.filter_by(
        is_digital=True,
        is_active=True
    ).order_by(Book.title).all()
    
    return render_template('main/offline_access.html',
                         current_tokens=current_tokens,
                         digital_books=digital_books)

@main_bp.route('/api/search-suggestions')
def search_suggestions():
    """API endpoint for search suggestions"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Get title and author suggestions
    titles = db.session.query(Book.title).filter(
        Book.title.ilike(f'%{query}%'),
        Book.is_active == True
    ).limit(5).all()
    
    authors = db.session.query(Book.author).filter(
        Book.author.ilike(f'%{query}%'),
        Book.is_active == True
    ).distinct().limit(5).all()
    
    suggestions = []
    
    # Add title suggestions
    for title in titles:
        suggestions.append({
            'text': title[0],
            'type': 'title'
        })
    
    # Add author suggestions
    for author in authors:
        suggestions.append({
            'text': author[0],
            'type': 'author'
        })
    
    return jsonify(suggestions[:10])

@main_bp.route('/locations')
@login_required
def locations():
    """Display library locations across all districts of Lesotho"""
    # Get library statistics
    stats = {
        'total_books': Book.query.filter_by(is_active=True).count(),
        'digital_books': Book.query.filter_by(is_active=True, is_digital=True).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'active_borrowings': BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count()
    }
    
    return render_template('main/locations.html', stats=stats, recommended_book=None)

@main_bp.route('/test-map')
def test_map():
    """Test page to verify map images load correctly"""
    return render_template('test_map.html')

@main_bp.route('/svg-debug')
def svg_debug():
    """Debug page for SVG rendering issues"""
    return render_template('svg_debug.html')

@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files (covers and books)"""
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    return send_from_directory(upload_folder, filename)

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'EduConnect Lesotho Digital Library'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'EduConnect Lesotho Digital Library'
        }), 500

@main_bp.route('/recommendations')
@login_required
def recommendations():
    user_id = current_user.id
    # Collaborative filtering: get books borrowed by similar users
    user_borrowed_books = set([bt.book_id for bt in BorrowingTransaction.query.filter_by(user_id=user_id).all()])
    similar_users = db.session.query(BorrowingTransaction.user_id).filter(BorrowingTransaction.book_id.in_(user_borrowed_books)).distinct()
    similar_books = db.session.query(BorrowingTransaction.book_id).filter(BorrowingTransaction.user_id.in_(similar_users)).distinct()
    # Content-based: get books in same categories as user's borrowed books
    borrowed_books = Book.query.filter(Book.id.in_(user_borrowed_books)).all()
    category_ids = set([b.category_id for b in borrowed_books])
    content_books = Book.query.filter(Book.category_id.in_(category_ids), Book.id.notin_(user_borrowed_books), Book.is_active==True).limit(10).all()
    # Combine and remove duplicates
    recommended_book_ids = set([b.book_id for b in similar_books]) | set([b.id for b in content_books])
    import random
    recommended_books = Book.query.filter(Book.id.in_(recommended_book_ids), Book.is_active==True).limit(12).all()
    svg_placeholders = [
        'uploads/books/cover_placeholder1.svg',
        'uploads/books/cover_placeholder2.svg',
        'uploads/books/cover_placeholder3.svg'
    ]
    for book in recommended_books:
        if not book.cover_image:
            book.svg_placeholder = random.choice(svg_placeholders)
        else:
            book.svg_placeholder = None
    return render_template('main/recommendations.html', books=recommended_books)

@main_bp.route('/summarize-search')
@login_required
def summarize_search_page():
    return render_template('main/summarize_search.html')
    

