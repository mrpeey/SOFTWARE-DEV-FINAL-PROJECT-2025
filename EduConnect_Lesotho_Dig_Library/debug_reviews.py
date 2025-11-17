#!/usr/bin/env python
"""Debug script for review functionality"""

from run import app
from app import db
from app.models.book import Book
from app.models.user import User
from app.models.review import BookReview

def debug_reviews():
    """Debug review functionality"""
    with app.app_context():
        print("=== Review System Debug ===\n")
        
        # Check if tables exist
        try:
            review_count = BookReview.query.count()
            print(f"Total reviews in database: {review_count}")
        except Exception as e:
            print(f"Error accessing reviews table: {e}")
            return
        
        # Check approved vs pending reviews
        approved_count = BookReview.query.filter_by(is_approved=True).count()
        pending_count = BookReview.query.filter_by(is_approved=False).count()
        
        print(f"Approved reviews: {approved_count}")
        print(f"Pending reviews: {pending_count}")
        
        # Show some sample reviews
        if review_count > 0:
            print("\n=== Sample Reviews ===")
            reviews = BookReview.query.limit(5).all()
            for review in reviews:
                try:
                    user_name = review.user.get_full_name() if review.user else "Unknown"
                    book_title = review.book.title if review.book else "Unknown"
                    print(f"Review {review.id}: {user_name} -> {book_title}")
                    print(f"  Rating: {review.rating}/5")
                    print(f"  Approved: {review.is_approved}")
                    print(f"  Text: {review.review_text[:50]}..." if review.review_text else "  No text")
                    print()
                except Exception as e:
                    print(f"Error displaying review {review.id}: {e}")
        
        # Check books and their review counts
        print("\n=== Books with Reviews ===")
        books_with_reviews = db.session.query(Book).join(BookReview).distinct().limit(5).all()
        
        if books_with_reviews:
            for book in books_with_reviews:
                try:
                    review_count = book.book_reviews.count()
                    approved_count = book.book_reviews.filter_by(is_approved=True).count()
                    print(f"Book: {book.title}")
                    print(f"  Total reviews: {review_count}")
                    print(f"  Approved reviews: {approved_count}")
                    print(f"  Average rating: {book.get_average_rating()}")
                    print()
                except Exception as e:
                    print(f"Error processing book {book.id}: {e}")
        else:
            print("No books have reviews yet.")
        
        # Create a test review if none exist
        if review_count == 0:
            print("\n=== Creating Test Review ===")
            try:
                # Get first user and first book
                user = User.query.first()
                book = Book.query.first()
                
                if user and book:
                    test_review = BookReview(
                        user_id=user.id,
                        book_id=book.id,
                        rating=5,
                        review_text="This is a test review to check the review system functionality.",
                        is_approved=True  # Approve for testing
                    )
                    
                    db.session.add(test_review)
                    db.session.commit()
                    
                    print(f"Created test review: User {user.get_full_name()} reviewed '{book.title}'")
                else:
                    print("Cannot create test review: No users or books found")
                    
            except Exception as e:
                db.session.rollback()
                print(f"Error creating test review: {e}")

if __name__ == '__main__':
    debug_reviews()