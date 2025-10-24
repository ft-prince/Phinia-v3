from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    if dictionary:
        return dictionary.get(key)
    return None

@register.filter
def selectattr(items, attr_value):
    """Filter items by attribute value"""
    attr, value = attr_value.split(',', 1)
    return [item for item in items if str(getattr(item, attr)) == value]






@register.filter
def get_field_value(form_data, field_id):
    """
    Get field value from POST data by field ID.
    Usage: {{ form_data|get_field_value:field.id }}
    """
    if form_data is None:
        return ''
    key = f'field_{field_id}'
    return form_data.get(key, '')


@register.filter
def get_status_value(form_data, field_id):
    """
    Get status value from POST data by field ID.
    Usage: {{ form_data|get_status_value:field.id }}
    """
    if form_data is None:
        return ''
    key = f'status_{field_id}'
    return form_data.get(key, '')


@register.filter
def get_comment_value(form_data, field_id):
    """
    Get comment value from POST data by field ID.
    Usage: {{ form_data|get_comment_value:field.id }}
    """
    if form_data is None:
        return ''
    key = f'comment_{field_id}'
    return form_data.get(key, '')
