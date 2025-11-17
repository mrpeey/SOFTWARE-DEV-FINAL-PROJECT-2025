#!/usr/bin/env python
"""
Approve all reviews in the database for testing purposes.
"""
from EduConnect_Lesotho_Dig_Library.app import db
from EduConnect_Lesotho_Dig_Library.app.models.review import BookReview

def approve_all_reviews():
    count = 0
    for review in BookReview.query.filter_by(is_approved=False).all():
        review.is_approved = True
        db.session.add(review)
        count += 1
    db.session.commit()
    print(f"Approved {count} reviews.")

if __name__ == "__main__":
    approve_all_reviews()
