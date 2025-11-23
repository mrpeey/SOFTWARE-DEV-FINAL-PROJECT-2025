from app import create_app, db
from app.models.user import User
from app.models.book import Book
from app.models.offline import DigitalDownload
from datetime import datetime

app = create_app()

with app.app_context():
    # Set cover image for book ID 1
    book = Book.query.get(1)
    if book:
        book.cover_image = "uploads/covers/sample_cover.jpg"  # Place your image in static/uploads/covers/
        db.session.commit()
        print(f"Set cover image for book: {book.title}")
    else:
        print("Book with ID 1 not found.")
