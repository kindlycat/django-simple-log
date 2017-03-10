# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from simple_log.models import SimpleLogAbstract


class CustomSimpleLog(SimpleLogAbstract):
    class Meta(SimpleLogAbstract.Meta):
        swappable = 'SIMPLE_LOG_MODEL'
