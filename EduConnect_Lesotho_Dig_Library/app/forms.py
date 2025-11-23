from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, BooleanField
from wtforms.validators import DataRequired

class PaymentForm(FlaskForm):
    payment_method = RadioField('Payment Method', choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card')], validators=[DataRequired()])
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired()])
    agree_terms = BooleanField('Agree to Terms', validators=[DataRequired()])
from flask_wtf import FlaskForm

class CSRFOnlyForm(FlaskForm):
    pass
