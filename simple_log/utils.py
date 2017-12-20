# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from threading import local

from contextlib import contextmanager
from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache, six
from django.utils.encoding import force_text
from django.utils.module_loading import import_string

from simple_log.conf import settings

__all__ = ['set_thread_variable', 'get_thread_variable', 'del_thread_variable',
           'get_log_model', 'get_current_user', 'get_current_request',
           'get_serializer', 'disable_logging', 'get_model_list',
           'disable_related', 'get_obj_repr', 'is_related_to']


_thread_locals = local()


def set_thread_variable(key, val):
    setattr(_thread_locals, key, val)


def get_thread_variable(key, default=None):
    return getattr(_thread_locals, key, default)


def del_thread_variable(key):
    if hasattr(_thread_locals, key):
        return delattr(_thread_locals, key)


def check_log_model(model):
    from simple_log.models import SimpleLogAbstractBase
    if not issubclass(model, SimpleLogAbstractBase):
        raise ImproperlyConfigured('Log model should be subclass of '
                                   'SimpleLogAbstract.')
    return model


@lru_cache.lru_cache()
def get_log_model():
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
def get_serializer(model=None):
    if hasattr(model, 'simple_log_serializer'):
        serializer = model.simple_log_serializer
    else:
        serializer = settings.MODEL_SERIALIZER
    if isinstance(serializer, six.string_types):
        return import_string(serializer)
    return serializer


def get_current_request_default():
    return get_thread_variable('request')


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
    return [f for f in fields if f.concrete or
            (settings.SAVE_ONE_TO_MANY and f.one_to_many and f.related_name)]


def get_label(m):
    try:
        return m._meta.label
    except AttributeError:
        return '{}.{}'.format(m._meta.app_label, m._meta.object_name)


@lru_cache.lru_cache(maxsize=None)
def get_model_list():
    from simple_log.models import SimpleLogAbstractBase
    model_list = [m for m in django_apps.get_models()
                  if not issubclass(m, SimpleLogAbstractBase)]
    if settings.MODEL_LIST:
        model_list = [m for m in model_list
                      if get_label(m) in settings.MODEL_LIST]
    if settings.EXCLUDE_MODEL_LIST:
        model_list = [m for m in model_list
                      if get_label(m) not in settings.EXCLUDE_MODEL_LIST]
    return model_list


def is_related_to(instance, to_instance):
    if instance == to_instance:
        return False
    old_instance = getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
    to_instance_pk = to_instance.pk
    if not to_instance_pk:
        # If deleted
        old_to_instance = getattr(to_instance, settings.OLD_INSTANCE_ATTR_NAME, None)
        to_instance_pk = getattr(old_to_instance, 'pk', None)
    for field in [x for x in instance._meta.get_fields()
                  if x.related_model == to_instance.__class__ and x.concrete]:
        if getattr(instance, field.attname) == to_instance_pk or \
              getattr(old_instance, field.attname) == to_instance_pk:
            return True


@contextmanager
def disable_logging():
    set_thread_variable('disable_logging', True)
    try:
        yield
    finally:
        del_thread_variable('disable_logging')


@contextmanager
def disable_related():
    set_thread_variable('disable_related', True)
    try:
        yield
    finally:
        del_thread_variable('disable_related')


def get_obj_repr(obj):
    if hasattr(obj, 'simple_log_repr'):
        return force_text(obj.simple_log_repr())
    return force_text(obj)


def user_is_authenticated(user):
    try:
        return user.is_authenticated()
    except TypeError:
        # In django==2.0 is_authenticated is boolean
        return user.is_authenticated
