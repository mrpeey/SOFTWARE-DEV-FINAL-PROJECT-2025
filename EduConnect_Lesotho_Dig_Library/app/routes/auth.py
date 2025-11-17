from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User, UserRole
from app.models.notification import Notification
from urllib.parse import urlparse as url_parse
from datetime import datetime
from werkzeug.utils import secure_filename
import re
import os

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))
        
        if not username_or_email or not password:
            flash('Please provide both username/email and password.', 'error')
            return render_template('auth/login.html')
        
        # Find user by username or email
        user = User.query.filter(
            db.or_(
                User.username == username_or_email,
                User.email == username_or_email
            )
        ).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the library administrator.', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember_me)
            user.update_last_login()
            
            # Create welcome notification for first-time login
            if user.last_login is None:
                welcome_notification = Notification(
                    user_id=user.id,
                    title="Welcome to EduConnect Lesotho Digital Library!",
                    message="Thank you for joining our digital library. Explore our collection of books and resources.",
                    type='success'
                )
                db.session.add(welcome_notification)
                db.session.commit()
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            
            # Redirect to next page if specified
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.index')
            
            return redirect(next_page)
        else:
            flash('Invalid username/email or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Check if public registration is allowed
    from flask import current_app
    if not current_app.config.get('ALLOW_PUBLIC_REGISTRATION', True):
        flash('Public registration is currently disabled. Please contact the library administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', 'Butha-Buthe').strip()
        user_type = request.form.get('user_type', 'public')
        profile_image_file = request.files.get('profile_image')
        
        # Validation
        errors = []
        
        if not all([username, email, password, confirm_password, first_name, last_name]):
            errors.append('Please fill in all required fields.')
        
        if len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not validate_email(email):
            errors.append('Please provide a valid email address.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        is_valid_password, password_message = validate_password(password)
        if not is_valid_password:
            errors.append(password_message)
        
        # Check for existing users
        existing_user = User.query.filter(
            db.or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                errors.append('Username already exists.')
            if existing_user.email == email:
                errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Get user role
        role = UserRole.query.filter_by(role_name=user_type).first()
        if not role:
            role = UserRole.query.filter_by(role_name='public').first()
        
        # Handle profile image upload
        profile_image_path = None
        if profile_image_file and profile_image_file.filename:
            filename = secure_filename(profile_image_file.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                flash('Invalid image format. Only JPG, PNG, GIF allowed.', 'error')
                return render_template('auth/register.html')
            if len(profile_image_file.read()) > 2 * 1024 * 1024:
                flash('Image file too large (max 2MB).', 'error')
                return render_template('auth/register.html')
            profile_image_file.seek(0)
            save_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            profile_image_file.save(save_path)
            profile_image_path = f'static/uploads/profiles/{filename}'

        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            address=address,
            district=district,
            role_id=role.id,
            profile_image=profile_image_path
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Create welcome notification
            welcome_notification = Notification(
                user_id=user.id,
                title="Registration Successful!",
                message="Your account has been created successfully. You can now browse and borrow books from our digital library.",
                type='success'
            )
            db.session.add(welcome_notification)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            current_app.logger.error(f'Registration error: {str(e)}')
    
    # Get available districts for the form
    districts = [
        'Butha-Buthe', 'Leribe', 'Berea', 'Maseru', 'Mafeteng',
        'Mohale\'s Hoek', 'Quthing', 'Qacha\'s Nek', 'Mokhotlong', 'Thaba-Tseka'
    ]
    
    return render_template('auth/register.html', districts=districts)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password - for future implementation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please provide your email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        if not validate_email(email):
            flash('Please provide a valid email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        # Check if user exists (but don't reveal if they don't for security)
        user = User.query.filter_by(email=email).first()
        
        # Always show success message for security (don't reveal if email exists)
        flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        
        # TODO: Implement actual email sending in future
        # For now, just log the request
        if user:
            # In a real implementation, you would:
            # 1. Generate a secure reset token
            # 2. Store it with expiration time
            # 3. Send email with reset link
            # 4. Allow user to reset password using the token
            current_app.logger.info(f'Password reset requested for user: {user.username} ({email})')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    flash(f'Goodbye, {current_user.first_name}!', 'info')
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user statistics
    stats = current_user.get_reading_statistics()
    
    # Get recent borrowing history
    recent_borrowings = current_user.borrowing_transactions.order_by(
        db.desc('borrowed_date')
    ).limit(5).all()
    
    # Get current borrowings
    current_borrowings = current_user.get_current_borrowings()
    
    # Get unread notifications
    notifications = current_user.notifications.filter_by(
        is_read=False
    ).order_by(db.desc('created_at')).limit(10).all()
    
    return render_template('auth/profile.html',
                         stats=stats,
                         recent_borrowings=recent_borrowings,
                         current_borrowings=current_borrowings,
                         notifications=notifications)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', '').strip()
        
        # Validation
        if not all([first_name, last_name]):
            flash('First name and last name are required.', 'error')
            return render_template('auth/edit_profile.html')
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                # Validate file
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                
                if file_ext in allowed_extensions:
                    # Create unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_filename = f"profile_{current_user.id}_{timestamp}.{file_ext}"
                    
                    # Save file
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, new_filename)
                    
                    try:
                        file.save(file_path)
                        
                        # Delete old profile image if exists
                        if current_user.profile_image:
                            old_image_path = os.path.join(upload_folder, current_user.profile_image)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                        
                        current_user.profile_image = new_filename
                    except Exception as e:
                        current_app.logger.error(f'Profile image upload error: {str(e)}')
                        flash('Failed to upload profile image.', 'error')
                else:
                    flash('Invalid image file type. Please use PNG, JPG, JPEG, or GIF.', 'error')
        
        # Update user
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.phone_number = phone_number
        current_user.address = address
        current_user.district = district
        current_user.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'error')
            current_app.logger.error(f'Profile update error: {str(e)}')
    
    districts = [
        'Butha-Buthe', 'Leribe', 'Berea', 'Maseru', 'Mafeteng',
        'Mohale\'s Hoek', 'Quthing', 'Qacha\'s Nek', 'Mokhotlong', 'Thaba-Tseka'
    ]
    
    return render_template('auth/edit_profile.html', districts=districts)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        is_valid, message = validate_password(new_password)
        if not is_valid:
            flash(message, 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        current_user.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while changing your password.', 'error')
            current_app.logger.error(f'Password change error: {str(e)}')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = current_user.notifications.order_by(
        db.desc('created_at')
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    notifications = pagination.items
    
    return render_template('auth/notifications.html', 
                         notifications=notifications,
                         pagination=pagination)

@auth_bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first()
    
    if notification:
        notification.mark_as_read()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@auth_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    current_user.notifications.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})