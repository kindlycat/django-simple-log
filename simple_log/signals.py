# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.signals import (
    post_save, pre_save, m2m_changed, post_delete, pre_delete
)

from .utils import (
    get_simple_log_model, get_models_for_log, get_serializer, registered_models
)


def log_pre_save_delete(sender, instance, **kwargs):
    if sender not in get_models_for_log():
        return
    instance._old_instance = None
    if instance.pk:
        instance._old_instance = sender.objects.filter(pk=instance.pk)\
                                               .select_related().first()
    serializer = get_serializer()()
    instance._old_values = serializer(instance._old_instance)


def log_post_save(sender, instance, created, **kwargs):
    if sender not in get_models_for_log():
        return
    SimpleLog = get_simple_log_model()
    serializer = get_serializer()()
    new_values = serializer(instance)

    if instance._old_values != new_values:
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.ADD if created else SimpleLog.CHANGE,
            old=instance._old_values or None,
            new=new_values,
        )


def log_post_delete(sender, instance, **kwargs):
    if sender not in get_models_for_log():
        return
    SimpleLog = get_simple_log_model()

    SimpleLog.log(
        instance,
        action_flag=SimpleLog.DELETE,
        old=instance._old_values,
        new=None
    )


def log_m2m_change(sender, instance, action, **kwargs):
    if instance.__class__ not in get_models_for_log():
        return
    SimpleLog = get_simple_log_model()
    serializer = get_serializer()()

    if action in ('pre_add', 'pre_remove'):
        if not hasattr(instance, '_old_values'):
            instance._old_values = serializer(instance)

    if not hasattr(instance, '_log'):
        instance._log = SimpleLog.log(
            instance,
            action_flag=SimpleLog.CHANGE,
            old=instance._old_values or None,
            new={},
        )

    if action in ('post_add', 'post_remove'):
        new_values = serializer(instance)
        if instance._old_values != new_values:
            instance._log.new = new_values
            instance._log.save()


def register(*models):
    models = models or [None]
    for model in models:
        pre_save.connect(log_pre_save_delete, sender=model)
        post_save.connect(log_post_save, sender=model)
        pre_delete.connect(log_pre_save_delete, sender=model)
        post_delete.connect(log_post_delete, sender=model)
        if not model:
            m2m_changed.connect(log_m2m_change)
        else:
            registered_models.append(model)
            for m2m in model._meta.many_to_many:
                sender = getattr(model, m2m.name).through
                m2m_changed.connect(log_m2m_change, sender=sender)
