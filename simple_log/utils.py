# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.apps import apps as django_apps

from .middleware import _thread_locals
from . import settings


__all__ = ['get_simple_log_model', 'get_current_user', 'get_current_request',
           'get_serializer']

registered_models = []


@lru_cache.lru_cache(maxsize=None)
def get_simple_log_model():
    try:
        return django_apps.get_model(settings.SIMPLE_LOG_MODEL)
    except ValueError:
        raise ImproperlyConfigured("SIMPLE_LOG_MODEL must be of the form "
                                   "'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SIMPLE_LOG_MODEL refers to model '%s' "
            "that has not been installed" % settings.SIMPLE_LOG_MODEL
        )


@lru_cache.lru_cache(maxsize=None)
def get_serializer():
    return import_string(settings.MODEL_SERIALIZER)


def get_current_request_default():
    return getattr(_thread_locals, 'request', None)


@lru_cache.lru_cache(maxsize=None)
def _get_current_request():
    return import_string(settings.GET_CURRENT_REQUEST)

get_current_request = _get_current_request()


def get_current_user():
    request = get_current_request()
    if request:
        return getattr(request, 'user', None)


@lru_cache.lru_cache()
def get_fields(klass):
    fields = klass._meta.get_fields()
    if hasattr(klass, 'simple_log_fields'):
        fields = [f for f in fields if f.name in klass.simple_log_fields]
    elif hasattr(klass, 'simple_log_exclude_fields'):
        fields = [f for f in fields
                  if f.name not in klass.simple_log_exclude_fields]
    else:
        fields = [f for f in fields
                  if f.name not in settings.EXCLUDE_FIELD_LIST]
    return [f for f in fields if f.concrete]


@lru_cache.lru_cache(maxsize=None)
def get_models_for_log():
    if registered_models:
        return registered_models
    all_models = [m for m in django_apps.get_models()
                  if m._meta.label != settings.SIMPLE_LOG_MODEL]
    if settings.MODEL_LIST:
        return [m for m in all_models if m._meta.label in settings.MODEL_LIST]
    if settings.EXCLUDE_MODEL_LIST:
        return [m for m in all_models
                if m._meta.label not in settings.EXCLUDE_MODEL_LIST]
    return all_models


def str_or_none(value):
    return None if value is None else force_text(value)
