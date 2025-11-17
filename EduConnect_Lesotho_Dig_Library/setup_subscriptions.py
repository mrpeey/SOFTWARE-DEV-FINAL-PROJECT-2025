#!/usr/bin/env python3
"""
Script to initialize subscription plans for the EduConnect Lesotho Digital Library
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run import app
from app import db
from app.models.subscription import SubscriptionPlan
from decimal import Decimal

def create_subscription_plans():
    """Create default subscription plans"""
    with app.app_context():
        # Check if plans already exist
        existing_plans = SubscriptionPlan.query.count()
        if existing_plans > 0:
            print(f"Subscription plans already exist ({existing_plans} plans found)")
            return

        # Create subscription plans
        plans = [
            {
                'name': 'Basic',
                'description': 'Perfect for casual readers - borrow 1 book at a time',
                'price': Decimal('50.00'),  # LSL 50
                'duration_days': 30,
                'max_books': 1,
                'is_active': True
            },
            {
                'name': 'Standard',
                'description': 'Great for regular readers - borrow up to 3 books at once',
                'price': Decimal('100.00'),  # LSL 100
                'duration_days': 30,
                'max_books': 3,
                'is_active': True
            },
            {
                'name': 'Premium',
                'description': 'For avid readers - borrow up to 5 books with extended access',
                'price': Decimal('150.00'),  # LSL 150
                'duration_days': 30,
                'max_books': 5,
                'is_active': True
            },
            {
                'name': 'Student',
                'description': 'Special rate for students - 2 books with education focus',
                'price': Decimal('30.00'),  # LSL 30
                'duration_days': 30,
                'max_books': 2,
                'is_active': True
            },
            {
                'name': 'Family',
                'description': 'Perfect for families - 6 books for multiple users',
                'price': Decimal('200.00'),  # LSL 200
                'duration_days': 30,
                'max_books': 6,
                'is_active': True
            }
        ]

        try:
            for plan_data in plans:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
            
            db.session.commit()
            print(f"Successfully created {len(plans)} subscription plans:")
            
            for plan in plans:
                print(f"  - {plan['name']}: LSL {plan['price']} ({plan['max_books']} books, {plan['duration_days']} days)")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating subscription plans: {str(e)}")
            return False
        
        return True

if __name__ == '__main__':
    print("Initializing subscription plans for EduConnect Lesotho Digital Library...")
    success = create_subscription_plans()
    if success:
        print("Subscription plans setup completed successfully!")
    else:
        print("Failed to setup subscription plans.")
        sys.exit(1)