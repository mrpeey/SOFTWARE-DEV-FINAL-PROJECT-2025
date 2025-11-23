from app import create_app, db
from app.models.offline import DigitalDownload
from app.models.user import User
from app.models.book import Book

app = create_app()

with app.app_context():
    print("All DigitalDownload records:")
    downloads = DigitalDownload.query.all()
    for d in downloads:
        print(f"ID: {d.id}, user_id: {d.user_id}, book_id: {d.book_id}, file_path: {getattr(d, 'file_path', None)}, download_complete: {d.download_complete}")
    print("\nAll Users:")
    for u in User.query.all():
        print(f"ID: {u.id}, username: {u.username}, email: {u.email}")
    print("\nAll Digital Books:")
    for b in Book.query.filter_by(is_digital=True).all():
        print(f"ID: {b.id}, title: {b.title}")
