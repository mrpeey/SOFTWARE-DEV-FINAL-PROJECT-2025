
from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, BooleanField, DecimalField, IntegerField, TextAreaField
from wtforms.validators import DataRequired

class SubscriptionPlanForm(FlaskForm):
    name = StringField('Plan Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    price = DecimalField('Price (LSL)', validators=[DataRequired()])
    duration_days = IntegerField('Duration (Days)', validators=[DataRequired()])
    max_books = IntegerField('Maximum Books', validators=[DataRequired()])
    is_active = BooleanField('Active')

class PaymentForm(FlaskForm):
    payment_method = RadioField('Payment Method', choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card')], validators=[DataRequired()])
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired()])
    agree_terms = BooleanField('Agree to Terms', validators=[DataRequired()])

class CSRFOnlyForm(FlaskForm):
    pass
