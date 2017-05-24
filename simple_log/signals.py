# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from simple_log.utils import get_serializer, get_log_model, get_thread_variable
from simple_log.conf import settings

from django.db import connection


def save_log(instance, force_save=False):
    serializer = get_serializer(instance.__class__)()
    if force_save:
        instance._log.save()
    else:
        new_values = serializer(instance)
        if instance._old_values != new_values:
            instance._log.old = instance._old_values or None
            instance._log.new = new_values or None
            instance._log.save()
    instance._on_commit = False


def set_initial(instance):
    if instance.pk and not hasattr(instance, settings.OLD_INSTANCE_ATTR_NAME):
        setattr(
            instance,
            settings.OLD_INSTANCE_ATTR_NAME,
            instance.__class__.objects.filter(pk=instance.pk)
                                      .select_related().first()
        )
    if not hasattr(instance, '_old_values'):
        serializer = get_serializer(instance.__class__)()
        instance._old_values = serializer(
            getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
        )
    instance._on_commit = False


def log_pre_save_delete(sender, instance, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    set_initial(instance)


def log_post_save(sender, instance, created, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    SimpleLog = get_log_model(sender)
    if not hasattr(instance, '_log'):
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.ADD if created else SimpleLog.CHANGE,
            commit=False
        )
    if not instance._on_commit:
        instance._on_commit = True
        connection.on_commit(lambda: save_log(instance))


def log_post_delete(sender, instance, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    SimpleLog = get_log_model(instance.__class__)
    instance._log = SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None,
        commit=False
    )
    if not instance._on_commit:
        instance._on_commit = True
        connection.on_commit(lambda: save_log(instance, True))


def log_m2m_change(sender, instance, action, **kwargs):
    if get_thread_variable('disable_logging'):
        return

    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        set_initial(instance)

    if action in ('post_add', 'post_remove', 'post_clear'):
        SimpleLog = get_log_model(instance.__class__)
        if not hasattr(instance, '_log'):
            instance._log = SimpleLog.log(
                instance,
                action_flag=SimpleLog.CHANGE,
                old=instance._old_values,
                commit=False
            )
        if not instance._on_commit:
            instance._on_commit = True
            connection.on_commit(lambda: save_log(instance))
