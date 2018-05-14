# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # Django < 1.10
    MiddlewareMixin = object

from simple_log.utils import set_thread_variable, del_thread_variable


class ThreadLocalMiddleware(MiddlewareMixin):
    def process_request(self, request):
        set_thread_variable('request', request)

    def process_response(self, request, response):
        del_thread_variable('request')
        return response

    def process_exception(self, request, exception):
        del_thread_variable('request')
