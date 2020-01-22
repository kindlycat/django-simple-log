# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings as dj_settings
from django.core.signals import setting_changed
from django.utils.translation import ugettext_lazy as _


DEFAULTS = {
    'MODEL': 'simple_log.SimpleLog',
    'MODEL_SERIALIZER': 'simple_log.models.ModelSerializer',
    'MODEL_LIST': (),
    'EXCLUDE_MODEL_LIST': (
        'admin.LogEntry',
        'migrations.Migration',
        'sessions.Session',
        'contenttypes.ContentType',
        'captcha.CaptchaStore',
    ),
    'EXCLUDE_FIELD_LIST': (
        'id',
        'last_login',
        'password',
        'created_at',
        'updated_at',
    ),
    'ANONYMOUS_REPR': _('Anonymous'),
    'NONE_USER_REPR': _('System'),
    'GET_CURRENT_REQUEST': 'simple_log.utils.get_current_request_default',
    'OLD_INSTANCE_ATTR_NAME': '_old_instance',
    'SAVE_RELATED': False,
    'SAVE_ONE_TO_MANY': False,
    'PROXY_CONCRETE': False,
    'SAVE_ONLY_CHANGED': False,
    'DATETIME_FORMAT': None,
    'DATE_FORMAT': None,
    'TIME_FORMAT': None,
    'FILE_NAME_ONLY': True,
    'EXCLUDE_RAW': False,
}


DEPRECATED_SETTINGS = []


class Settings(object):
    prefix = 'SIMPLE_LOG_'

    def __getattr__(self, name):
        if name not in DEFAULTS:
            msg = "'%s' object has no attribute '%s'"
            raise AttributeError(msg % (self.__class__.__name__, name))

        value = self.get_setting(name)
        setattr(self, name, value)
        return value

    def get_setting(self, setting):
        django_setting = self.prefix + setting
        return getattr(dj_settings, django_setting, DEFAULTS[setting])

    def change_setting(self, setting, value, enter, **kwargs):
        if not setting.startswith(self.prefix):
            return
        setting = setting.replace(self.prefix, '')

        if setting not in DEFAULTS:
            return

        if enter:
            setattr(self, setting, value)
        else:
            delattr(self, setting)


if not hasattr(dj_settings, 'SIMPLE_LOG_MODEL'):
    setattr(dj_settings, 'SIMPLE_LOG_MODEL', DEFAULTS['MODEL'])

settings = Settings()
setting_changed.connect(settings.change_setting)
