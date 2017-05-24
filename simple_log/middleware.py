# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # Django < 1.10
    MiddlewareMixin = object

from simple_log.utils import set_thread_variable


class ThreadLocalMiddleware(MiddlewareMixin):
    def process_request(self, request):
        set_thread_variable('request', request)
