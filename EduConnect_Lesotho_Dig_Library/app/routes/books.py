
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.reservation import BookReservation
from app.models.offline import DigitalDownload, ReadingSession
from app.models.user import UserRole
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta

books_bp = Blueprint('books', __name__)


from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.reservation import BookReservation
from app.models.offline import DigitalDownload, ReadingSession
from app.models.user import UserRole
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta

books_bp = Blueprint('books', __name__)

@books_bp.route('/api/review/<int:book_id>', methods=['POST'])
@login_required
def api_create_review(book_id):
    rating = request.json.get('rating', type=int)
    content = request.json.get('content', '').strip()
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400
    if not content or len(content) < 10:
        return jsonify({'success': False, 'message': 'Review too short'}), 400
    review = BookReview(
        user_id=current_user.id,
        book_id=book_id,
        rating=rating,
        review_text=content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_approved=False
    )
    try:
        db.session.add(review)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review submitted', 'review_id': review.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.reservation import BookReservation
from app.models.offline import DigitalDownload, ReadingSession
from app.models.user import UserRole
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta

books_bp = Blueprint('books', __name__)

@books_bp.route('/api/review/<int:book_id>/<int:review_id>', methods=['PUT'])
@login_required
def api_edit_review(book_id, review_id):
    review = BookReview.query.filter_by(id=review_id, user_id=current_user.id, book_id=book_id).first_or_404()
    rating = request.json.get('rating', type=int)
    content = request.json.get('content', '').strip()
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400
    if not content or len(content) < 10:
        return jsonify({'success': False, 'message': 'Review too short'}), 400
    review.rating = rating
    review.review_text = content
    review.updated_at = datetime.utcnow()
    review.is_approved = False
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@books_bp.route('/api/review/<int:book_id>/<int:review_id>', methods=['DELETE'])
@login_required
def api_delete_review(book_id, review_id):
    review = BookReview.query.filter_by(id=review_id, user_id=current_user.id, book_id=book_id).first_or_404()
    try:
        db.session.delete(review)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@books_bp.route('/borrow/confirm/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow_confirm(book_id):
    """Borrow confirmation page with subscription check and admin exemption. Applies borrowing logic directly."""
    book = Book.query.get_or_404(book_id)
    is_admin = current_user.is_admin() if hasattr(current_user, 'is_admin') else False
    can_borrow, borrow_msg = book.can_be_borrowed_by(current_user)
    # Collect detailed error reasons
    error_details = []
    if not book.is_active:
        error_details.append('Book is not active.')
    if not book.is_available():
        error_details.append('Book is not available for borrowing.')
    if hasattr(current_user, 'has_overdue_books') and current_user.has_overdue_books():
        error_details.append('You have overdue books. Please return them first.')
    if hasattr(current_user, 'get_total_fines') and current_user.get_total_fines() > 0:
        error_details.append(f'You have unpaid fines: LSL {current_user.get_total_fines():.2f}')
    if hasattr(current_user, 'can_borrow_more') and not current_user.can_borrow_more():
        error_details.append('You have reached your borrowing limit.')
    if hasattr(current_user, 'has_active_subscription') and not current_user.has_active_subscription() and not current_user.is_admin():
        error_details.append('You do not have an active subscription.')
    if request.method == 'POST':
        current_app.logger.info(f"POST received on borrow_confirm for book_id={book_id}, user_id={current_user.id}")
        if can_borrow:
            current_app.logger.info(f"User {current_user.id} is eligible to borrow book {book_id}")
            if not book.is_available():
                current_app.logger.warning(f"Book {book_id} is not available for borrowing.")
                flash('This book is not available for borrowing.', 'error')
                return redirect(url_for('main.book_detail', book_id=book.id))
            librarian = UserRole.query.filter_by(role_name='librarian').first()
            if not librarian:
                current_app.logger.warning("No librarian available to process the borrowing request.")
                flash('No librarian available to process the borrowing request.', 'error')
                return redirect(url_for('main.book_detail', book_id=book.id))
            borrowing_days = current_app.config.get('DEFAULT_BORROWING_DAYS', 14)
            due_date = date.today() + timedelta(days=borrowing_days)
            transaction = BorrowingTransaction(
                user_id=current_user.id,
                book_id=book.id,
                due_date=due_date,
                librarian_id=librarian.id,
                status='pending'
            )
            try:
                db.session.add(transaction)
                db.session.commit()
                current_app.logger.info(f"Borrowing transaction created for user {current_user.id}, book {book_id}")
                flash(f'You have successfully borrowed "{book.title}". Due date: {due_date.strftime("%Y-%m-%d")}', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Borrowing error: {str(e)}')
                flash('An error occurred while borrowing the book. Please try again.', 'error')
            return redirect(url_for('main.book_detail', book_id=book.id))
        else:
            current_app.logger.info(f"User {current_user.id} is NOT eligible to borrow book {book_id}: {borrow_msg}")
            detailed_message = borrow_msg or 'You are not eligible to borrow this book.'
            if error_details:
                detailed_message += ' Reasons: ' + '; '.join(error_details)
            flash(detailed_message, 'error')
            return redirect(url_for('books.borrow_confirm', book_id=book.id))
    return render_template('books/borrow_confirm.html', book=book, can_borrow=can_borrow, is_admin=is_admin)
# Temporary debug route to check cover_image for book ID 5
@books_bp.route('/debug_cover/5')
@login_required
def debug_cover():
    book = Book.query.get_or_404(5)
    return f"cover_image for book 5: {book.cover_image}"

def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'epub', 'txt'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@books_bp.route('/my_book/<int:book_id>')
@login_required
def my_book(book_id):
    """Display book details and reviews in a professional card layout"""
    book = Book.query.get_or_404(book_id)
    from sqlalchemy.orm import joinedload
    reviews = BookReview.query.options(joinedload(BookReview.user)).filter_by(book_id=book_id, is_approved=True).order_by(BookReview.created_at.desc()).all()
    can_borrow, borrow_msg = book.can_be_borrowed_by(current_user)
    can_download, download_msg = book.can_be_downloaded_by(current_user)
    svg_content = None
    if book.cover_image and book.cover_image.endswith('.svg'):
        svg_path = os.path.join(current_app.static_folder, book.cover_image)
        if os.path.exists(svg_path):
            with open(svg_path, 'r', encoding='utf-8') as svg_file:
                svg_content = svg_file.read()
    return render_template('books/my_book.html',
                          book=book,
                          reviews=reviews,
                          can_borrow=can_borrow,
                          borrow_msg=borrow_msg,
                          can_download=can_download,
                          download_msg=download_msg,
                          svg_content=svg_content)
@books_bp.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    """Borrow a book"""
    book = Book.query.get_or_404(book_id)
    if not book.is_available():
        flash('This book is not available for borrowing.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    # Find a librarian (example logic, adjust as needed)
    librarian = UserRole.query.filter_by(role='librarian').first()
    if not librarian:
        flash('No librarian available to process the borrowing request.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    borrowing_days = current_app.config.get('DEFAULT_BORROWING_DAYS', 14)
    due_date = date.today() + timedelta(days=borrowing_days)
    transaction = BorrowingTransaction(
        user_id=current_user.id,
        book_id=book.id,
        due_date=due_date,
        librarian_id=librarian.id,
        status='pending'
    )
    # Do NOT decrement available_copies until approved by admin
    try:
        db.session.add(transaction)
        db.session.commit()
        flash(f'You have successfully borrowed "{book.title}". Due date: {due_date.strftime("%Y-%m-%d")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while borrowing the book. Please try again.', 'error')
        current_app.logger.error(f'Borrowing error: {str(e)}')
    return redirect(url_for('main.book_detail', book_id=book_id))

# ...existing code...

# ...existing code...


# Edit review route
@books_bp.route('/review/<int:book_id>/edit/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(book_id, review_id):
    review = BookReview.query.filter_by(id=review_id, book_id=book_id).first_or_404()
    book = Book.query.get_or_404(book_id)
    from app.forms import CSRFOnlyForm
    form = CSRFOnlyForm()
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin()
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        reading_status = request.form.get('reading_status', '').strip()
        tags = request.form.get('tags', '').strip()
        is_anonymous = bool(request.form.get('is_anonymous'))
        # Admin approval logic
        if is_admin and 'approve_review' in request.form:
            review.is_approved = True
            db.session.commit()
            flash('Review approved by admin.', 'success')
            return redirect(url_for('main.book_detail', book_id=book_id))
        if not rating or rating < 1 or rating > 5:
            flash('Please provide a rating between 1 and 5 stars.', 'error')
            return render_template('books/review.html', book=book, existing_review=review)
        if not content or len(content) < 10:
            flash('Your review should be at least 10 characters long.', 'error')
            return render_template('books/review.html', book=book, existing_review=review)
        review.rating = rating
        review.title = title
        review.content = content
        review.reading_status = reading_status
        review.tags = tags
        review.is_anonymous = is_anonymous
        review.updated_at = datetime.utcnow()
        review.is_approved = False
        try:
            db.session.commit()
            flash('Your review has been updated and is pending approval.', 'success')
            return redirect(url_for('main.book_detail', book_id=book_id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your review.', 'error')
            current_app.logger.error(f'Review update error: {str(e)}')
    return render_template('books/review.html', book=book, existing_review=review, form=form, is_admin=is_admin)

# Delete review route (with review_id)
@books_bp.route('/review/<int:book_id>/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(book_id, review_id):
    review = BookReview.query.filter_by(id=review_id, book_id=book_id, user_id=current_user.id).first()
    if not review:
        flash('Review not found.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    try:
        db.session.delete(review)
        db.session.commit()
        flash('Your review has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting your review.', 'error')
        current_app.logger.error(f'Review delete error: {str(e)}')
    return redirect(url_for('main.book_detail', book_id=book_id))
    
    if not librarian:
        flash('No librarian available to process the borrowing request.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Calculate due date
    borrowing_days = current_app.config.get('DEFAULT_BORROWING_DAYS', 14)
    due_date = date.today() + timedelta(days=borrowing_days)
    
    transaction = BorrowingTransaction(
        user_id=current_user.id,
        book_id=book.id,
        due_date=due_date,
        librarian_id=librarian.id
    )
    
    # Update book availability for physical books
    if not book.is_digital:
        book.available_copies -= 1
    
    try:
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'You have successfully borrowed "{book.title}". Due date: {due_date.strftime("%Y-%m-%d")}', 'success')
        return redirect(url_for('main.book_detail', book_id=book_id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while borrowing the book. Please try again.', 'error')
        current_app.logger.error(f'Borrowing error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))

@books_bp.route('/return/<int:transaction_id>', methods=['POST'])
@login_required
def return_book(transaction_id):
    """Return a borrowed book"""
    transaction = BorrowingTransaction.query.get_or_404(transaction_id)
    
    # Check if user owns this transaction or is a librarian
    if transaction.user_id != current_user.id and not current_user.is_librarian():
        flash('You are not authorized to return this book.', 'error')
        return redirect(url_for('auth.profile'))
    
    # Check if book is already returned
    if transaction.status == 'returned':
        flash('This book has already been returned.', 'error')
        return redirect(url_for('auth.profile'))
    
    librarian_id = current_user.id if current_user.is_librarian() else transaction.librarian_id
    notes = request.form.get('notes', '').strip()
    
    success, message = transaction.return_book(librarian_id, notes)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('auth.profile'))

@books_bp.route('/renew/<int:transaction_id>', methods=['POST'])
@login_required
def renew_book(transaction_id):
    """Renew a borrowed book"""
    transaction = BorrowingTransaction.query.get_or_404(transaction_id)
    
    # Check if user owns this transaction
    if transaction.user_id != current_user.id:
        flash('You are not authorized to renew this book.', 'error')
        return redirect(url_for('auth.profile'))
    
    librarian_id = current_user.id if current_user.is_librarian() else transaction.librarian_id
    success, message = transaction.renew(librarian_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('auth.profile'))

@books_bp.route('/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    """Reserve a book when not available"""
    book = Book.query.get_or_404(book_id)
    
    if book.is_available():
        flash('This book is currently available. You can borrow it directly.', 'info')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Check if user already has a reservation for this book
    existing_reservation = BookReservation.query.filter_by(
        user_id=current_user.id,
        book_id=book_id,
        status='active'
    ).first()
    
    if existing_reservation:
        flash('You already have an active reservation for this book.', 'info')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Create reservation
    reservation = BookReservation(
        user_id=current_user.id,
        book_id=book_id
    )
    
    try:
        db.session.add(reservation)
        db.session.commit()
        
        flash(f'You have successfully reserved "{book.title}". You will be notified when it becomes available.', 'success')
        return redirect(url_for('main.book_detail', book_id=book_id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while reserving the book. Please try again.', 'error')
        current_app.logger.error(f'Reservation error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))

@books_bp.route('/download/<int:book_id>')
@login_required
def download_book(book_id):
    """Download a digital book"""
    book = Book.query.get_or_404(book_id)
    
    # Check if user can download this book
    can_download, message = book.can_be_downloaded_by(current_user)
    
    if not can_download:
        flash(message, 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    if not book.file_path:
        flash('Book file not available for download.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Check if file exists - try both static uploads and root uploads
    file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'books', book.file_path)
    if not os.path.exists(file_path):
        # Try old location as fallback
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', book.file_path)
        if not os.path.exists(file_path):
            flash('Book file not found. Please contact the library administrator.', 'error')
            current_app.logger.error(f'Book file not found: {book.file_path}')
            return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Record download
    download_record = DigitalDownload(
        user_id=current_user.id,
        book_id=book.id,
        ip_address=request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
        user_agent=request.headers.get('User-Agent'),
        file_size=book.file_size if hasattr(book, 'file_size') else 0
    )
    
    # Increment download count
    book.increment_download_count()
    
    try:
        db.session.add(download_record)
        db.session.commit()
        
        # Determine file extension from filename
        file_extension = book.file_path.split('.')[-1] if '.' in book.file_path else 'pdf'
        
        # Return file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"{book.title}.{file_extension}",
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while downloading the book. Please try again.', 'error')
        current_app.logger.error(f'Download error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))

@books_bp.route('/read/<int:book_id>')
@login_required
def read_book(book_id):
    """Start reading a digital book online"""
    book = Book.query.get_or_404(book_id)
    
    if not book.is_digital:
        flash('This book is not available for online reading.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    if not current_user.can_access_digital_resources():
        flash('You cannot read books due to overdue items or unpaid fines.', 'error')
        return redirect(url_for('main.book_detail', book_id=book_id))
    
    # Create reading session
    session = ReadingSession(
        user_id=current_user.id,
        book_id=book.id,
        device_type=request.headers.get('User-Agent', '')[:50],
        is_offline=False
    )
    
    try:
        db.session.add(session)
        db.session.commit()
        
        # Increment view count
        book.increment_view_count()
        
        return render_template('books/reader.html', book=book, session=session)
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while opening the book. Please try again.', 'error')
        current_app.logger.error(f'Reading session error: {str(e)}')
        return redirect(url_for('main.book_detail', book_id=book_id))

@books_bp.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def review_book(book_id):
    """Add or edit a book review"""

    from app.forms import CSRFOnlyForm
    book = Book.query.get_or_404(book_id)
    # Check if user has already reviewed this book
    existing_review = BookReview.query.filter_by(
        user_id=current_user.id,
        book_id=book_id
    ).first()
    form = CSRFOnlyForm()

    if request.method == 'POST':
        current_app.logger.info('POST request received for review_book')
        rating = request.form.get('rating', type=int)
        content = request.form.get('content', '').strip()
        current_app.logger.info(f'Form data: rating={rating}, content={content}')

        # Validation
        if not rating or rating < 1 or rating > 5:
            flash('Please provide a rating between 1 and 5 stars.', 'error')
            current_app.logger.warning('Rating validation failed')
            return render_template('books/review.html', book=book, existing_review=existing_review, form=form)
        if not content or len(content) < 10:
            flash('Your review should be at least 10 characters long.', 'error')
            current_app.logger.warning('Content validation failed')
            return render_template('books/review.html', book=book, existing_review=existing_review, form=form)

        if existing_review:
            # Update existing review
            current_app.logger.info('Updating existing review')
            existing_review.rating = rating
            existing_review.review_text = content
            existing_review.updated_at = datetime.utcnow()
            existing_review.is_approved = False  # Re-approval needed after edit
            try:
                db.session.commit()
                flash('Your review has been updated and is pending approval.', 'success')
                current_app.logger.info('Review updated and committed')
                return redirect(url_for('main.book_detail', book_id=book_id))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating your review.', 'error')
                current_app.logger.error(f'Review update error: {str(e)}')
        else:
            # Create new review
            current_app.logger.info('Creating new review')
            review = BookReview(
                user_id=current_user.id,
                book_id=book_id,
                rating=rating,
                review_text=content,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_approved=False
            )
            try:
                db.session.add(review)
                db.session.commit()
                flash('Your review has been submitted and is pending approval.', 'success')
                current_app.logger.info('Review created and committed')
                return redirect(url_for('main.book_detail', book_id=book_id))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while submitting your review.', 'error')
                current_app.logger.error(f'Review submission error: {str(e)}')

    return render_template('books/review.html', book=book, existing_review=existing_review, form=form)

@books_bp.route('/my-books')
@login_required
def my_books():
    """User's borrowed and downloaded books"""
    # Current borrowings
    current_borrowings = current_user.get_current_borrowings()
    
    # Borrowing history
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('TRANSACTIONS_PER_PAGE', 25)
    
    borrowing_history = current_user.borrowing_transactions.order_by(
        db.desc(BorrowingTransaction.borrowed_date)
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Recent downloads
    recent_downloads = current_user.digital_downloads.order_by(
        db.desc(DigitalDownload.download_date)
    ).limit(10).all()
    
    # Active reservations
    active_reservations = current_user.book_reservations.filter_by(
        status='active'
    ).order_by(BookReservation.reserved_date).all()
    
    # Get books the user is subscribed for
    current_subscription = current_user.get_current_subscription()
    subscribed_books = []
    if current_subscription and not current_subscription.is_expired:
        plan = current_subscription.plan
        subscribed_books = Book.query.filter(Book.is_active==True).limit(plan.max_books).all()

    # Compute books by category for pie chart
    books_by_category = {}
    for book in subscribed_books:
        cat_name = book.category.name if book.category else 'Uncategorized'
        books_by_category[cat_name] = books_by_category.get(cat_name, 0) + 1

    return render_template('books/my_books.html',
                         subscribed_books=subscribed_books,
                         current_borrowings=current_borrowings,
                         borrowing_history=borrowing_history,
                         recent_downloads=recent_downloads,
                         active_reservations=active_reservations,
                         books_by_category=books_by_category)

@books_bp.route('/reading-session/<int:session_id>/end', methods=['POST'])
@login_required
def end_reading_session(session_id):
    """End a reading session"""
    session = ReadingSession.query.get_or_404(session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    pages_read = request.json.get('pages_read', 0)
    progress = request.json.get('progress', 0.0)
    
    session.end_session(pages_read=pages_read, progress=progress)
    
    return jsonify({
        'success': True,
        'duration_minutes': session.get_duration_minutes()
    })

@books_bp.route('/api/book-suggestions')
def book_suggestions():
    """API endpoint for book suggestions based on user's reading history"""
    if not current_user.is_authenticated:
        return jsonify([])
    
    # Get user's reading categories
    user_categories = db.session.query(Category.id).join(
        Book, Category.id == Book.category_id
    ).join(
        BorrowingTransaction, Book.id == BorrowingTransaction.book_id
    ).filter(
        BorrowingTransaction.user_id == current_user.id
    ).group_by(Category.id).all()
    
    category_ids = [cat[0] for cat in user_categories]
    
    if not category_ids:
        # If no history, suggest popular books
        suggestions = Book.query.filter_by(is_active=True).order_by(
            db.desc(Book.view_count + Book.download_count)
        ).limit(6).all()
    else:
        # Suggest books from user's preferred categories
        suggestions = Book.query.filter(
            Book.category_id.in_(category_ids),
            Book.is_active == True
        ).order_by(db.func.random()).limit(6).all()
    
    return jsonify([book.to_dict() for book in suggestions])

@books_bp.route('/offline-access/generate', methods=['POST'])
@login_required
def generate_offline_access():
    """Generate offline access token"""
    if not current_user.can_access_digital_resources():
        return jsonify({'success': False, 'message': 'Cannot access digital resources'}), 403
    
    selected_books = request.json.get('book_ids', [])
    days = request.json.get('days', 30)
    
    if not selected_books:
        return jsonify({'success': False, 'message': 'No books selected'}), 400
    
    # Validate book IDs
    books = Book.query.filter(
        Book.id.in_(selected_books),
        Book.is_digital == True,
        Book.is_active == True
    ).all()
    
    if len(books) != len(selected_books):
        return jsonify({'success': False, 'message': 'Some books are not available'}), 400
    
    try:
        token = current_user.generate_offline_token(
            resources=selected_books,
            days=days
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_in_days': days,
            'book_count': len(selected_books)
        })
        
    except Exception as e:
        current_app.logger.error(f'Offline token generation error: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to generate token'}), 500