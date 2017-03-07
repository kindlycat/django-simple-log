# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SimpleLogConfig(AppConfig):
    name = 'simple_log'
    verbose_name = _('Logs')
