# Create this file as: your_app/templatetags/ep_filters.py

from django import template
from datetime import timedelta
from django.utils import timezone

register = template.Library()

@register.filter
def has_recent_changes(mechanism_status, hours=24):
    """Check if mechanism status has been changed in the last N hours (excluding creation)"""
    if not mechanism_status:
        return False
    
    cutoff_time = timezone.now() - timedelta(hours=hours)
    recent_changes = mechanism_status.history.exclude(field_name='created').filter(
        timestamp__gte=cutoff_time
    )
    return recent_changes.exists()

@register.filter
def get_last_change_time(mechanism_status):
    """Get the timestamp of the last actual change (excluding creation)"""
    if not mechanism_status:
        return None
    
    last_change = mechanism_status.history.exclude(field_name='created').first()
    return last_change.timestamp if last_change else None

@register.filter
def has_any_changes(mechanism_status):
    """Check if mechanism status has any changes (excluding creation)"""
    if not mechanism_status:
        return False
    
    return mechanism_status.history.exclude(field_name='created').exists()

@register.filter
def get_change_count(mechanism_status):
    """Get the number of changes made to a mechanism status (excluding creation)"""
    if not mechanism_status:
        return 0
    
    return mechanism_status.history.exclude(field_name='created').count()

@register.filter
def get_latest_changes(mechanism_status, field_name=None):
    """Get the latest changes for a specific field or all fields"""
    if not mechanism_status:
        return []
    
    changes = mechanism_status.history.exclude(field_name='created')
    
    if field_name:
        changes = changes.filter(field_name=field_name)
    
    return changes[:5]  # Return last 5 changes