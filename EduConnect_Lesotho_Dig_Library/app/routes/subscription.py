from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import abort
from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models.subscription import SubscriptionPlan, UserSubscription, BillingRecord, Payment
from app.models.user import User

subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscription')

@subscription_bp.route('/')
@login_required
def index():
    """Show user's subscription dashboard"""
    user_subscription = current_user.get_current_subscription()
    subscription_status = current_user.get_subscription_status()
    pending_bills = current_user.get_pending_bills()
    billing_history = BillingRecord.query.filter_by(user_id=current_user.id).order_by(BillingRecord.created_at.desc()).limit(10).all()
    
    return render_template('subscription/dashboard.html',
                         user_subscription=user_subscription,
                         subscription_status=subscription_status,
                         pending_bills=pending_bills,
                         billing_history=billing_history)

@subscription_bp.route('/plans')
@login_required
def plans():
    """Show available subscription plans"""
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.price).all()
    current_subscription = current_user.get_current_subscription()
    
    from app.forms import CSRFOnlyForm
    csrf_forms = [CSRFOnlyForm() for _ in plans]
    return render_template('subscription/plans.html',
                         plans=plans,
                         current_subscription=current_subscription,
                         csrf_forms=csrf_forms)

@subscription_bp.route('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def subscribe(plan_id):
    """Subscribe to a plan"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # Check if user already has an active subscription
    current_subscription = current_user.get_current_subscription()
    if current_subscription:
        flash('You already have an active subscription. Please wait for it to expire or contact admin.', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # For GET requests, show confirmation page
    if request.method == 'GET':
        return render_template('subscription/confirm.html', plan=plan)
    
    # For POST requests, process the subscription
    try:
        # Create new subscription
        subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=plan.id
        )
        db.session.add(subscription)
        db.session.flush()  # Get the subscription ID
        
        # Create billing record
        billing_record = BillingRecord(
            user_id=current_user.id,
            subscription_id=subscription.id,
            amount=plan.price,
            description=f'Subscription to {plan.name} plan',
            billing_type='subscription',
            due_date=datetime.utcnow() + timedelta(days=7)  # 7 days to pay
        )
        db.session.add(billing_record)
        db.session.commit()
        
        flash(f'Successfully subscribed to {plan.name} plan. Please complete payment to activate your subscription.', 'success')
        return redirect(url_for('subscription.billing', billing_id=billing_record.id))
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating subscription. Please try again.', 'error')
        current_app.logger.error(f'Subscription error: {str(e)}')
        return redirect(url_for('subscription.plans'))

@subscription_bp.route('/billing/<int:billing_id>')
@login_required
def billing(billing_id):
    """Show billing details and payment form"""
    billing_record = BillingRecord.query.filter_by(
        id=billing_id,
        user_id=current_user.id
    ).first_or_404()
    
    from app.forms import PaymentForm
    form = PaymentForm()
    return render_template('subscription/billing.html',
                         billing_record=billing_record,
                         form=form)

@subscription_bp.route('/pay/<int:billing_id>', methods=['POST'])
@login_required
def process_payment(billing_id):
    """Process payment for a billing record"""
    billing_record = BillingRecord.query.filter_by(
        id=billing_id,
        user_id=current_user.id,
        status='pending'
    ).first_or_404()
    
    payment_method = request.form.get('payment_method')
    transaction_ref = request.form.get('transaction_reference', '')
    
    if not payment_method:
        flash('Please select a payment method.', 'error')
        return redirect(url_for('subscription.billing', billing_id=billing_id))
    
    try:
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            billing_record_id=billing_record.id,
            amount=billing_record.amount,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed',  # In real system, this would be 'pending' until confirmed
            processed_at=datetime.utcnow()
        )
        db.session.add(payment)
        
        # Mark billing record as paid
        billing_record.mark_as_paid(payment_method, transaction_ref)
        
        # If this is a subscription payment, set status to pending approval
        if billing_record.subscription_id:
            subscription = UserSubscription.query.get(billing_record.subscription_id)
            if subscription:
                subscription.status = 'pending'
                subscription.is_active = False
                db.session.commit()
        flash('Payment processed successfully! Your subscription is pending admin approval.', 'info')
        return redirect(url_for('subscription.index'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error processing payment. Please try again.', 'error')
        current_app.logger.error(f'Payment error: {str(e)}')
        return redirect(url_for('subscription.billing', billing_id=billing_id))

@subscription_bp.route('/history')
@login_required
def billing_history():
    """Show user's billing history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = BillingRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(BillingRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    billing_records = pagination.items

    # Calculate summary totals
    from sqlalchemy import func
    total_paid = BillingRecord.query.filter_by(user_id=current_user.id, status='paid').with_entities(func.sum(BillingRecord.amount)).scalar() or 0
    total_pending = BillingRecord.query.filter_by(user_id=current_user.id, status='pending').with_entities(func.sum(BillingRecord.amount)).scalar() or 0
    total_overdue = BillingRecord.query.filter_by(user_id=current_user.id, status='overdue').with_entities(func.sum(BillingRecord.amount)).scalar() or 0
    summary = type('Summary', (), {})()
    summary.total_paid = total_paid
    summary.total_pending = total_pending
    summary.total_overdue = total_overdue

    return render_template('subscription/history.html',
                         billing_records=billing_records,
                         pagination=pagination,
                         summary=summary)

@subscription_bp.route('/cancel', methods=['GET', 'POST'])
@login_required
def cancel_subscription():
    """Cancel current subscription (at end of period)"""
    subscription = current_user.get_current_subscription()
    if not subscription:
        flash('No active subscription to cancel.', 'warning')
        return redirect(url_for('subscription.index'))
    
    # Show confirmation page for GET requests
    if request.method == 'GET':
        return render_template('subscription/cancel_confirm.html', 
                             subscription=subscription)
    
    try:
        subscription.auto_renew = False
        db.session.commit()
        
        flash('Subscription cancelled. It will remain active until the end date.', 'info')
        return redirect(url_for('subscription.index'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error cancelling subscription. Please try again.', 'error')
        current_app.logger.error(f'Cancellation error: {str(e)}')
        return redirect(url_for('subscription.index'))

@subscription_bp.route('/renew', methods=['GET', 'POST'])
@login_required
def renew_subscription():
    """Renew current subscription"""
    current_subscription = current_user.get_current_subscription()
    if not current_subscription:
        flash('No subscription to renew.', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Show confirmation page for GET requests
    if request.method == 'GET':
        return render_template('subscription/renew_confirm.html', 
                             subscription=current_subscription)
    
    try:
        # Create new subscription starting from current end date
        new_subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=current_subscription.plan_id,
            start_date=current_subscription.end_date
        )
        db.session.add(new_subscription)
        db.session.flush()
        
        # Create billing record
        billing_record = BillingRecord(
            user_id=current_user.id,
            subscription_id=new_subscription.id,
            amount=current_subscription.plan.price,
            description=f'Renewal of {current_subscription.plan.name} plan',
            billing_type='subscription',
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(billing_record)
        db.session.commit()
        
        flash('Subscription renewal created. Please complete payment.', 'success')
        return redirect(url_for('subscription.billing', billing_id=billing_record.id))
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating renewal. Please try again.', 'error')
        current_app.logger.error(f'Renewal error: {str(e)}')
        return redirect(url_for('subscription.index'))

# API endpoints for AJAX requests
@subscription_bp.route('/api/status')
@login_required
def api_subscription_status():
    """API endpoint to get subscription status"""
    status = current_user.get_subscription_status()
    return jsonify(status)

@subscription_bp.route('/api/billing-summary')
@login_required
def api_billing_summary():
    """API endpoint to get billing summary"""
    pending_amount = current_user.get_total_outstanding_amount()
    pending_count = len(current_user.get_pending_bills())
    
    return jsonify({
        'pending_amount': float(pending_amount),
        'pending_count': pending_count,
        'currency': 'LSL'  # Lesotho Loti
    })

# Utility functions for subscription management
def create_automatic_renewal_bill(user_id, expired_subscription):
    """Create an automatic renewal bill when subscription expires"""
    try:
        # Check if renewal bill already exists
        existing_bill = BillingRecord.query.filter_by(
            user_id=user_id,
            subscription_id=expired_subscription.id,
            billing_type='subscription',
            status='pending'
        ).first()
        
        if existing_bill:
            return existing_bill
        
        # Create new subscription for renewal
        new_subscription = UserSubscription(
            user_id=user_id,
            plan_id=expired_subscription.plan_id,
            start_date=expired_subscription.end_date,  # Start from expiry date
            is_active=False  # Will be activated when paid
        )
        db.session.add(new_subscription)
        db.session.flush()  # Get subscription ID
        
        # Create billing record for renewal
        billing_record = BillingRecord(
            user_id=user_id,
            subscription_id=new_subscription.id,
            amount=expired_subscription.plan.price,
            description=f'Automatic renewal of {expired_subscription.plan.name} plan',
            billing_type='subscription',
            due_date=datetime.utcnow() + timedelta(days=30)  # 30 days to pay
        )
        db.session.add(billing_record)
        db.session.commit()
        
        return billing_record
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating automatic renewal bill: {str(e)}')
        return None

@subscription_bp.route('/api/check-expired-subscriptions', methods=['POST'])
def check_expired_subscriptions():
    """API endpoint to check and handle expired subscriptions (for admin/cron jobs)"""
    try:
        # Find subscriptions that expired in the last 7 days but don't have renewal bills
        expired_subscriptions = UserSubscription.query.filter(
            UserSubscription.end_date <= datetime.utcnow(),
            UserSubscription.end_date >= datetime.utcnow() - timedelta(days=7),
            UserSubscription.is_active == True
        ).all()
        
        renewal_bills_created = 0
        
        for subscription in expired_subscriptions:
            # Skip admin users
            user = User.query.get(subscription.user_id)
            if user and user.is_admin():
                continue
            
            # Mark subscription as inactive
            subscription.is_active = False
            
            # Create automatic renewal bill
            renewal_bill = create_automatic_renewal_bill(subscription.user_id, subscription)
            if renewal_bill:
                renewal_bills_created += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'expired_subscriptions': len(expired_subscriptions),
            'renewal_bills_created': renewal_bills_created
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })