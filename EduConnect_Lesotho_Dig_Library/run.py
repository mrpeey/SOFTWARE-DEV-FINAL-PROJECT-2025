#!/usr/bin/env python3
"""
EduConnect Lesotho Digital Library
A comprehensive library management system designed for resource-constrained environments
with support for offline access and digital literacy programs.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app, db
from app.models.user import User, UserRole
from app.models.book import Book, Category
from app.models.borrowing import BorrowingTransaction
from app.models.review import BookReview
from app.models.notification import Notification
from app.models.reservation import BookReservation
from app.models.offline import OfflineToken, DigitalDownload, ReadingSession, LiteracyProgress

# Create Flask application
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'UserRole': UserRole,
        'Book': Book,
        'Category': Category,
        'BorrowingTransaction': BorrowingTransaction,
        'BookReview': BookReview,
        'Notification': Notification,
        'BookReservation': BookReservation,
        'OfflineToken': OfflineToken,
        'DigitalDownload': DigitalDownload,
        'ReadingSession': ReadingSession,
        'LiteracyProgress': LiteracyProgress
    }

@app.cli.command()
def init_db():
    """Initialize the database with tables and default data"""
    print("Creating database tables...")
    db.create_all()
    
    print("Creating default user roles...")
    roles_data = [
        ('admin', 'System administrator with full access'),
        ('librarian', 'Library staff with management privileges'),
        ('student', 'Student user with borrowing privileges'),
        ('public', 'General public user with limited access'),
        ('researcher', 'Researcher with extended access to academic resources')
    ]
    
    for role_name, description in roles_data:
        if not UserRole.query.filter_by(role_name=role_name).first():
            role = UserRole(role_name=role_name, description=description)
            db.session.add(role)
    
    print("Creating default categories...")
    categories_data = [
        ('Academic', 'Academic and educational resources'),
        ('Literature', 'Fiction and literary works'),
        ('Science & Technology', 'Science, technology and engineering'),
        ('History & Culture', 'Historical and cultural materials'),
        ('Health & Medicine', 'Medical and health resources'),
        ('Agriculture', 'Agricultural and farming resources'),
        ('Business & Economics', 'Business and economic materials'),
        ('Government & Law', 'Legal and government documents'),
        ('Digital Literacy', 'Computer and digital skills resources'),
        ('Local Resources', 'Local Lesotho and community materials')
    ]
    
    for name, description in categories_data:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name, description=description)
            db.session.add(category)
    
    db.session.commit()
    print("Database initialized successfully!")

@app.cli.command()
def create_admin():
    """Create an admin user"""
    username = input("Enter admin username: ")
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        print(f"User {username} already exists!")
        return
    
    if User.query.filter_by(email=email).first():
        print(f"Email {email} already registered!")
        return
    
    # Get admin role
    admin_role = UserRole.query.filter_by(role_name='admin').first()
    if not admin_role:
        print("Admin role not found! Please run 'flask init-db' first.")
        return
    
    # Create admin user
    admin_user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role_id=admin_role.id,
        is_active=True,
        email_verified=True
    )
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"Admin user {username} created successfully!")

@app.cli.command()
def update_overdue():
    """Update overdue book status and calculate fines"""
    count = BorrowingTransaction.update_overdue_status()
    print(f"Updated {count} overdue transactions")

@app.cli.command()
def cleanup_expired():
    """Cleanup expired reservations and tokens"""
    # Cleanup expired reservations
    from app.models.reservation import BookReservation
    expired_reservations = BookReservation.cleanup_expired()
    print(f"Marked {expired_reservations} reservations as expired")
    
    # Deactivate expired offline tokens
    from datetime import datetime
    expired_tokens = OfflineToken.query.filter(
        OfflineToken.is_active == True,
        OfflineToken.expiry_date < datetime.utcnow()
    ).update({'is_active': False})
    
    db.session.commit()
    print(f"Deactivated {expired_tokens} expired offline tokens")

@app.cli.command()
def sample_data():
    """Add sample data for testing"""
    print("Adding sample books...")
    
    # Get categories
    academic = Category.query.filter_by(name='Academic').first()
    literature = Category.query.filter_by(name='Literature').first()
    digital_literacy = Category.query.filter_by(name='Digital Literacy').first()
    
    # Get admin user to assign as creator
    admin_user = User.query.filter(User.role.has(role_name='admin')).first()
    if not admin_user:
        print("No admin user found! Please create an admin user first.")
        return
    
    sample_books = [
        {
            'title': 'Introduction to Computer Science',
            'author': 'Dr. Jane Smith',
            'isbn': '978-0123456789',
            'publisher': 'Education Press',
            'publication_year': 2023,
            'language': 'English',
            'description': 'A comprehensive guide to computer science fundamentals for beginners.',
            'category_id': academic.id if academic else 1,
            'is_digital': True,
            'total_copies': 1,
            'is_featured': True
        },
        {
            'title': 'Digital Literacy for Everyone',
            'author': 'Mary Johnson',
            'isbn': '978-0987654321',
            'publisher': 'Tech Publications',
            'publication_year': 2022,
            'language': 'English',
            'description': 'Essential digital skills for the modern world.',
            'category_id': digital_literacy.id if digital_literacy else 1,
            'is_digital': True,
            'total_copies': 1,
            'is_featured': True
        },
        {
            'title': 'Lesotho Folk Tales',
            'author': 'Traditional Stories',
            'publisher': 'Local Heritage Press',
            'publication_year': 2021,
            'language': 'English',
            'description': 'Collection of traditional Lesotho stories and folklore.',
            'category_id': literature.id if literature else 1,
            'is_digital': False,
            'total_copies': 5,
            'available_copies': 5
        }
    ]
    
    for book_data in sample_books:
        if not Book.query.filter_by(title=book_data['title']).first():
            book = Book(**book_data, created_by=admin_user.id)
            db.session.add(book)
    
    db.session.commit()
    print("Sample data added successfully!")

if __name__ == '__main__':
    # For development only - use port 8080 to avoid conflicts
    print("Starting EduConnect Lesotho Digital Library...")
    print("Access URL: http://127.0.0.1:8080")
    print("Admin Login: admin / Admin123")
    print("-" * 50)
    # Allow overriding host/port via environment for remote testing
    run_host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    run_port = int(os.getenv('FLASK_RUN_PORT', '8080'))
    run_debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('1', 'true', 'yes')
    print(f"Running on {run_host}:{run_port} (debug={run_debug})")
    app.run(host=run_host, port=run_port, debug=run_debug, threaded=True)