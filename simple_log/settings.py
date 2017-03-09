# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.utils.translation import ugettext_lazy as _


SIMPLE_LOG_MODEL = getattr(settings, 'SIMPLE_LOG_MODEL', 'simple_log.SimpleLog')
MODEL_SERIALIZER = getattr(settings, 'SIMPLE_LOG_MODEL_SERIALIZER',
                           'simple_log.models.ModelSerializer')
MODEL_LIST = getattr(settings, 'SIMPLE_LOG_MODEL_LIST', ())
EXCLUDE_MODEL_LIST = getattr(
    settings, 'SIMPLE_LOG_EXCLUDE_MODEL_LIST',
    ('admin.LogEntry', 'migrations.Migration', 'sessions.Session',
     'contenttypes.ContentType', 'captcha.CaptchaStore')
)
EXCLUDE_FIELD_LIST = getattr(
    settings, 'SIMPLE_LOG_EXCLUDE_FIELD_LIST',
    ('id', 'last_login', 'password', 'created_at', 'updated_at')
)
ANONYMOUS_REPR = getattr(settings, 'SIMPLE_LOG_ANONYMOUS_REPR', _('Anonymous'))
NONE_USER_REPR = getattr(settings, 'SIMPLE_LOG_NONE_USER_REPR', _('System'))
GET_CURRENT_REQUEST = getattr(settings, 'SIMPLE_LOG_GET_REQUEST_PATH',
                              'simple_log.utils.get_current_request_default')
