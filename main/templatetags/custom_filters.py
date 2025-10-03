from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    try:
        return round((value / total) * 100, 1) if total > 0 else 0
    except (ValueError, ZeroDivisionError):
        return 0
    
    
