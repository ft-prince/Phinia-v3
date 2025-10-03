# main/templatetags/custom_tags.py

from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculates percentage"""
    try:
        return round((float(value) / float(total)) * 100)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    

@register.filter
def percentage(value, total):
    """Calculate percentage of value relative to total"""
    try:
        if total == 0:
            return 0
        return (value / total) * 100
    except (ValueError, ZeroDivisionError, TypeError):
        return 0    
    
        
@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def status_class(status):
    status_classes = {
        'pending': 'bg-warning',
        'supervisor_approved': 'bg-info',
        'quality_approved': 'bg-success',
        'rejected': 'bg-danger'
    }
    return status_classes.get(status, 'bg-secondary')

@register.filter
def add_multiply(value, arg):
    """Add value and arg, then multiply by 21."""
    try:
        return (float(value) + float(arg)) * 21
    except (ValueError, TypeError):
        return 0
    
    
@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0    
@register.filter
def timedelta_format(td):
    if not isinstance(td, timedelta):
        return ""
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@register.filter
def divisibleby(queryset, verifier_type):
    """Filter verifications by verifier type"""
    return queryset.filter(verifier_type=verifier_type).first()




@register.filter(name='absolute')
def absolute(value):
    """Return the absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='negative_to_positive')
def negative_to_positive(value):
    """Convert negative value to positive, keep positive as is"""
    try:
        val = float(value)
        if val < 0:
            return -val
        return val
    except (ValueError, TypeError):
        return value
    
from decimal import Decimal
    
@register.filter
def getattribute(obj, attr):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(obj, str(attr)):
        return getattr(obj, attr)
    elif hasattr(obj, 'fields') and attr in obj.fields:
        return obj[attr]
    return None
    
@register.filter(name='absolute')
def absolute(value):
    """Return the absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='negative_to_positive')
def negative_to_positive(value):
    """Convert negative value to positive, keep positive as is"""
    try:
        val = float(value)
        if val < 0:
            return -val
        return val
    except (ValueError, TypeError):
        return value    
    
    
    