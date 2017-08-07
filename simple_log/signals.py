# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import partial

from simple_log.utils import (
    get_serializer, get_log_model, get_thread_variable, set_thread_variable,
    del_thread_variable, get_related_models
)
from simple_log.conf import settings

from django.db import connection


def save_log_instance(log):
    if settings.SAVE_ONLY_CHANGED:
        changed = log.changed_fields.keys()
        log.old = {k: v for k, v in (log.old or {}).items()
                   if k in changed} or None
        log.new = {k: v for k, v in (log.new or {}).items()
                   if k in changed} or None
    log.save()


def save_related(logs):
    for instance, saved_log in [(k, v) for k, v in logs.items() if v.pk]:
        related_models = get_related_models(instance.__class__)
        for related in [v for k, v in logs.items()
                        if k.__class__ in related_models]:
            if not related.pk:
                save_log_instance(related)
            related.related_logs.add(saved_log)


def save_log_to_thread(instance, force_save=False):
    logs = get_thread_variable('logs', {})
    logs[instance] = instance._log
    set_thread_variable('logs', logs)
    if not getattr(instance, '_save_logs', False):
        instance._save_logs = True
        connection.on_commit(partial(save_log, instance, force_save))


def save_log(instance, force_save=False):
    serializer = get_serializer(instance.__class__)()
    if force_save:
        instance._log.save()
    else:
        new_values = serializer(instance)
        instance._log.old = instance._old_values
        instance._log.new = new_values
        if instance._old_values != new_values:
            save_log_instance(instance._log)
    instance._save_logs = False
    logs = get_thread_variable('logs', {})
    if not [x for x in logs.keys() if x._save_logs]:
        if (settings.SAVE_RELATED and
                not get_thread_variable('disable_related') and
                any([x.pk for x in logs.values()])):
            save_related(logs)
        del_thread_variable('logs')
        del_thread_variable('request')


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
            getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None),
            override=getattr(instance, 'simple_log_override', None)
        )
    instance._save_logs = False


def log_pre_save_delete(sender, instance, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    set_initial(instance)


def log_post_save(sender, instance, created, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    if not hasattr(instance, '_log'):
        SimpleLog = get_log_model(sender)
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.ADD if created else SimpleLog.CHANGE,
            commit=False
        )
    save_log_to_thread(instance)


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
    save_log_to_thread(instance, True)


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
                commit=False
            )
        save_log_to_thread(instance)
