# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import (
    pre_save, post_save, pre_delete, post_delete, m2m_changed
)
from django.utils.translation import ugettext_lazy as _

import simple_log
from simple_log.utils import get_label, get_model_list


class SimpleLogConfig(AppConfig):
    name = 'simple_log'
    verbose_name = _('Logs')

    def register_signals(self, model):
        from simple_log.signals import (
            log_pre_save_delete, log_post_save, log_post_delete, log_m2m_change
        )
        label = get_label(model)
        pre_save.connect(log_pre_save_delete, sender=label)
        post_save.connect(log_post_save, sender=label)
        pre_delete.connect(log_pre_save_delete, sender=label)
        post_delete.connect(log_post_delete, sender=label)
        for m2m in model._meta.many_to_many:
            sender = getattr(model, m2m.name).through
            m2m_changed.connect(log_m2m_change, sender=sender)

    def ready(self):
        if not simple_log.registered:
            for model in get_model_list():
                self.register_signals(model)
                simple_log.registered = True
