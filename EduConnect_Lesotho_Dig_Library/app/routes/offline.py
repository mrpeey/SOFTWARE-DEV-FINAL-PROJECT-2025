from flask import Blueprint, render_template
from flask_login import login_required, current_user, AnonymousUserMixin
from app.models.offline import DigitalDownload
from app.models.book import Book
from app.models.bookmark import Bookmark
from app.models.note import Note
from app.models.search_history import SearchHistory

offline_bp = Blueprint('offline', __name__)

@offline_bp.route('/offline-access')
@login_required
def offline_access():
    downloads = DigitalDownload.query.filter_by(user_id=current_user.id, download_complete=True).all()
    books = [Book.query.get(d.book_id) for d in downloads]

    # Bookmarks & Notes
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
    notes = Note.query.filter_by(user_id=current_user.id).all()
    # Combine bookmarks and notes for display
    bookmarks_notes = [
        {
            'book_title': Book.query.get(b.book_id).title if Book.query.get(b.book_id) else '',
            'page': b.page,
            'content': getattr(b, 'content', None) or 'Bookmark',
        } for b in bookmarks + notes
    ]

    # Search History
    search_history = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.date.desc()).limit(10).all()

    # Ensure user is always defined
    user = current_user if hasattr(current_user, 'name') else AnonymousUserMixin()
    if not hasattr(user, 'name'):
        user.name = 'Guest'
        user.email = ''
        user.preferences = ''

    storage_used = sum([d.file_size or 0 for d in downloads]) // (1024 * 1024)
    storage_total = 8
    storage_percent = int((storage_used / storage_total) * 100) if storage_total else 0
    device_info = "Browser/Device Info"

    return render_template(
        'main/offline_access.html',
        books=books,
        bookmarks=bookmarks_notes,
        search_history=search_history,
        user=user,
        storage_used=storage_used,
        storage_total=storage_total,
        storage_percent=storage_percent,
        device_info=device_info
    )
