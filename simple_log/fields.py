# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import ManyToManyField


class SimpleManyToManyField(ManyToManyField):
    def deconstruct(self):
        name, path, args, kwargs = super(SimpleManyToManyField, self)\
            .deconstruct()
        kwargs['to'] = 'self'
        return name, path, args, kwargs
