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


def save_log(instance, flag):
    model = instance.__class__
    if not need_to_log(model):
        return
    SimpleLog = get_log_model(model)
    serializer = get_serializer()()
    new_values = serializer(instance)
    if instance._old_values != new_values:
        SimpleLog.log(
            instance,
            action_flag=flag,
            old=instance._old_values or None,
            new=new_values or None,
        )


def set_old_instance(instance):
    if instance.pk and not hasattr(instance, settings.OLD_INSTANCE_ATTR_NAME):
        setattr(
            instance,
            settings.OLD_INSTANCE_ATTR_NAME,
            instance.__class__.objects.filter(pk=instance.pk)
                                      .select_related().first()
        )


def log_pre_save(sender, instance, **kwargs):
    if not need_to_log(sender):
        return
    set_old_instance(instance)
    serializer = get_serializer()()
    SimpleLog = get_log_model(instance.__class__)
    if not hasattr(instance, '_old_values'):
        instance._old_values = serializer(
            getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
        )


def log_pre_delete(sender, instance, **kwargs):
    if not need_to_log(sender):
        return
    set_old_instance(instance)
    serializer = get_serializer()()
    SimpleLog = get_log_model(instance.__class__)
    if not hasattr(instance, '_old_values'):
        instance._old_values = serializer(
            getattr(instance, settings.OLD_INSTANCE_ATTR_NAME, None)
        )
    SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None
    )


def log_post_save(sender, instance, created, **kwargs):
    if not need_to_log(sender):
        return
    SimpleLog = get_log_model(sender)
    flag = SimpleLog.ADD if created else SimpleLog.CHANGE
    connection.on_commit(lambda: save_log(instance, flag))


def log_post_delete(sender, instance, **kwargs):
    if not need_to_log(sender):
        return
    SimpleLog = get_log_model(sender)

    SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None
    )
    # connection.on_commit(lambda: save_log(instance))


def log_m2m_change(sender, instance, action, **kwargs):
    if not need_to_log(instance.__class__):
        return
    SimpleLog = get_log_model(instance.__class__)
    serializer = get_serializer()()

    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        set_old_instance(instance)
        if not hasattr(instance, '_old_values'):
            instance._old_values = serializer(instance)

    if not hasattr(instance, '_log'):
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.CHANGE,
            commit=False,
        )
    connection.on_commit(lambda: save_log(instance, SimpleLog.CHANGE))

    # if action in ('post_add', 'post_remove', 'post_clear'):
    #     new_values = serializer(instance)
    #     if instance._old_values != new_values:
    #         instance._log.new = new_values
    #         instance._log.save()


def register(*models, **kwargs):
    models = models or [None]
    for model in models:
        pre_save.connect(log_pre_save, sender=model)
        post_save.connect(log_post_save, sender=model)
        pre_delete.connect(log_pre_delete, sender=model)
        # post_delete.connect(log_post_delete, sender=model)
        if not model:
            m2m_changed.connect(log_m2m_change)
        if model:
            registered_models[model] = kwargs.get('log_model')
            for m2m in model._meta.many_to_many:
                sender = getattr(model, m2m.name).through
                m2m_changed.connect(log_m2m_change, sender=sender)
