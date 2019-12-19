# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from functools import wraps

from request_vars.utils import del_variable, get_variable, set_variable

from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_text
from django.utils.module_loading import import_string

from simple_log.conf import settings


try:
    from django.utils import six
    from django.utils.lru_cache import lru_cache
except ImportError:
    # django > 2.
    import six
    from functools import lru_cache


__all__ = [
    'get_log_model',
    'get_current_user',
    'get_current_request',
    'get_serializer',
    'disable_logging',
    'get_model_list',
    'disable_related',
    'get_obj_repr',
    'is_related_to',
    'get_fields',
    'ContextDecorator',
    'serialize_instance',
]


logger = logging.getLogger('simple_log')


def check_log_model(model):
    from simple_log.models import SimpleLogAbstractBase

    if not issubclass(model, SimpleLogAbstractBase):
        raise ImproperlyConfigured(
            'Log model should be subclass of ' 'SimpleLogAbstractBase.'
        )
    return model


@lru_cache()
def get_log_model():
    try:
        return check_log_model(django_apps.get_model(settings.MODEL))
    except (ValueError, AttributeError):
        raise ImproperlyConfigured(
            "SIMPLE_LOG_MODEL must be of the form " "'app_label.model_name'"
        )
    except LookupError:
        raise ImproperlyConfigured(
            "SIMPLE_LOG_MODEL refers to model '%s' "
            "that has not been installed" % settings.MODEL
        )


@lru_cache(maxsize=None)
def get_serializer(model=None):
    if hasattr(model, 'simple_log_serializer'):
        serializer = model.simple_log_serializer
    else:
        serializer = settings.MODEL_SERIALIZER
    if isinstance(serializer, six.string_types):
        return import_string(serializer)
    return serializer


def get_current_request_default():
    return get_variable('request')


@lru_cache(maxsize=None)
def _get_current_request():
    return import_string(settings.GET_CURRENT_REQUEST)


get_current_request = _get_current_request()


def get_current_user():
    request = get_current_request()
    if request:
        return getattr(request, 'user', None)


@lru_cache()
def get_fields(klass):
    fields = klass._meta.get_fields()
    if hasattr(klass, 'simple_log_fields'):
        fields = [f for f in fields if f.name in klass.simple_log_fields]
    elif hasattr(klass, 'simple_log_exclude_fields'):
        fields = [
            f for f in fields if f.name not in klass.simple_log_exclude_fields
        ]
    else:
        fields = [
            f for f in fields if f.name not in settings.EXCLUDE_FIELD_LIST
        ]
    return [
        f
        for f in fields
        if f.concrete
        or (settings.SAVE_ONE_TO_MANY and f.one_to_many and f.related_name)
    ]


@lru_cache(maxsize=None)
def get_model_list():
    from simple_log.models import SimpleLogAbstractBase

    model_list = [
        m
        for m in django_apps.get_models()
        if not issubclass(m, SimpleLogAbstractBase) and m._meta.managed
    ]
    if settings.MODEL_LIST:
        model_list = [
            m for m in model_list if m._meta.label in settings.MODEL_LIST
        ]
    if settings.EXCLUDE_MODEL_LIST:
        model_list = [
            m
            for m in model_list
            if m._meta.label not in settings.EXCLUDE_MODEL_LIST
        ]
    return model_list


def is_related_to(instance, to_instance):
    if instance == to_instance:
        return False
    old_instance = getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
    to_instance_pk = to_instance.pk
    if not to_instance_pk:
        # If deleted
        old_to_instance = getattr(
            to_instance, settings.OLD_INSTANCE_ATTR_NAME, None
        )
        to_instance_pk = getattr(old_to_instance, 'pk', None)
    related_fields = [
        x
        for x in instance._meta.get_fields()
        if (
            x.related_model
            and issubclass(to_instance.__class__, x.related_model)
            and x.concrete
        )
    ]
    for field in related_fields:
        if (
            getattr(instance, field.attname, None) == to_instance_pk
            or getattr(old_instance, field.attname, None) == to_instance_pk
        ):
            return True


class ContextDecorator(object):
    """
    A base class or mixin that enables context managers to work as decorators.

    Backport for python 2.7
    """

    def _recreate_cm(self):
        """Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 for details.
        """
        return self

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            with self._recreate_cm():
                return func(*args, **kwds)

        return inner


class disable_logging(ContextDecorator):
    def __enter__(self):
        set_variable('disable_logging', True)
        return self

    def __exit__(self, *exc):
        del_variable('disable_logging')


class disable_related(ContextDecorator):
    def __enter__(self):
        set_variable('disable_related', True)
        return self

    def __exit__(self, *exc):
        del_variable('disable_related')


def get_obj_repr(obj):
    if hasattr(obj, 'simple_log_repr'):
        return force_text(obj.simple_log_repr())
    return force_text(obj)


def serialize_instance(instance):
    serializer_class = get_serializer(instance.__class__)
    serializer = serializer_class()
    try:
        return serializer(instance)
    except Exception:
        logger.exception(
            "Can't serialize instance: {} with pk {}".format(
                instance.__class__, instance.pk
            )
        )


def is_log_needed(instance, raw):
    return not (
        get_variable('disable_logging')
        or instance in get_variable('simple_log_instances', [])
        or (raw and settings.EXCLUDE_RAW)
    )
