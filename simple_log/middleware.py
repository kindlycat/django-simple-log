# -*- coding: utf-8 -*-
from threading import local

_thread_locals = local()


class ThreadLocalMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        return self.get_response(request)
