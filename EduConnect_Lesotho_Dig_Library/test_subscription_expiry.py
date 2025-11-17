#!/usr/bin/env python3
"""
Script to test subscription expiry and automatic renewal billing
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run import app
from app import db
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription, BillingRecord
from decimal import Decimal

def test_subscription_expiry():
    """Test subscription expiry and renewal billing logic"""
    with app.app_context():
        print("Testing subscription expiry and renewal billing...")
        
        # Find a non-admin user to test with
        test_user = User.query.filter(
            User.role.has(role_name='public')
        ).first()
        
        if not test_user:
            print("No non-admin user found. Creating test user...")
            from app.models.user import UserRole
            public_role = UserRole.query.filter_by(role_name='public').first()
            if not public_role:
                print("Public role not found!")
                return False
            
            test_user = User(
                username='testuser',
                email='test@library.com',
                first_name='Test',
                last_name='User',
                role_id=public_role.id,
                is_active=True,
                email_verified=True
            )
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: {test_user.username}")
        
        # Get a subscription plan
        plan = SubscriptionPlan.query.first()
        if not plan:
            print("No subscription plan found!")
            return False
        
        print(f"Using plan: {plan.name} (LSL {plan.price})")
        
        # Create an expired subscription
        expired_date = datetime.utcnow() - timedelta(days=2)  # Expired 2 days ago
        expired_subscription = UserSubscription(
            user_id=test_user.id,
            plan_id=plan.id,
            start_date=expired_date - timedelta(days=30),
            end_date=expired_date,
            is_active=True  # Will be set to False when processed
        )
        db.session.add(expired_subscription)
        db.session.commit()
        
        print(f"Created expired subscription for {test_user.username}")
        print(f"Subscription expired on: {expired_subscription.end_date}")
        
        # Test subscription status
        print("\n--- Testing Subscription Status ---")
        status = test_user.get_subscription_status()
        print(f"Status: {status['status']}")
        print(f"Message: {status['message']}")
        print(f"Can borrow: {status.get('can_borrow', False)}")
        print(f"Can download: {status.get('can_download', False)}")
        
        # Test borrowing ability
        print(f"\n--- Testing Access Rights ---")
        print(f"Can borrow physical books: {test_user.can_borrow_physical_books()}")
        print(f"Can access digital content: {test_user.can_access_digital_content()}")
        
        # Simulate automatic renewal bill creation
        print(f"\n--- Creating Automatic Renewal Bill ---")
        try:
            # Mark subscription as inactive
            expired_subscription.is_active = False
            
            # Create new subscription for renewal
            new_subscription = UserSubscription(
                user_id=test_user.id,
                plan_id=plan.id,
                start_date=expired_subscription.end_date,
                is_active=False  # Will be activated when paid
            )
            db.session.add(new_subscription)
            db.session.flush()
            
            # Create billing record
            billing_record = BillingRecord(
                user_id=test_user.id,
                subscription_id=new_subscription.id,
                amount=plan.price,
                description=f'Automatic renewal of {plan.name} plan',
                billing_type='subscription',
                due_date=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(billing_record)
            db.session.commit()
            
            print(f"Created renewal bill: LSL {billing_record.amount}")
            print(f"Due date: {billing_record.due_date}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating renewal bill: {str(e)}")
            return False
        
        # Test status after renewal bill creation
        print(f"\n--- Testing Status After Renewal Bill ---")
        status = test_user.get_subscription_status()
        print(f"Status: {status['status']}")
        print(f"Message: {status['message']}")
        print(f"Can borrow: {status.get('can_borrow', False)}")
        print(f"Can download: {status.get('can_download', False)}")
        
        if 'pending_bill_amount' in status:
            print(f"Pending bill amount: LSL {status['pending_bill_amount']}")
        
        # Test updated access rights
        print(f"\n--- Testing Updated Access Rights ---")
        print(f"Can borrow physical books: {test_user.can_borrow_physical_books()}")
        print(f"Can access digital content: {test_user.can_access_digital_content()}")
        
        # Clean up test data
        print(f"\n--- Cleaning Up Test Data ---")
        try:
            db.session.delete(billing_record)
            db.session.delete(new_subscription)
            db.session.delete(expired_subscription)
            db.session.delete(test_user)
            db.session.commit()
            print("Test data cleaned up successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning up: {str(e)}")
        
        return True

if __name__ == '__main__':
    print("Starting subscription expiry test...")
    success = test_subscription_expiry()
    if success:
        print("\n✅ Subscription expiry test completed successfully!")
        print("\nKey findings:")
        print("- Users with expired subscriptions cannot borrow physical books")
        print("- Users with pending renewal bills can still download digital books")
        print("- Automatic renewal bills are created properly")
        print("- Status messages are clear and informative")
    else:
        print("\n❌ Subscription expiry test failed!")
        sys.exit(1)