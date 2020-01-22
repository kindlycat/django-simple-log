# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import (
    m2m_changed,
    post_save,
    pre_delete,
    pre_save,
)
from django.utils.translation import ugettext_lazy as _

import simple_log
from simple_log.signals import (
    log_m2m_change_handler,
    log_post_save_handler,
    log_pre_delete_handler,
    log_pre_save_handler,
)
from simple_log.utils import get_model_list


class SimpleLogConfig(AppConfig):
    name = 'simple_log'
    verbose_name = _('Logs')
    uid = 'simple_log.{}.{}'
    m2m_uid = 'simple_log.{}.{}.{}'

    def register_signals(self, model):
        label = model._meta.label
        pre_save.connect(
            log_pre_save_handler,
            sender=label,
            dispatch_uid=self.uid.format('pre_save', label),
        )
        post_save.connect(
            log_post_save_handler,
            sender=label,
            dispatch_uid=self.uid.format('post_save', label),
        )
        pre_delete.connect(
            log_pre_delete_handler,
            sender=label,
            dispatch_uid=self.uid.format('pre_delete', label),
        )
        pre_delete.connect(
            log_pre_delete_handler,
            sender=label,
            dispatch_uid=self.uid.format('post_delete', label),
        )
        for m2m in model._meta.many_to_many:
            sender = getattr(model, m2m.name).through
            m2m_changed.connect(
                log_m2m_change_handler,
                sender=sender,
                dispatch_uid=self.m2m_uid.format(
                    'post_delete', sender._meta.label, label
                ),
            )

    def ready(self):
        if not simple_log.registered:
            for model in get_model_list():
                self.register_signals(model)
                simple_log.registered = True
