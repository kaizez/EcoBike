from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp, NumberRange
from wtforms import Form, StringField, RadioField, SelectField, TextAreaField, validators, DecimalField, FileField, IntegerField
from wtforms.fields import EmailField, DateField
from datetime import datetime
import email_validator
import re
import requests
import shelve
from flask import current_app

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(message="email is required"), Email(message="Please enter a valid email")])
    password = PasswordField('Password', validators=[DataRequired(message="password is required")])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="email is required"),
        Email(message="Please enter a valid email")
    ])
    username = StringField('Username', validators=[
        DataRequired(message="username is required"),
        Length(min=3, max=20, message="Username must be between 3 and 20 characters")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="password is required")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="password is required"),
        EqualTo('password', message="Passwords must match")
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        if not username.data.isalnum():
            raise ValidationError("Username can only contain letters and numbers")

class EditUsernameForm(FlaskForm):
    username = StringField('New Username', validators=[
        DataRequired(),
        Length(min=3, max=20, message="Username must be between 3 and 20 characters")
    ])
    submit = SubmitField('Update Username')

    def validate_username(self, username):
        if not username.data.isalnum():
            raise ValidationError("Username can only contain letters and numbers")


class NumberOnlyValidator(object):
    def __init__(self, message=None):
        if not message:
            message = 'Please enter numbers only'
        self.message = message

    def __call__(self, form, field):
        if not field.data.isdigit():
            raise validators.ValidationError(self.message)

class FutureDateValidator:
    def __init__(self, message=None):
        if not message:
            message = 'Date cannot be in the future'
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data > datetime.now().date():
            raise validators.ValidationError(self.message)

class CreateDefectForm(Form):
    bike_id = StringField('Bike ID', [
        validators.DataRequired(),
        validators.Length(min=1, max=20)
    ])

    defect_type = SelectField('Defect type',
                              [validators.DataRequired()],
                              choices=[('', 'Select'), ('New', 'New Defect'), ('Old', 'Old Defect')],
                              default='')

    date_found = DateField('Date Found',
                           format='%Y-%m-%d',
                           validators=[
                               validators.DataRequired(message="Date is required"),
                               FutureDateValidator()
                           ])

    bike_location = TextAreaField('Location of Bike', [
        validators.Length(max=200),
        validators.DataRequired(message="Please enter a location."),
    ])

    severity = RadioField('Severity',
                          choices=[('V', 'Very Serious'),
                                   ('S', 'Serious'),
                                   ('N', 'Normal'),
                                   ('L', 'Less Serious'),
                                   ('X', 'Not so serious')],
                          default='N')

    description = TextAreaField('Description',
                                [validators.DataRequired()])

    def validate_bike_location(self, field):
        address = field.data
        api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')  # Ensure the API key is configured

        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": api_key}
        )
        data = response.json()
        print(response.json())
        if response.status_code != 200 or data.get('status') != 'OK':
            raise ValidationError("Invalid address. Please enter a valid location in Singapore.")

        # Ensure the address is in Singapore
        if not any("Singapore" in comp.get('long_name', '') for result in data['results'] for comp in
                   result.get('address_components', [])):
            raise ValidationError("Location must be in Singapore. Please enter a valid Singapore address.")

    def validate_bike_id(self, field):
        bike_id = field.data
        try:
            with shelve.open('bike_ids.db', 'r') as db:
                bike_ids = db.get('bike_ids', {})
                if bike_id not in bike_ids:
                    raise ValidationError("Bike ID does not exist. Please enter a valid Bike ID.")
        except Exception as e:
            raise ValidationError("Bike ID does not exist. Please enter a valid Bike ID.")


class UpdateDefectForm(Form):
    status = SelectField('Status',
                         [validators.DataRequired()],
                         choices=[('Pending', 'Pending'),
                                  ('Repaired', 'Repaired'),
                                  ('Closed', 'Closed')],
                         default='Pending')
    
class DateSelectionForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Proceed to Payment') #Submit button redirects to payment

class PaymentForm(FlaskForm):
    # Shipping/Billing Info
    full_name = StringField('Full Name', 
                          validators=[DataRequired(message="Please enter your full name")])
    email = StringField('Email', 
                       validators=[DataRequired(message="Please enter your email"),
                                 Email(message="Please enter a valid email address")])
    address = StringField('Address', 
                         validators=[DataRequired(message="Please enter your address")])
    city = StringField('City', 
                      validators=[DataRequired(message="Please enter your city")])
    postal_code = StringField('Postal Code', 
                            validators=[DataRequired(message="Please enter your postal code"),
                                      Regexp('^[0-9]{6}$', message="Postal code must be 6 digits")])
    
    # Payment Info
    def validate_card_number(form, field):
        # Remove any spaces from the card number
        number = field.data.replace(' ', '')
        if not number.isdigit():
            raise ValidationError("Card number must contain only digits")
        if len(number) != 16:
            raise ValidationError("Card number must be 16 digits")
    
    card_no = StringField('Card Number', 
                         validators=[DataRequired(message="Please enter your card number"),
                                   validate_card_number])
    
    cvv = StringField('CVV', 
                     validators=[DataRequired(message="Please enter the CVV"),
                               Regexp('^[0-9]{3,4}$', message="CVV must be 3 or 4 digits")])
    
    def validate_exp_date(form, field):
        if not field.data:
            raise ValidationError("Please enter the expiration date")
        # Remove any spaces from the expiration date
        exp = field.data.replace(' ', '')
        if not re.match('^(0[1-9]|1[0-2])/([0-9]{2})$', exp):
            raise ValidationError("Expiration date must be in MM/YY format")
    
    exp_date = StringField('Expiration Date', 
                          validators=[DataRequired(message="Please enter the expiration date"),
                                    validate_exp_date])
    
    submit = SubmitField('Place Order')
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    
    
class LockUnlockForm(FlaskForm):
    bike_id = StringField('Bike ID', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
class BikeIDManagementForm(FlaskForm):
    id_string = StringField(
        'Bike ID',
        validators=[DataRequired(message="Bike ID is required.")],
    )
    bike_name = StringField(
        'Bike Name',
        validators=[DataRequired(message="Bike Name is required.")],
    )
    stock_quantity = IntegerField(
        'Stock Quantity',
        validators=[
            DataRequired(message="Stock Quantity is required."),
            NumberRange(min=1, message="Stock must be at least 1."),
        ],
    )
    submit = SubmitField('Add/Update Bike ID')


    
class CreateBikeForm(Form):

    bike_name = StringField("Bike Name: ", [validators.Length(min=1, max=50), validators.DataRequired()])
    upload_bike_image = FileField("Bike Upload: ", )
    price = DecimalField("Price $: ", [validators.NumberRange(min=1, message="Price must be greater than 0"), validators.DataRequired()])
    transmission_type = SelectField("Transmission Type: ", choices=[("Manual", "Manual"), ("Automatic", "Automatic")], validators=[validators.DataRequired()])
    seating_capacity = SelectField("Seating Capacity: ", choices=[("1", "1 Seat"), ("2", "2 Seats")], default="1", validators=[validators.DataRequired()])
    engine_output = StringField("Engine Output (W): ", [validators.DataRequired()])
    stock_quantity = IntegerField('Stock Quantity', validators=[validators.DataRequired(), validators.NumberRange(min=0)])

class CreateFAQForm(Form):
    question = StringField('Question', [validators.Length(min=1, max=150), validators.DataRequired()])
    answer = TextAreaField('Answer', [validators.Length(min=1), validators.DataRequired()])

class UpdateFAQForm(Form):
    question = StringField('Question', [validators.Length(min=1, max=150), validators.DataRequired()])
    answer = TextAreaField('Answer', [validators.Length(min=1), validators.DataRequired()])