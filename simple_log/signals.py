# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from simple_log.utils import (
    get_serializer, get_thread_variable, del_thread_variable,
    get_related_models, get_log_model,
)
from simple_log.conf import settings


def save_related(logs):
    map_related = defaultdict(list)
    for saved_log in [x for x in logs if x.pk]:
        instance = saved_log.instance
        related_models = get_related_models(instance.__class__)
        for related in [k for k in logs
                        if k.instance.__class__ in related_models and
                        k != saved_log]:
            if not related.pk:
                related.save()
            map_related[related].append(saved_log)
    for instance, related in map_related.items():
        instance.related_logs.add(*related)


def save_logs_on_commit():
    logs = get_thread_variable('logs', [])
    for log in [x for x in logs if not x.pk]:
        instance = log.instance
        serializer = get_serializer(instance.__class__)()
        log.old = getattr(instance, '_old_values', None)
        log.new = serializer(instance)
        if log.old != log.new:
            log.save()

    if (settings.SAVE_RELATED and
            not get_thread_variable('disable_related') and
            any([x.pk for x in logs])):
        save_related(logs)

    del_thread_variable('logs')
    del_thread_variable('request')
    del_thread_variable('save_logs_on_commit')


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


def log_pre_save_delete(sender, instance, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    set_initial(instance)


def log_post_save(sender, instance, created, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    if not hasattr(instance, '_log'):
        SimpleLog = get_log_model()
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.ADD if created else SimpleLog.CHANGE,
            commit=False
        )


def log_post_delete(sender, instance, **kwargs):
    if get_thread_variable('disable_logging'):
        return
    SimpleLog = get_log_model()
    instance._log = SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None
    )


def log_m2m_change(sender, instance, action, **kwargs):
    if get_thread_variable('disable_logging'):
        return

    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        set_initial(instance)

    if action in ('post_add', 'post_remove', 'post_clear'):
        SimpleLog = get_log_model()
        if not hasattr(instance, '_log'):
            instance._log = SimpleLog.log(
                instance,
                action_flag=SimpleLog.CHANGE,
                commit=False
            )
