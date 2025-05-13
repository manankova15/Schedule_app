from django import template

register = template.Library()

@register.filter
def split(value, arg):
    if not value:
        return []
    return value.split(arg)

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key, [])