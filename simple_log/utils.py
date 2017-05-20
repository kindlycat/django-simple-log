# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager
from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils.encoding import force_text
from django.utils.module_loading import import_string

from simple_log.conf import settings
from simple_log import middleware

__all__ = ['get_log_model', 'get_current_user', 'get_current_request',
           'get_serializer', 'disable_logging', 'get_models_for_log']

registered_models = {}


def check_log_model(model):
    from simple_log.models import SimpleLogAbstract
    if not issubclass(model, SimpleLogAbstract):
        raise ImproperlyConfigured('Log model should be subclass of '
                                   'SimpleLogAbstract.')
    return model


@lru_cache.lru_cache(maxsize=None)
def get_log_model(model=None):
    if model and registered_models.get(model):
        return check_log_model(registered_models[model])
    try:
        return check_log_model(django_apps.get_model(settings.MODEL))
    except (ValueError, AttributeError):
        raise ImproperlyConfigured("SIMPLE_LOG_MODEL must be of the form "
                                   "'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SIMPLE_LOG_MODEL refers to model '%s' "
            "that has not been installed" % settings.MODEL
        )


@lru_cache.lru_cache(maxsize=None)
def get_serializer():
    return import_string(settings.MODEL_SERIALIZER)


def get_current_request_default():
    return getattr(middleware._thread_locals, 'request', None)


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


def get_label(m):
    try:
        return m._meta.label
    except AttributeError:
        return '{}.{}'.format(m._meta.app_label, m._meta.object_name)


@lru_cache.lru_cache(maxsize=None)
def get_models_for_log():
    if registered_models:
        return list(registered_models.keys())
    from simple_log.models import SimpleLogAbstract
    all_models = [m for m in django_apps.get_models()
                  if not issubclass(m, SimpleLogAbstract)]
    if settings.MODEL_LIST:
        return [m for m in all_models if get_label(m) in settings.MODEL_LIST]
    if settings.EXCLUDE_MODEL_LIST:
        return [m for m in all_models
                if get_label(m) not in settings.EXCLUDE_MODEL_LIST]
    return all_models


def str_or_none(value):
    return None if value is None else force_text(value)


def need_to_log(model):
    disabled = getattr(middleware._thread_locals, 'disable_logging', False)
    return model in get_models_for_log() and not disabled


@contextmanager
def disable_logging():
    middleware._thread_locals.disable_logging = True
    try:
        yield
    finally:
        delattr(middleware._thread_locals, 'disable_logging')
