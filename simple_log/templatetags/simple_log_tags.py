from django.template import Library
from django.utils.encoding import force_text


register = Library()


@register.simple_tag()
def get_type(value):
    if isinstance(value, str):
        return 'str'
    if value is None:
        return 'None'
    if isinstance(value, dict):
        return 'dict'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, list):
        return 'list'
    if isinstance(value, int):
        return 'int'
    return force_text(type(value))
