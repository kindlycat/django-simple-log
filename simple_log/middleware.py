# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from threading import local

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # Django < 1.10
    MiddlewareMixin = object


_thread_locals = local()


class ThreadLocalMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_locals.request = request
