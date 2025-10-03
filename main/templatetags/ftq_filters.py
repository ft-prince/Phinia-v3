from django import template
from decimal import Decimal

register = template.Library()

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