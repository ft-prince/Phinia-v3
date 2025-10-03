# history_utils.py
from django.utils import timezone
from .models import ErrorPreventionCheckHistory, ErrorPreventionMechanismHistory

def track_ep_check_changes(original, updated, user):
    """Track changes made to EP check main fields"""
    if not user:
        return  # Skip if no user provided
    
    # Track field changes
    fields_to_track = ['status', 'comments', 'current_model']
    
    for field in fields_to_track:
        old_value = getattr(original, field, None)
        new_value = getattr(updated, field, None)
        
        if old_value != new_value:
            # Determine action type
            if field == 'status':
                if new_value == 'supervisor_approved':
                    action = 'supervisor_verified'
                elif new_value == 'quality_approved':
                    action = 'quality_verified'
                elif new_value == 'rejected':
                    action = 'rejected'
                else:
                    action = 'status_changed'
            else:
                action = 'updated'
            
            # Create human-readable description
            description = create_change_description(field, old_value, new_value)
            
            ErrorPreventionCheckHistory.objects.create(
                ep_check=updated,
                changed_by=user,
                action=action,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                description=description
            )

def track_mechanism_changes(original, updated, user):
    """Track changes made to mechanism status fields"""
    if not user:
        return  # Skip if no user provided
    
    # Track field changes - only create history for fields that actually changed
    fields_to_track = ['status', 'is_working', 'is_not_applicable', 'alternative_method', 'comments']
    
    changes_made = False
    for field in fields_to_track:
        old_value = getattr(original, field, None)
        new_value = getattr(updated, field, None)
        
        # Only create history entry if the value actually changed
        if old_value != new_value:
            ErrorPreventionMechanismHistory.objects.create(
                mechanism_status=updated,
                changed_by=user,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None
            )
            changes_made = True
    
    return changes_made

def create_change_description(field_name, old_value, new_value):
    """Create human-readable change descriptions"""
    field_labels = {
        'status': 'Status',
        'comments': 'Comments',
        'current_model': 'Current Model',
        'is_working': 'Working Status',
        'is_not_applicable': 'N/A Status',
        'alternative_method': 'Alternative Method'
    }
    
    field_label = field_labels.get(field_name, field_name.replace('_', ' ').title())
    
    if field_name == 'status':
        status_labels = {
            'pending': 'Pending',
            'supervisor_approved': 'Supervisor Approved',
            'quality_approved': 'Quality Approved',
            'rejected': 'Rejected'
        }
        old_display = status_labels.get(old_value, old_value)
        new_display = status_labels.get(new_value, new_value)
        return f"{field_label} changed from '{old_display}' to '{new_display}'"
    
    elif field_name in ['is_working', 'is_not_applicable']:
        old_display = 'Yes' if old_value else 'No'
        new_display = 'Yes' if new_value else 'No'
        return f"{field_label} changed from '{old_display}' to '{new_display}'"
    
    else:
        old_display = old_value if old_value else '(empty)'
        new_display = new_value if new_value else '(empty)'
        return f"{field_label} changed from '{old_display}' to '{new_display}'"

def create_initial_history(ep_check, user):
    """Create initial history entry when EP check is created"""
    ErrorPreventionCheckHistory.objects.create(
        ep_check=ep_check,
        changed_by=user,
        action='created',
        description=f"EP Check created for {ep_check.date}"
    )

def get_mechanism_change_summary(mechanism_status, days=7):
    """Get a summary of changes for a mechanism in the last N days"""
    from datetime import timedelta
    since_date = timezone.now() - timedelta(days=days)
    
    changes = mechanism_status.history.filter(timestamp__gte=since_date)
    
    summary = []
    for change in changes:
        if change.field_name == 'status':
            summary.append({
                'field': 'Status',
                'old': change.old_value,
                'new': change.new_value,
                'user': change.changed_by.username,
                'time': change.timestamp
            })
    
    return summary

def get_ep_check_timeline(ep_check):
    """Get complete timeline of changes for an EP check"""
    timeline = []
    
    # Get EP check level changes
    ep_changes = ep_check.history.all()
    for change in ep_changes:
        timeline.append({
            'type': 'ep_check',
            'action': change.action,
            'description': change.description or f"{change.field_name} changed",
            'user': change.changed_by.username,
            'timestamp': change.timestamp,
            'details': {
                'field': change.field_name,
                'old_value': change.old_value,
                'new_value': change.new_value
            }
        })
    
    # Get mechanism level changes - EXCLUDE creation records
    for mechanism in ep_check.mechanism_statuses.all():
        mech_changes = mechanism.history.exclude(field_name='created').all()  # Exclude creation records
        for change in mech_changes:
            # Create better description based on field changed
            field_descriptions = {
                'status': f"Status changed from '{change.old_value}' to '{change.new_value}'",
                'is_working': f"Working status changed from '{change.old_value}' to '{change.new_value}'",
                'is_not_applicable': f"N/A status changed from '{change.old_value}' to '{change.new_value}'",
                'alternative_method': f"Alternative method updated",
                'comments': f"Comments updated"
            }
            
            description = field_descriptions.get(
                change.field_name, 
                f"{change.field_name} changed"
            )
            
            timeline.append({
                'type': 'mechanism',
                'mechanism_id': mechanism.ep_mechanism_id,
                'mechanism_display': mechanism.get_ep_mechanism_id_display(),
                'description': description,
                'user': change.changed_by.username,
                'timestamp': change.timestamp,
                'details': {
                    'field': change.field_name,
                    'old_value': change.old_value,
                    'new_value': change.new_value
                }
            })
    
    # Sort by timestamp (newest first)
    timeline.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return timeline