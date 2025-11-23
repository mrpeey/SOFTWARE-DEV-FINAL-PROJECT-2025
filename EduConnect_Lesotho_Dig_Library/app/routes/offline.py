from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user, AnonymousUserMixin
from app.models.offline import DigitalDownload
from app.models.book import Book
from app.models.bookmark import Bookmark
from app.models.note import Note
from app.models.search_history import SearchHistory
import os

offline_bp = Blueprint('offline', __name__)

@offline_bp.route('/offline-access')
@login_required
def offline_access():
    downloads = DigitalDownload.query.filter_by(user_id=current_user.id, download_complete=True).all()
    books = [Book.query.get(d.book_id) for d in downloads]
    download_links = [
        {
            'id': d.id,
            'book_title': Book.query.get(d.book_id).title if Book.query.get(d.book_id) else '',
            'file_path': getattr(d, 'file_path', None),
            'download_date': d.download_date,
            'user_id': d.user_id
        } for d in downloads
    ]
    download_count = len(download_links)

    # Bookmarks & Notes
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
    notes = Note.query.filter_by(user_id=current_user.id).all()
    bookmarks_notes = [
        {
            'book_title': Book.query.get(b.book_id).title if Book.query.get(b.book_id) else '',
            'page': b.page,
            'content': getattr(b, 'content', None) or 'Bookmark',
        } for b in bookmarks + notes
    ]

    search_history = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.date.desc()).limit(10).all()

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
        download_links=download_links,
        download_count=download_count,
        bookmarks=bookmarks_notes,
        search_history=search_history,
        user=user,
        storage_used=storage_used,
        storage_total=storage_total,
        storage_percent=storage_percent,
        device_info=device_info
    )

# Route to serve downloaded files
@offline_bp.route('/downloaded/<int:download_id>')
@login_required
def serve_downloaded_file(download_id):
    download = DigitalDownload.query.get_or_404(download_id)
    if not hasattr(download, 'file_path') or not download.file_path:
        flash('File not found.', 'error')
        return redirect(url_for('offline.offline_access'))
    file_dir = os.path.join(current_app.static_folder, 'uploads', 'downloads')
    return send_from_directory(file_dir, download.file_path, as_attachment=True)

# Route to delete a downloaded file and its record
@offline_bp.route('/delete-download/<int:download_id>', methods=['POST'])
@login_required
def delete_download(download_id):
    download = DigitalDownload.query.get_or_404(download_id)
    file_path = getattr(download, 'file_path', None)
    file_dir = os.path.join(current_app.static_folder, 'uploads', 'downloads')
    if file_path:
        try:
            os.remove(os.path.join(file_dir, file_path))
        except Exception:
            pass
    try:
        db.session.delete(download)
        db.session.commit()
        flash('Download deleted.', 'success')
    except Exception:
        db.session.rollback()
        flash('Could not delete download.', 'error')
    return redirect(url_for('offline.offline_access'))
