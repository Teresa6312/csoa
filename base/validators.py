import json
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import RegexValidator

def validate_json(value):
    try:
        json.loads(value)
    except json.JSONDecodeError:
        raise ValidationError( 'Invalid JSON string.')

def validate_today_and_before(value):
    if value > timezone.now().date():
        raise ValidationError('The date must be today or before.')

def validate_today_and_after(value):
    if value < timezone.now().date():
        raise ValidationError('The date must be today or after.')
    

def get_validator(key):
    if key == 'validate_today_and_before':
        return validate_today_and_before
    elif key == 'validate_today_and_after':
        return validate_today_and_after
    elif VALIDATOR[key] is not None:
        return RegexValidator(regex=VALIDATOR[key]['regex'], message=VALIDATOR[key]['message'])
    raise ValueError('Invalid validator key or missing regex')
    
VALIDATOR = {
    'phone_regex' : { 'regex': r'^\d{3}-\d{3}-\d{4}$', 'message': "Invalid phone number format. Enter as 000-000-0000." },
    'number_str': { 'regex': r'^\d+$', 'message': "Invalid input, only number is allowed" },
    'number_str_0_8': { 'regex': r'^0\d{7}$', 'message': "8-digit number, start with 0" },
    'no_space_str_w_-': {'regex':r'^[a-zA-Z][a-zA-Z0-9_]*$', 'message': "Start with letters, and only accepts letters (a-z, A-Z), numbers (0-9), dashes (-), and underscores (_)." },
    'no_space_str_w_': {'regex':r'^[a-zA-Z][a-zA-Z0-9_]*$', 'message': "Start with letters, and only accepts letters (a-z, A-Z), numbers (0-9), and underscores (_)." }
}