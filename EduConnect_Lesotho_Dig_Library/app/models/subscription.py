from datetime import datetime, timedelta
from app import db
from sqlalchemy import func, Numeric

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    price = db.Column(Numeric(10, 2), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)  # Duration in days
    max_books = db.Column(db.Integer, nullable=False, default=1)  # Max books that can be borrowed at once
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'duration_days': self.duration_days,
            'max_books': self.max_books,
            'is_active': self.is_active
        }

class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    auto_renew = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, user_id, plan_id, start_date=None):
        self.user_id = user_id
        self.plan_id = plan_id
        if start_date:
            self.start_date = start_date
        else:
            self.start_date = datetime.utcnow()
        
        # Calculate end date based on plan duration
        plan = SubscriptionPlan.query.get(plan_id)
        if plan:
            self.end_date = self.start_date + timedelta(days=plan.duration_days)
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.end_date
    
    @property
    def days_remaining(self):
        if self.is_expired:
            return 0
        return (self.end_date - datetime.utcnow()).days
    
    def __repr__(self):
        return f'<UserSubscription user_id={self.user_id} plan_id={self.plan_id}>'

class BillingRecord(db.Model):
    __tablename__ = 'billing_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'), nullable=True)
    amount = db.Column(Numeric(10, 2), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    billing_type = db.Column(db.String(50), nullable=False)  # 'subscription', 'late_fee', 'damage_fee'
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'paid', 'overdue', 'cancelled'
    due_date = db.Column(db.DateTime, nullable=False)
    paid_date = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))  # 'cash', 'card', 'mobile_money', 'bank_transfer'
    transaction_reference = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='billing_records')
    subscription = db.relationship('UserSubscription', backref='billing_records')
    
    @property
    def is_overdue(self):
        return self.status == 'pending' and datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (datetime.utcnow() - self.due_date).days
    
    def mark_as_paid(self, payment_method, transaction_ref=None):
        self.status = 'paid'
        self.paid_date = datetime.utcnow()
        self.payment_method = payment_method
        if transaction_ref:
            self.transaction_reference = transaction_ref
        db.session.commit()
    
    def __repr__(self):
        return f'<BillingRecord user_id={self.user_id} amount={self.amount} status={self.status}>'

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    billing_record_id = db.Column(db.Integer, db.ForeignKey('billing_records.id'), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_reference = db.Column(db.String(100))
    payment_status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    gateway_response = db.Column(db.Text)  # Store gateway response for debugging
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payments')
    billing_record = db.relationship('BillingRecord', backref='payments')
    
    def __repr__(self):
        return f'<Payment user_id={self.user_id} amount={self.amount} status={self.payment_status}>'