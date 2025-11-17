from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
admin_bp = Blueprint('admin', __name__)
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from app import db
from app.models.user import User, UserRole
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.reservation import BookReservation
from app.models.offline import DigitalDownload, ReadingSession
from app.models.subscription import SubscriptionPlan, UserSubscription, BillingRecord, Payment
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def librarian_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_librarian():
            flash('You need librarian privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/borrowings/<int:borrowing_id>/approve', methods=['POST'])
@librarian_required
def approve_borrowing(borrowing_id):
    borrowing = BorrowingTransaction.query.get_or_404(borrowing_id)
    if borrowing.status != 'pending':
        flash('Borrowing request is not pending.', 'error')
        return redirect(url_for('admin.pending_borrowings'))
    borrowing.status = 'borrowed'
    db.session.commit()
    flash('Borrowing request approved.', 'success')
    return redirect(url_for('admin.pending_borrowings'))

@admin_bp.route('/borrowings/<int:borrowing_id>/reject', methods=['POST'])
@librarian_required
def reject_borrowing(borrowing_id):
    borrowing = BorrowingTransaction.query.get_or_404(borrowing_id)
    if borrowing.status != 'pending':
        flash('Borrowing request is not pending.', 'error')
        return redirect(url_for('admin.pending_borrowings'))
    borrowing.status = 'rejected'
    db.session.commit()
    flash('Borrowing request rejected.', 'success')
    return redirect(url_for('admin.pending_borrowings'))

@admin_bp.route('/borrowings/pending')
@librarian_required
def pending_borrowings():
    """View and manage pending borrow requests"""
    pending = BorrowingTransaction.query.filter_by(status='pending').order_by(BorrowingTransaction.created_at.desc()).all()
    return render_template('admin/pending_borrowings.html', borrowings=pending)
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app

admin_bp = Blueprint('admin', __name__)
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from app import db
from app.models.user import User, UserRole
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.reservation import BookReservation
from app.models.offline import DigitalDownload, ReadingSession
from app.models.subscription import SubscriptionPlan, UserSubscription, BillingRecord, Payment
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def librarian_required(f):
    """Decorator to require librarian or admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_librarian() or current_user.is_admin()):
            flash('You need librarian or administrator privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@librarian_required
def dashboard():
    """Admin/Librarian dashboard"""
    # Get statistics
    stats = {
        'total_books': Book.query.filter_by(is_active=True).count(),
        'digital_books': Book.query.filter_by(is_active=True, is_digital=True).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'active_borrowings': BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count(),
        'overdue_books': BorrowingTransaction.query.filter_by(status='overdue').count(),
        'pending_reservations': BookReservation.query.filter_by(status='active').count(),
        'pending_reviews': BookReview.query.filter_by(is_approved=False).count(),
        'total_downloads': DigitalDownload.query.count()
    }
    
    # Recent activity aggregation
    recent_activity = []

    # Recent books
    for book in Book.query.order_by(Book.created_at.desc()).limit(5).all():
        recent_activity.append({
            'type': 'book',
            'type_class': 'primary',
            'description': f"Book added: {book.title}",
            'details': f"By {book.author}",
            'timestamp': book.created_at
        })

    # Recent users
    for user in User.query.order_by(User.created_at.desc()).limit(3).all():
        recent_activity.append({
            'type': 'user',
            'type_class': 'success',
            'description': f"User registered: {user.username}",
            'details': f"{user.first_name} {user.last_name}",
            'timestamp': user.created_at
        })

    # Recent borrowings
    for tx in BorrowingTransaction.query.order_by(BorrowingTransaction.borrowed_date.desc()).limit(5).all():
        recent_activity.append({
            'type': 'borrowing',
            'type_class': 'warning' if tx.status == 'borrowed' else 'danger' if tx.status == 'overdue' else 'info',
            'description': f"Borrowing: {tx.book.title}",
            'details': f"User: {tx.user_id}, Status: {tx.status}",
            'timestamp': tx.borrowed_date
        })

    # Recent reviews
    for review in BookReview.query.order_by(BookReview.created_at.desc()).limit(3).all():
        recent_activity.append({
            'type': 'review',
            'type_class': 'info',
            'description': f"Review {'approved' if review.is_approved else 'submitted'} for {review.book.title}",
            'details': f"By user {review.user_id}",
            'timestamp': review.created_at
        })

    # Sort by timestamp descending
    recent_activity = sorted(recent_activity, key=lambda x: x['timestamp'], reverse=True)[:10]

    # Existing dashboard data
    recent_borrowings = BorrowingTransaction.query.order_by(
        db.desc(BorrowingTransaction.borrowed_date)
    ).limit(10).all()

    recent_returns = BorrowingTransaction.query.filter_by(status='returned').order_by(
        db.desc(BorrowingTransaction.returned_date)
    ).limit(10).all()

    overdue_books = BorrowingTransaction.query.filter_by(status='overdue').order_by(
        BorrowingTransaction.due_date
    ).limit(10).all()

    last_month = datetime.utcnow() - timedelta(days=30)
    popular_books = db.session.query(
        Book.id, Book.title, Book.author,
        db.func.count(BorrowingTransaction.id).label('borrow_count')
    ).join(BorrowingTransaction).filter(
        BorrowingTransaction.borrowed_date >= last_month
    ).group_by(Book.id).order_by(
        db.desc('borrow_count')
    ).limit(10).all()

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    category_labels = [c.name for c in categories]
    category_data = [Book.query.filter_by(category_id=c.id, is_active=True).count() for c in categories]

    from calendar import month_name
    monthly_labels = [month_name[i] for i in range(1, 13)]
    monthly_borrowings = [0] * 12
    for i in range(1, 13):
        start = datetime(datetime.utcnow().year, i, 1)
        if i < 12:
            end = datetime(datetime.utcnow().year, i+1, 1)
        else:
            end = datetime(datetime.utcnow().year+1, 1, 1)
        monthly_borrowings[i-1] = BorrowingTransaction.query.filter(
            BorrowingTransaction.borrowed_date >= start,
            BorrowingTransaction.borrowed_date < end
        ).count()

    # Calculate peak month for borrowings (avoid Jinja2 'max' error)
    if monthly_borrowings:
        peak_idx = monthly_borrowings.index(max(monthly_borrowings))
        peak_month = monthly_labels[peak_idx]
    else:
        peak_month = 'N/A'

    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_activity=recent_activity,
                         recent_borrowings=recent_borrowings,
                         recent_returns=recent_returns,
                         overdue_books=overdue_books,
                         popular_books=popular_books,
                         category_labels=category_labels,
                         category_data=category_data,
                         monthly_labels=monthly_labels,
                         monthly_borrowings=monthly_borrowings,
                         peak_month=peak_month)

@admin_bp.route('/books')
@librarian_required
def manage_books():
    """Manage books"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category', type=int)
    is_digital = request.args.get('digital')
    
    query = Book.query
    
    if search:
        search_filter = db.or_(
            Book.title.ilike(f'%{search}%'),
            Book.author.ilike(f'%{search}%'),
            Book.isbn.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if is_digital == 'true':
        query = query.filter_by(is_digital=True)
    elif is_digital == 'false':
        query = query.filter_by(is_digital=False)
    
    pagination = query.order_by(Book.title).paginate(
        page=page, per_page=20, error_out=False
    )
    books = pagination.items
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    # Define a color palette
    palette = ["#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b", "#858796", "#5a5c69", "#fd7e14", "#20c997", "#6610f2"]
    # Map category id to a color (cycle if more categories than colors)
    cat_colors = {}
    for idx, cat in enumerate(categories):
        cat_colors[cat.id] = palette[idx % len(palette)]
    return render_template('admin/books.html',
                         books=books,
                         pagination=pagination,
                         categories=categories,
                         search=search,
                         category_id=category_id,
                         is_digital=is_digital,
                         cat_colors=cat_colors)

@admin_bp.route('/books/add', methods=['GET', 'POST'])
@librarian_required
def add_book():
    """Add a new book"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        publisher = request.form.get('publisher', '').strip()
        publication_year = request.form.get('publication_year', type=int)
        edition = request.form.get('edition', '').strip()
        pages = request.form.get('pages', type=int)
        language = request.form.get('language', 'English').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        is_digital = bool(request.form.get('is_digital'))
        total_copies = request.form.get('total_copies', 1, type=int)
        is_featured = bool(request.form.get('is_featured'))
        
        # Validation
        if not all([title, author, category_id]):
            flash('Title, author, and category are required.', 'error')
            return render_template('admin/add_book.html')
        
        # Check for duplicate ISBN
        if isbn:
            existing_book = Book.query.filter_by(isbn=isbn).first()
            if existing_book:
                flash('A book with this ISBN already exists.', 'error')
                return render_template('admin/add_book.html')
        
        # Handle file upload for digital books
        file_path = None
        file_size = None
        file_format = None
        
        if is_digital and 'book_file' in request.files:
            file = request.files['book_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join('books', filename)
                full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
                
                try:
                    file.save(full_path)
                    file_size = os.path.getsize(full_path)
                    file_format = filename.rsplit('.', 1)[1].upper()
                except Exception as e:
                    flash('Error uploading file. Please try again.', 'error')
                    current_app.logger.error(f'File upload error: {str(e)}')
                    return render_template('admin/add_book.html')
        
        # Handle cover image
        cover_image = None
        if 'cover_image' in request.files:
            cover_file = request.files['cover_image']
            if cover_file and cover_file.filename:
                cover_filename = secure_filename(cover_file.filename)
                cover_path = os.path.join('covers', cover_filename)
                cover_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cover_path)
                try:
                    cover_file.save(cover_full_path)
                    cover_image = cover_path
                except Exception as e:
                    flash('Error uploading cover image.', 'warning')
                    current_app.logger.error(f'Cover upload error: {str(e)}')
        # If no cover image uploaded, assign default SVG
        if not cover_image:
            cover_image = 'covers/default_cover.svg'  # Ensure this SVG exists in your static/uploads/covers folder
        
        # Create book
        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            publisher=publisher,
            publication_year=publication_year,
            edition=edition,
            pages=pages,
            language=language,
            description=description,
            category_id=category_id,
            is_digital=is_digital,
            file_path=file_path,
            file_size=file_size,
            file_format=file_format,
            cover_image=cover_image,
            total_copies=total_copies,
            available_copies=total_copies,
            is_featured=is_featured,
            created_by=current_user.id
        )
        
        try:
            db.session.add(book)
            db.session.commit()
            flash(f'Book "{title}" has been added successfully.', 'success')
            return redirect(url_for('admin.manage_books'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the book.', 'error')
            current_app.logger.error(f'Add book error: {str(e)}')
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return render_template('admin/add_book.html', categories=categories)

@admin_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@librarian_required
def edit_book(book_id):
    """Edit a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        errors = []
        # Validate required fields
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        category_id = request.form.get('category_id', type=int)
        total_copies = request.form.get('total_copies', 1, type=int)
        available_copies = request.form.get('available_copies', 1, type=int)
        if not title:
            errors.append('Title is required.')
        if not author:
            errors.append('Author is required.')
        if not isbn:
            errors.append('ISBN is required.')
        if not category_id:
            errors.append('Category is required.')
        if total_copies < 1:
            errors.append('Total copies must be at least 1.')
        if available_copies < 0:
            errors.append('Available copies cannot be negative.')
        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('admin/edit_book.html', book=book, categories=Category.query.filter_by(is_active=True).order_by(Category.name).all())

        # Update book details
        book.title = title
        book.author = author
        book.isbn = isbn
        book.publisher = request.form.get('publisher', '').strip()

        # Handle publication date
        pub_date_str = request.form.get('publication_date', '').strip()
        if pub_date_str:
            try:
                from datetime import datetime as dt
                book.publication_date = dt.strptime(pub_date_str, '%Y-%m-%d').date()
            except Exception as e:
                flash(f'Invalid publication date: {pub_date_str}', 'error')

        book.edition = request.form.get('edition', '').strip()
        book.pages = request.form.get('pages', type=int)
        book.language = request.form.get('language', 'English').strip()
        book.description = request.form.get('description', '').strip()
        book.category_id = category_id
        book.total_copies = total_copies
        book.available_copies = available_copies
        book.location = request.form.get('location', '').strip()
        book.tags = request.form.get('tags', '').strip()
        book.reading_level = request.form.get('reading_level', '').strip()
        book.is_digital = bool(request.form.get('is_digital'))
        book.download_url = request.form.get('download_url', '').strip()
        book.is_featured = bool(request.form.get('is_featured'))
        book.is_active = bool(request.form.get('is_active', True))
        book.updated_at = datetime.utcnow()

        # Handle cover image upload with validation
        try:
            if 'cover_image' in request.files:
                cover_file = request.files['cover_image']
                if cover_file and cover_file.filename:
                    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/webp'}
                    max_size = 5 * 1024 * 1024  # 5MB
                    if cover_file.mimetype not in allowed_types:
                        flash('Invalid image type. Allowed types: JPEG, PNG, GIF, SVG, WEBP.', 'error')
                    elif cover_file.content_length and cover_file.content_length > max_size:
                        flash('Image file is too large (max 5MB).', 'error')
                    else:
                        filename = secure_filename(cover_file.filename)
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + filename
                        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'covers')
                        os.makedirs(upload_path, exist_ok=True)
                        full_path = os.path.join(upload_path, filename)
                        cover_file.save(full_path)
                        book.cover_image = filename
                        current_app.logger.info(f'Cover image saved: {filename}')
        except Exception as e:
            current_app.logger.error(f'Cover image upload error: {str(e)}')
            flash(f'Error uploading cover image: {str(e)}', 'warning')

        # Handle digital book file upload
        try:
            if book.is_digital and 'file_upload' in request.files:
                book_file = request.files['file_upload']
                if book_file and book_file.filename:
                    filename = secure_filename(book_file.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'books')
                    os.makedirs(upload_path, exist_ok=True)
                    full_path = os.path.join(upload_path, filename)
                    book_file.save(full_path)
                    book.file_path = filename
                    current_app.logger.info(f'Book file saved: {filename}')
        except Exception as e:
            current_app.logger.error(f'Book file upload error: {str(e)}')
            flash(f'Error uploading book file: {str(e)}', 'warning')

        try:
            db.session.commit()
            flash(f'Book "{book.title}" has been updated successfully.', 'success')
            return redirect(url_for('admin.manage_books'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the book: {str(e)}', 'error')
            current_app.logger.error(f'Edit book error: {str(e)}')
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return render_template('admin/edit_book.html', book=book, categories=categories)

@admin_bp.route('/books/<int:book_id>/delete', methods=['DELETE'])
@librarian_required
def delete_book(book_id):
    """Delete a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        # Check if book has active borrowings
        active_borrowings = book.borrowing_transactions.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count()
        
        if active_borrowings > 0:
            return jsonify({
                'success': False, 
                'message': f'Cannot delete book with {active_borrowings} active borrowings'
            })
        
        book_title = book.title
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Book "{book_title}" deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Delete book error: {str(e)}')
        return jsonify({
            'success': False, 
            'message': 'An error occurred while deleting the book'
        })

@admin_bp.route('/users')
@admin_required
def manage_users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_id = request.args.get('role', type=int)
    status = request.args.get('status', '')
    
    query = User.query
    
    if search:
        search_filter = db.or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            User.first_name.ilike(f'%{search}%'),
            User.last_name.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    if role_id:
        query = query.filter_by(role_id=role_id)
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    users = pagination.items
    
    roles = UserRole.query.order_by(UserRole.role_name).all()
    
    return render_template('admin/users.html',
                         users=users,
                         pagination=pagination,
                         roles=roles,
                         search=search,
                         role_id=role_id,
                         status=status)

@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Add a new user"""
    try:
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        role_id = request.form.get('role_id', type=int)
        password = request.form.get('password', '').strip()
        
        # Validate required fields
        if not first_name:
            flash('First name is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        if not last_name:
            flash('Last name is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        if not username:
            flash('Username is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        if not email:
            flash('Email is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        if not role_id:
            flash('Role is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        if not password:
            flash('Password is required.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" already exists. Please choose a different username.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered. Please use a different email.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Create new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            phone_number=phone if phone else None,
            role_id=role_id
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User "{username}" has been added successfully!', 'success')
        current_app.logger.info(f'New user created: {username} by {current_user.username}')
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'An error occurred while adding the user: {str(e)}'
        flash('An error occurred while adding the user. Please try again.', 'error')
        current_app.logger.error(f'Add user error: {error_msg}')
        import traceback
        current_app.logger.error(traceback.format_exc())
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.username} has been {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating user status.', 'error')
        current_app.logger.error(f'User status toggle error: {str(e)}')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/details')
@admin_required
def view_user_details(user_id):
    """View user details - returns HTML fragment for modal"""
    user = User.query.get_or_404(user_id)
    
    # Get user's subscription info
    subscription = UserSubscription.query.filter_by(
        user_id=user.id,
        is_active=True
    ).first()
    
    # Get borrowing statistics
    total_borrowed = BorrowingTransaction.query.filter_by(user_id=user.id).count()
    currently_borrowed = BorrowingTransaction.query.filter(
        BorrowingTransaction.user_id == user.id,
        BorrowingTransaction.status.in_(['borrowed', 'overdue'])
    ).count()
    overdue_count = BorrowingTransaction.query.filter_by(
        user_id=user.id,
        status='overdue'
    ).count()
    
    # Get recent activity
    recent_borrowings = BorrowingTransaction.query.filter_by(
        user_id=user.id
    ).order_by(db.desc(BorrowingTransaction.borrowed_date)).limit(5).all()
    
    # Get total fines
    total_fines = db.session.query(
        db.func.sum(BorrowingTransaction.fine_amount)
    ).filter_by(user_id=user.id).scalar() or 0
    
    html = f'''
    <div class="row">
        <div class="col-md-4 text-center mb-4">
            <div class="avatar-circle bg-primary text-white mx-auto" style="width: 100px; height: 100px; font-size: 2.5rem;">
                {user.first_name[0] if user.first_name else user.username[0]}
            </div>
            <h4 class="mt-3">{user.first_name} {user.last_name}</h4>
            <p class="text-muted">@{user.username}</p>
            <span class="badge bg-{"danger" if user.role.role_name == "admin" else "warning" if user.role.role_name == "librarian" else "secondary"}">
                {user.role.role_name.title()}
            </span>
            <span class="badge bg-{"success" if user.is_active else "danger"} ms-2">
                {"Active" if user.is_active else "Inactive"}
            </span>
        </div>
        <div class="col-md-8">
            <h5 class="border-bottom pb-2 mb-3">Contact Information</h5>
            <div class="row mb-3">
                <div class="col-6">
                    <small class="text-muted">Email</small>
                    <p class="mb-0">
                        {user.email}
                        {"<i class='fas fa-check-circle text-success ms-1'></i>" if user.email_verified else "<i class='fas fa-exclamation-circle text-warning ms-1'></i>"}
                    </p>
                </div>
                <div class="col-6">
                    <small class="text-muted">Phone</small>
                    <p class="mb-0">{user.phone_number if user.phone_number else "N/A"}</p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-6">
                    <small class="text-muted">Address</small>
                    <p class="mb-0">{user.address if user.address else "N/A"}</p>
                </div>
                <div class="col-6">
                    <small class="text-muted">District</small>
                    <p class="mb-0">{user.district if user.district else "N/A"}</p>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-6">
                    <small class="text-muted">Member Since</small>
                    <p class="mb-0">{user.created_at.strftime("%b %d, %Y") if user.created_at else "Unknown"}</p>
                </div>
                <div class="col-6">
                    <small class="text-muted">Last Login</small>
                    <p class="mb-0">{user.last_login.strftime("%b %d, %Y") if user.last_login else "Never"}</p>
                </div>
            </div>
            
            <h5 class="border-bottom pb-2 mb-3 mt-4">Subscription</h5>
            <div class="row mb-3">
                <div class="col-12">
                    {"<p class='text-success'><i class='fas fa-check-circle'></i> " + subscription.plan.name + " Plan (Expires: " + subscription.end_date.strftime("%b %d, %Y") + ")</p>" if subscription else "<p class='text-muted'>No active subscription</p>"}
                </div>
            </div>
            
            <h5 class="border-bottom pb-2 mb-3 mt-4">Borrowing Statistics</h5>
            <div class="row text-center">
                <div class="col-3">
                    <h3 class="text-primary">{total_borrowed}</h3>
                    <small class="text-muted">Total Borrowed</small>
                </div>
                <div class="col-3">
                    <h3 class="text-info">{currently_borrowed}</h3>
                    <small class="text-muted">Currently Borrowed</small>
                </div>
                <div class="col-3">
                    <h3 class="text-danger">{overdue_count}</h3>
                    <small class="text-muted">Overdue</small>
                </div>
                <div class="col-3">
                    <h3 class="text-warning">M{total_fines:.2f}</h3>
                    <small class="text-muted">Total Fines</small>
                </div>
            </div>
            
            <h5 class="border-bottom pb-2 mb-3 mt-4">Recent Activity</h5>
            <div class="list-group">
                {"".join([f'<div class="list-group-item list-group-item-action"><small class="text-muted">{bt.borrowed_date.strftime("%b %d, %Y")}</small><br><strong>{bt.book.title}</strong><br><span class="badge bg-{"success" if bt.status == "returned" else "warning" if bt.status == "borrowed" else "danger"}">{bt.status.title()}</span></div>' for bt in recent_borrowings]) if recent_borrowings else "<p class='text-muted'>No recent activity</p>"}
            </div>
        </div>
    </div>
    '''
    
    return html

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user information"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update user information
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.phone_number = request.form.get('phone_number', '').strip()
            user.address = request.form.get('address', '').strip()
            user.district = request.form.get('district', '').strip()
            
            # Update role if changed
            role_name = request.form.get('role')
            if role_name:
                role = UserRole.query.filter_by(role_name=role_name).first()
                if role:
                    user.role_id = role.id
            
            # Update email verification status
            email_verified = request.form.get('email_verified') == 'true'
            user.email_verified = email_verified
            
            # Update active status
            is_active = request.form.get('is_active') == 'true'
            if user.id != current_user.id:  # Can't deactivate yourself
                user.is_active = is_active
            
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'User {user.username} has been updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the user. Please try again.', 'error')
            current_app.logger.error(f'Edit user error: {str(e)}')
    
    # GET request - show edit form
    roles = UserRole.query.order_by(UserRole.role_name).all()
    return render_template('admin/edit_user.html', user=user, roles=roles)

@admin_bp.route('/users/export')
@admin_required
def export_users():
    """Export users to CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    # Get all users with filters applied
    search = request.args.get('search', '').strip()
    role_id = request.args.get('role', type=int)
    status = request.args.get('status', '')
    
    query = User.query
    
    if search:
        search_filter = db.or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%'),
            User.first_name.ilike(f'%{search}%'),
            User.last_name.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    if role_id:
        query = query.filter_by(role_id=role_id)
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    users = query.order_by(User.created_at.desc()).all()
    
    # Create CSV
    si = StringIO()
    writer = csv.writer(si)
    
    # Write header
    writer.writerow([
        'ID', 'Username', 'Email', 'First Name', 'Last Name', 
        'Phone', 'District', 'Address', 'Role', 'Status', 
        'Email Verified', 'Member Since', 'Last Login', 
        'Total Borrowed', 'Currently Borrowed'
    ])
    
    # Write data
    for user in users:
        total_borrowed = user.borrowing_transactions.count()
        currently_borrowed = user.borrowing_transactions.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).count()
        
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            user.phone_number if user.phone_number else '',
            user.district if user.district else '',
            user.address if user.address else '',
            user.role.role_name,
            'Active' if user.is_active else 'Inactive',
            'Yes' if user.email_verified else 'No',
            user.created_at.strftime('%Y-%m-%d') if user.created_at else '',
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            total_borrowed,
            currently_borrowed
        ])
    
    # Create response
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=users_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output

@admin_bp.route('/borrowings')
@librarian_required
def manage_borrowings():
    """Manage borrowing transactions"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    
    query = BorrowingTransaction.query
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        search_filter = db.or_(
            BorrowingTransaction.user.has(User.username.ilike(f'%{search}%')),
            BorrowingTransaction.user.has(User.first_name.ilike(f'%{search}%')),
            BorrowingTransaction.user.has(User.last_name.ilike(f'%{search}%')),
            BorrowingTransaction.book.has(Book.title.ilike(f'%{search}%'))
        )
        query = query.filter(search_filter)
    
    pagination = query.order_by(
        BorrowingTransaction.borrowed_date.desc()
    ).paginate(page=page, per_page=4, error_out=False)
    transactions = pagination.items
    
    return render_template('admin/borrowings.html',
                         transactions=transactions,
                         pagination=pagination,
                         status=status,
                         search=search)

@admin_bp.route('/borrowings/bulk-return', methods=['GET', 'POST'])
@librarian_required
def bulk_return():
    """Bulk return processing for borrowed books"""
    if request.method == 'POST':
        transaction_ids = request.form.getlist('transaction_ids')
        
        if not transaction_ids:
            flash('No transactions selected for return.', 'error')
            return redirect(url_for('admin.bulk_return'))
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for trans_id in transaction_ids:
            try:
                transaction = BorrowingTransaction.query.get(int(trans_id))
                if transaction and transaction.status in ['borrowed', 'overdue']:
                    success, message = transaction.return_book(current_user.id)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(f"Transaction {trans_id}: {message}")
            except Exception as e:
                error_count += 1
                error_msg = f'Transaction {trans_id}: {str(e)}'
                error_messages.append(error_msg)
                current_app.logger.error(f'Bulk return error for transaction {trans_id}: {str(e)}')
        
        if success_count > 0:
            flash(f'{success_count} book(s) successfully returned.', 'success')
        if error_count > 0:
            flash(f'{error_count} transaction(s) failed to process.', 'error')
            for msg in error_messages[:3]:  # Show first 3 errors
                flash(msg, 'warning')
        return redirect(url_for('admin.manage_borrowings'))
    
    # GET request - show borrowed books for bulk return
    borrowed_books = BorrowingTransaction.query.filter(
        BorrowingTransaction.status.in_(['borrowed', 'overdue'])
    ).order_by(BorrowingTransaction.borrowed_date.desc()).all()
    
    return render_template('admin/bulk_return.html', transactions=borrowed_books)

@admin_bp.route('/borrowings/<int:borrowing_id>/remind', methods=['POST'])
@librarian_required
def send_reminder(borrowing_id):
    """Send reminder for a specific borrowing"""
    from app.models.notification import Notification
    
    try:
        transaction = BorrowingTransaction.query.get_or_404(borrowing_id)
        
        if transaction.status not in ['borrowed', 'overdue']:
            return jsonify({
                'success': False,
                'message': 'Cannot send reminder for returned books'
            }), 400
        
        # Create notification
        days_until_due = (transaction.due_date - date.today()).days
        if days_until_due < 0:
            message = f"Your borrowed book '{transaction.book.title}' is {abs(days_until_due)} day(s) overdue. Please return it as soon as possible."
            notification_type = 'warning'
        else:
            message = f"Reminder: Your borrowed book '{transaction.book.title}' is due in {days_until_due} day(s). Due date: {transaction.due_date.strftime('%b %d, %Y')}."
            notification_type = 'info'
        
        notification = Notification(
            user_id=transaction.user_id,
            title="Book Return Reminder",
            message=message,
            type=notification_type
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reminder sent successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Send reminder error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to send reminder'
        }), 500

@admin_bp.route('/borrowings/send-reminders', methods=['POST'])
@librarian_required
def send_bulk_reminders():
    """Send reminders to all users with due or overdue books"""
    from app.models.notification import Notification
    
    try:
        # Get all borrowed and overdue books
        transactions = BorrowingTransaction.query.filter(
            BorrowingTransaction.status.in_(['borrowed', 'overdue'])
        ).all()
        
        sent_count = 0
        
        for transaction in transactions:
            # Only send reminders for books due within 3 days or overdue
            days_until_due = (transaction.due_date - date.today()).days
            
            if days_until_due <= 3:
                if days_until_due < 0:
                    message = f"Your borrowed book '{transaction.book.title}' is {abs(days_until_due)} day(s) overdue. Please return it as soon as possible to avoid fines."
                    notification_type = 'warning'
                else:
                    message = f"Reminder: Your borrowed book '{transaction.book.title}' is due in {days_until_due} day(s). Due date: {transaction.due_date.strftime('%b %d, %Y')}."
                    notification_type = 'info'
                
                notification = Notification(
                    user_id=transaction.user_id,
                    title="Book Return Reminder",
                    message=message,
                    type=notification_type
                )
                
                db.session.add(notification)
                sent_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'message': f'{sent_count} reminder(s) sent successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Send bulk reminders error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to send reminders'
        }), 500

@admin_bp.route('/borrowings/export')
@librarian_required
def export_borrowings():
    """Export borrowings to CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    # Get filters from request
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    filter_type = request.args.get('filter', '')
    
    query = BorrowingTransaction.query
    
    # Apply status filter
    if status:
        query = query.filter_by(status=status)
    
    # Apply custom filters
    if filter_type == 'overdue':
        query = query.filter_by(status='overdue')
    elif filter_type == 'due_soon':
        # Books due within 3 days
        three_days_from_now = date.today() + timedelta(days=3)
        query = query.filter(
            BorrowingTransaction.status == 'borrowed',
            BorrowingTransaction.due_date <= three_days_from_now
        )
    
    # Apply search filter
    if search:
        search_filter = db.or_(
            BorrowingTransaction.user.has(User.username.ilike(f'%{search}%')),
            BorrowingTransaction.user.has(User.first_name.ilike(f'%{search}%')),
            BorrowingTransaction.user.has(User.last_name.ilike(f'%{search}%')),
            BorrowingTransaction.book.has(Book.title.ilike(f'%{search}%'))
        )
        query = query.filter(search_filter)
    
    transactions = query.order_by(
        BorrowingTransaction.borrowed_date.desc()
    ).all()
    
    # Create CSV
    si = StringIO()
    writer = csv.writer(si)
    
    # Write header
    writer.writerow([
        'Transaction ID', 'Book Title', 'Author', 'ISBN',
        'User Name', 'Username', 'Email', 'Phone',
        'Borrowed Date', 'Due Date', 'Returned Date',
        'Status', 'Renewal Count', 'Fine Amount', 'Fine Paid',
        'Days Overdue', 'Librarian', 'Notes'
    ])
    
    # Write data
    for transaction in transactions:
        writer.writerow([
            transaction.id,
            transaction.book.title,
            transaction.book.author,
            transaction.book.isbn if transaction.book.isbn else '',
            transaction.user.get_full_name(),
            transaction.user.username,
            transaction.user.email,
            transaction.user.phone_number if transaction.user.phone_number else '',
            transaction.borrowed_date.strftime('%Y-%m-%d %H:%M') if transaction.borrowed_date else '',
            transaction.due_date.strftime('%Y-%m-%d') if transaction.due_date else '',
            transaction.returned_date.strftime('%Y-%m-%d %H:%M') if transaction.returned_date else '',
            transaction.status.title(),
            transaction.renewal_count,
            float(transaction.fine_amount),
            'Yes' if transaction.fine_paid else 'No',
            transaction.days_overdue() if transaction.status in ['borrowed', 'overdue'] else 0,
            transaction.librarian.get_full_name() if transaction.librarian else '',
            transaction.notes if transaction.notes else ''
        ])
    
    # Create response
    filename = f"borrowings_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    if filter_type:
        filename = f"borrowings_{filter_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    
    return output

@admin_bp.route('/reviews')
@librarian_required
def manage_reviews():
    """Manage book reviews"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    query = BookReview.query
    
    if status == 'pending':
        query = query.filter_by(is_approved=False)
    elif status == 'approved':
        query = query.filter_by(is_approved=True)
    
    pagination = query.order_by(BookReview.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    reviews = pagination.items
    
    return render_template('admin/reviews.html',
                         reviews=reviews,
                         pagination=pagination,
                         status=status)

@admin_bp.route('/reviews/<int:review_id>/approve', methods=['POST'])
@librarian_required
def approve_review(review_id):
    """Approve a book review"""
    review = BookReview.query.get_or_404(review_id)
    
    review.approve()
    flash('Review has been approved.', 'success')
    
    return redirect(url_for('admin.manage_reviews'))

@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@librarian_required
def delete_review(review_id):
    """Delete a book review"""
    review = BookReview.query.get_or_404(review_id)
    try:
        db.session.delete(review)
        db.session.commit()
        flash('Review has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting review.', 'error')
    return redirect(url_for('admin.manage_reviews'))

@admin_bp.route('/reviews/<int:review_id>')
@librarian_required
def review_detail(review_id):
    """View details of a single review"""
    review = BookReview.query.get_or_404(review_id)
    return render_template('admin/review_detail.html', review=review)

@admin_bp.route('/categories')
@librarian_required
def manage_categories():
    """Manage categories"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
@librarian_required
def add_category():
    """Add a new category"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Category name is required.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    # Check for duplicate
    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash('A category with this name already exists.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    category = Category(name=name, description=description)
    
    try:
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{name}" has been added.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while adding the category.', 'error')
        current_app.logger.error(f'Add category error: {str(e)}')
    
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/reports')
@librarian_required
def reports():
    """Generate reports"""
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type', 'overview')
    
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Parse dates
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    data = {}
    
    if report_type == 'overview':
        # Overview statistics
        data['total_borrowings'] = BorrowingTransaction.query.filter(
            BorrowingTransaction.borrowed_date.between(start_dt, end_dt)
        ).count()
        
        data['total_returns'] = BorrowingTransaction.query.filter(
            BorrowingTransaction.returned_date.between(start_dt, end_dt)
        ).count()
        
        data['total_downloads'] = DigitalDownload.query.filter(
            DigitalDownload.download_date.between(start_dt, end_dt)
        ).count()
        
        data['new_users'] = User.query.filter(
            User.created_at.between(start_dt, end_dt)
        ).count()
    
    elif report_type == 'popular_books':
        # Most borrowed books
        data['popular_books'] = db.session.query(
            Book.title, Book.author,
            db.func.count(BorrowingTransaction.id).label('borrow_count')
        ).join(BorrowingTransaction).filter(
            BorrowingTransaction.borrowed_date.between(start_dt, end_dt)
        ).group_by(Book.id).order_by(
            db.desc('borrow_count')
        ).limit(20).all()
    
    elif report_type == 'user_activity':
        # Most active users
        data['active_users'] = db.session.query(
            User.username, User.first_name, User.last_name,
            db.func.count(BorrowingTransaction.id).label('activity_count')
        ).join(BorrowingTransaction).filter(
            BorrowingTransaction.borrowed_date.between(start_dt, end_dt)
        ).group_by(User.id).order_by(
            db.desc('activity_count')
        ).limit(20).all()
    
    return render_template('admin/reports.html',
                         data=data,
                         start_date=start_date,
                         end_date=end_date,
                         report_type=report_type)

def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'epub', 'txt'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Subscription Management Routes
@admin_bp.route('/subscriptions')
@admin_required
def subscriptions():
    """Manage subscription plans"""
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price).all()
    active_subscriptions = UserSubscription.query.filter_by(is_active=True).count()
    total_revenue = db.session.query(db.func.sum(BillingRecord.amount)).filter_by(status='paid').scalar() or 0
    
    return render_template('admin/subscriptions.html',
                         plans=plans,
                         active_subscriptions=active_subscriptions,
                         total_revenue=total_revenue)

@admin_bp.route('/subscriptions/plans/add', methods=['POST'])
@admin_required
def add_subscription_plan():
    """Add new subscription plan"""
    try:
        plan = SubscriptionPlan(
            name=request.form['name'],
            description=request.form.get('description', ''),
            price=Decimal(request.form['price']),
            duration_days=int(request.form['duration_days']),
            max_books=int(request.form['max_books']),
            is_active=True
        )
        db.session.add(plan)
        db.session.commit()
        flash(f'Subscription plan "{plan.name}" created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating subscription plan: {str(e)}', 'error')
    
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscriptions/plans/<int:plan_id>/edit', methods=['POST'])
@admin_required
def edit_subscription_plan(plan_id):
    """Edit subscription plan"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    try:
        plan.name = request.form['name']
        plan.description = request.form.get('description', '')
        plan.price = Decimal(request.form['price'])
        plan.duration_days = int(request.form['duration_days'])
        plan.max_books = int(request.form['max_books'])
        plan.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash(f'Subscription plan "{plan.name}" updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating subscription plan: {str(e)}', 'error')
    
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscriptions/plans/<int:plan_id>/delete', methods=['DELETE'])
@admin_required
def delete_subscription_plan(plan_id):
    """Delete subscription plan"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # Check if plan has active subscriptions
    active_subs = UserSubscription.query.filter_by(plan_id=plan_id, is_active=True).count()
    if active_subs > 0:
        return jsonify({'success': False, 'message': f'Cannot delete plan with {active_subs} active subscriptions'})
    
    try:
        db.session.delete(plan)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Plan "{plan.name}" deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting plan: {str(e)}'})

@admin_bp.route('/billing')
@admin_required
def billing_management():
    """Manage billing and payments"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    billing_type = request.args.get('type', '')
    
    query = BillingRecord.query
    
    if status:
        query = query.filter_by(status=status)
    if billing_type:
        query = query.filter_by(billing_type=billing_type)
    
    pagination = query.order_by(BillingRecord.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    billing_records = pagination.items
    
    # Summary statistics
    stats = {
        'total_pending': db.session.query(db.func.sum(BillingRecord.amount)).filter_by(status='pending').scalar() or 0,
        'total_paid': db.session.query(db.func.sum(BillingRecord.amount)).filter_by(status='paid').scalar() or 0,
        'total_overdue': db.session.query(db.func.sum(BillingRecord.amount)).filter(
            BillingRecord.status == 'pending',
            BillingRecord.due_date < datetime.utcnow()
        ).scalar() or 0
    }
    
    return render_template('admin/billing.html',
                         billing_records=billing_records,
                         pagination=pagination,
                         stats=stats)

@admin_bp.route('/billing/<int:billing_id>/mark-paid', methods=['POST'])
@admin_required
def mark_bill_paid(billing_id):
    """Mark a bill as paid"""
    billing_record = BillingRecord.query.get_or_404(billing_id)
    
    if billing_record.status != 'pending':
        return jsonify({'success': False, 'message': 'Bill is not pending'})
    
    try:
        payment_method = request.form.get('payment_method', 'cash')
        transaction_ref = request.form.get('transaction_reference', '')
        
        # Create payment record
        payment = Payment(
            user_id=billing_record.user_id,
            billing_record_id=billing_record.id,
            amount=billing_record.amount,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed',
            processed_at=datetime.utcnow()
        )
        db.session.add(payment)
        
        # Mark bill as paid
        billing_record.mark_as_paid(payment_method, transaction_ref)
        
        # Activate subscription if applicable
        if billing_record.subscription_id:
            subscription = UserSubscription.query.get(billing_record.subscription_id)
            if subscription:
                subscription.is_active = True
                db.session.commit()
        
        return jsonify({'success': True, 'message': 'Payment recorded successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error recording payment: {str(e)}'})

@admin_bp.route('/user-subscriptions')
@admin_required
def user_subscriptions():
    """Manage user subscriptions"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = db.session.query(UserSubscription).join(User).join(SubscriptionPlan)
    
    if status == 'active':
        query = query.filter(
            UserSubscription.is_active == True,
            UserSubscription.end_date > datetime.utcnow()
        )
    elif status == 'expired':
        query = query.filter(UserSubscription.end_date <= datetime.utcnow())
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    pagination = query.order_by(UserSubscription.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    subscriptions = pagination.items
    
    return render_template('admin/user_subscriptions.html',
                         subscriptions=subscriptions,
                         pagination=pagination)

@admin_bp.route('/subscription/<int:subscription_id>/extend', methods=['POST'])
@admin_required
def extend_subscription(subscription_id):
    """Extend a user's subscription"""
    subscription = UserSubscription.query.get_or_404(subscription_id)
    
    try:
        days = int(request.form.get('days', 30))
        subscription.end_date = subscription.end_date + timedelta(days=days)
        db.session.commit()
        
        flash(f'Subscription extended by {days} days', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error extending subscription: {str(e)}', 'error')
    
    return redirect(url_for('admin.user_subscriptions'))