# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.signals import (
    m2m_changed, post_delete, post_save, pre_delete, pre_save
)

from simple_log.utils import (
    get_serializer, get_log_model, registered_models, need_to_log
)
from simple_log.conf import settings

from django.db import connection


def save_log(instance):
    model = instance.__class__
    if not need_to_log(model):
        return
    serializer = get_serializer()()
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
        serializer = get_serializer()()
        instance._old_values = serializer(
            getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
        )
    instance._on_commit = False


def log_pre_save_delete(sender, instance, **kwargs):
    if not need_to_log(sender):
        return
    set_initial(instance)


def log_post_save(sender, instance, created, **kwargs):
    if not need_to_log(sender):
        return
    SimpleLog = get_log_model(sender)
    if not hasattr(instance, '_log'):
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.ADD if created else SimpleLog.CHANGE,
            commit=False
        )
    if not instance._on_commit:
        connection.on_commit(lambda: save_log(instance))
        instance._on_commit = True


def log_post_delete(sender, instance, **kwargs):
    if not need_to_log(sender):
        return
    SimpleLog = get_log_model(instance.__class__)
    SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None,
    )


def log_m2m_change(sender, instance, action, **kwargs):
    if not need_to_log(instance.__class__):
        return

    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        set_initial(instance)

    if action in ('post_add', 'post_remove', 'post_clear'):
        SimpleLog = get_log_model(instance.__class__)
        if not hasattr(instance, '_log'):
            instance._log = SimpleLog.log(
                instance,
                action_flag=SimpleLog.DELETE,
                old=instance._old_values,
                commit=False
            )
        if not instance._on_commit:
            connection.on_commit(lambda: save_log(instance))
            instance._on_commit = True


def register(*models, **kwargs):
    models = models or [None]
    for model in models:
        pre_save.connect(log_pre_save_delete, sender=model)
        post_save.connect(log_post_save, sender=model)
        pre_delete.connect(log_pre_save_delete, sender=model)
        post_delete.connect(log_post_delete, sender=model)
        if not model:
            m2m_changed.connect(log_m2m_change)
        if model:
            registered_models[model] = kwargs.get('log_model')
            for m2m in model._meta.many_to_many:
                sender = getattr(model, m2m.name).through
                m2m_changed.connect(log_m2m_change, sender=sender)
