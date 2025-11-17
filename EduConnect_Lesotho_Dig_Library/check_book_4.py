from app import app
from app.models.book import Book
with app.app_context():
    book = Book.query.get(4)
    print(book)
    if book:
        print('Active:', book.is_active)
        print('Title:', book.title)
    else:
        print('Book not found')
