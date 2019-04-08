# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.template import Library
from django.utils.encoding import force_text


register = Library()


try:
    assignment = register.assignment_tag
except AttributeError:
    # In django==2.0 use simple_tag
    assignment = register.simple_tag


@assignment()
def get_type(value):
    if isinstance(value, six.string_types):
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
