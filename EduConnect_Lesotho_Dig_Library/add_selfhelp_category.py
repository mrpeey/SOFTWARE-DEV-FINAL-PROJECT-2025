"""
Add Self-Help & Personal Development category with free books
"""
from app import create_app, db
from app.models.book import Book, Category
from app.models.user import User
import os

def add_selfhelp_category():
    """Add Self-Help category and books"""
    app = create_app()
    
    with app.app_context():
        # Check if category already exists
        category = Category.query.filter_by(name='Self-Help & Personal Development').first()
        
        if not category:
            # Create category
            category = Category(
                name='Self-Help & Personal Development',
                description='Books on personal growth, motivation, and self-improvement'
            )
            db.session.add(category)
            db.session.commit()
            print(f"Created category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")
        
        # Get admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Admin user not found!")
            return
        
        # Free books to add (Project Gutenberg - public domain)
        books_data = [
            {
                'title': 'Think and Grow Rich',
                'author': 'Napoleon Hill',
                'isbn': '9780449214923',
                'publisher': 'Public Domain',
                'publication_year': 1937,
                'pages': 238,
                'language': 'English',
                'description': 'A classic book on personal achievement and wealth-building. This timeless masterpiece has inspired millions to achieve success through the power of thought and positive mental attitude.',
                'is_digital': True,
                'is_featured': True
            },
            {
                'title': 'As a Man Thinketh',
                'author': 'James Allen',
                'isbn': '9781604593891',
                'publisher': 'Public Domain',
                'publication_year': 1903,
                'pages': 68,
                'language': 'English',
                'description': 'A philosophical essay on the power of thought in creating one\'s circumstances. A foundational text in the self-help genre that explores how our thoughts shape our reality.',
                'is_digital': True,
                'is_featured': False
            },
            {
                'title': 'The Science of Getting Rich',
                'author': 'Wallace D. Wattles',
                'isbn': '9781603863056',
                'publisher': 'Public Domain',
                'publication_year': 1910,
                'pages': 100,
                'language': 'English',
                'description': 'A practical guide to creating wealth through the power of positive thinking and constructive action. This influential book has inspired many modern self-help authors.',
                'is_digital': True,
                'is_featured': False
            },
            {
                'title': 'The Power of Concentration',
                'author': 'Theron Q. Dumont',
                'isbn': '9781585092925',
                'publisher': 'Public Domain',
                'publication_year': 1918,
                'pages': 150,
                'language': 'English',
                'description': 'Learn to harness the power of your mind through concentration exercises. This classic guide offers practical techniques for developing focus and mental discipline.',
                'is_digital': True,
                'is_featured': False
            }
        ]
        
        added_count = 0
        
        for book_data in books_data:
            # Check if book already exists
            existing = Book.query.filter_by(title=book_data['title']).first()
            if existing:
                print(f"Book already exists: {book_data['title']}")
                continue
            
            # Create book
            book = Book(
                title=book_data['title'],
                author=book_data['author'],
                isbn=book_data.get('isbn'),
                publisher=book_data['publisher'],
                publication_year=book_data['publication_year'],
                pages=book_data['pages'],
                language=book_data['language'],
                description=book_data['description'],
                category_id=category.id,
                is_digital=book_data['is_digital'],
                is_featured=book_data.get('is_featured', False),
                total_copies=1,
                available_copies=1,
                created_by=admin.id
            )
            
            db.session.add(book)
            added_count += 1
            print(f"Added book: {book.title}")
        
        db.session.commit()
        print(f"\nCompleted! Added {added_count} books to '{category.name}' category")
        print(f"Total books in category: {category.books.count()}")

if __name__ == '__main__':
    add_selfhelp_category()
