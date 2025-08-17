from django import template

register = template.Library()

@register.filter
def consumption_type_display(value):
    types = {
        'market': 'Market',
        'food': 'Food',
        'other': 'Other',
    }
    return types.get(value, value.capitalize())