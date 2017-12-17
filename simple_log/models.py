# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime

import os
from django.conf import settings as django_settings
from django.contrib.admin.utils import quote
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import models, connection
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from simple_log.fields import SimpleManyToManyField, SimpleJSONField
from simple_log.signals import save_logs_on_commit
from .conf import settings
from .utils import (
    get_current_request, get_current_user, get_fields,
    get_thread_variable, set_thread_variable, get_obj_repr,
    get_serializer, del_thread_variable, user_is_authenticated,
)

try:
    from django.urls import reverse, NoReverseMatch
except ImportError:
    from django.core.urlresolvers import reverse, NoReverseMatch


__all__ = ['SimpleLogAbstractBase', 'SimpleLogAbstract', 'SimpleLog',
           'ModelSerializer']


@python_2_unicode_compatible
class SimpleLogAbstractBase(models.Model):
    ADD = 1
    CHANGE = 2
    DELETE = 3
    ACTION_CHOICES = (
        (ADD, _('added')),
        (CHANGE, _('changed')),
        (DELETE, _('deleted')),
    )
    action_time = models.DateTimeField(
        _('action time'),
        default=timezone.now,
        editable=False,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        verbose_name=_('content type'),
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name=_('user'),
        null=True
    )
    user_repr = models.CharField(_('user repr'), blank=True, max_length=1000)
    user_ip = models.GenericIPAddressField(_('IP address'), null=True)
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), max_length=1000)
    old = SimpleJSONField(_('old values'), null=True)
    new = SimpleJSONField(_('new values'), null=True)
    change_message = models.TextField(_('change message'), blank=True)

    related_logs = SimpleManyToManyField(
        'self',
        verbose_name=_('related log'),
        blank=True,
        symmetrical=False,
    )

    is_add = property(lambda self: self.action_flag == self.ADD)
    is_change = property(lambda self: self.action_flag == self.CHANGE)
    is_delete = property(lambda self: self.action_flag == self.DELETE)

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('logs entries')
        ordering = ('-action_time',)
        abstract = True

    def __str__(self):
        return '%s' % self.object_repr

    def save(self, *args, **kwargs):
        if settings.SAVE_ONLY_CHANGED:
            changed = self.changed_fields.keys()
            self.old = {k: v for k, v in (self.old or {}).items()
                        if k in changed} or None
            self.new = {k: v for k, v in (self.new or {}).items()
                        if k in changed} or None
        super(SimpleLogAbstractBase, self).save(*args, **kwargs)

    def get_edited_object(self):
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        if self.content_type and self.object_id:
            url_name = 'admin:%s_%s_change' % (self.content_type.app_label,
                                               self.content_type.model)
            try:
                return reverse(url_name, args=(quote(self.object_id),))
            except NoReverseMatch:
                pass
        return None

    @classmethod
    def get_log_params(cls, instance, **kwargs):
        if 'user' in kwargs:
            user = kwargs['user']
        else:
            user = get_current_user()
        params = dict(
            content_type=ContentType.objects.get_for_model(
                instance.__class__,
                for_concrete_model=getattr(
                    instance,
                    'simple_log_proxy_concrete',
                    settings.PROXY_CONCRETE
                )
            ),
            object_id=instance.pk,
            object_repr=get_obj_repr(instance),
            user=user if user and user_is_authenticated(user) else None,
            user_repr=cls.get_user_repr(user),
            user_ip=cls.get_ip()
        )
        params.update(getattr(instance, 'simple_log_params', {}))
        params.update(kwargs)
        return params

    @classmethod
    def add_to_thread(cls, obj):
        in_commit = save_logs_on_commit in \
                    [f[1] for f in connection.run_on_commit]
        logs = get_thread_variable('logs', [])
        # prevent memory usage in non transaction test cases
        if not in_commit and logs:
            del_thread_variable('logs')
            del_thread_variable('request')
            logs = []
        logs.append(obj)
        set_thread_variable('logs', logs)
        if not in_commit:
            connection.on_commit(save_logs_on_commit)

    @classmethod
    def set_initial(cls, instance):
        if instance.pk and \
                not hasattr(instance, settings.OLD_INSTANCE_ATTR_NAME):
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

    @classmethod
    def log(cls, instance, commit=True, with_initial=False,
            force_save=False, **kwargs):
        if with_initial:
            cls.set_initial(instance)
        obj = cls(**cls.get_log_params(instance, **kwargs))
        obj.force_save = force_save
        obj.instance = instance
        if commit:
            obj.save()
        cls.add_to_thread(obj)
        return obj

    @cached_property
    def changed_fields(self):
        old = self.old or {}
        new = self.new or {}
        vals = old or new
        return {
            k: vals[k]['label'] for k in vals.keys()
            if old.get(k) != new.get(k)
        }

    def m2m_field_diff(self, field_name):
        """
        :param field_name: m2m field name
        :return:
            - list with added items
            - list with removed items
        """
        old = (self.old or {}).get(field_name, {}).get('value', [])
        new = (self.new or {}).get(field_name, {}).get('value', [])
        return [x for x in new if x not in old], \
               [x for x in old if x not in new]

    @staticmethod
    def get_ip():
        request = get_current_request()
        if request:
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip:
                ip = ip.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            try:
                validate_ipv46_address(ip)
                return ip
            except ValidationError:
                pass

    @classmethod
    def get_user_repr(cls, user):
        if user is None:
            return settings.NONE_USER_REPR
        elif user_is_authenticated(user):
            return force_text(user)
        else:
            return settings.ANONYMOUS_REPR

    def get_differences(self):
        old = self.old or {}
        new = self.new or {}
        return [{
            'label': value,
            'old': old.get(key, {}).get('value'),
            'new': new.get(key, {}).get('value')
        } for key, value in self.changed_fields.items()]


class SimpleLogAbstract(SimpleLogAbstractBase):
    action_flag = models.PositiveSmallIntegerField(
        _('action flag'),
        choices=SimpleLogAbstractBase.ACTION_CHOICES
    )

    class Meta(SimpleLogAbstractBase.Meta):
        abstract = True

    def __str__(self):
        return '%s: %s' % (self.object_repr, self.get_action_flag_display())


class SimpleLog(SimpleLogAbstract):
    class Meta(SimpleLogAbstract.Meta):
        swappable = 'SIMPLE_LOG_MODEL'


class ModelSerializer(object):
    def __call__(self, instance, override=None):
        return self.serialize(instance, override)

    def serialize(self, instance, override=None):
        if not (instance and instance.pk):
            return None
        return {
            field.name: {
                'label': self.get_field_label(field),
                'value': self.get_field_value(instance, field, override)
            } for field in get_fields(instance.__class__)
        }

    def get_field_label(self, field):
        if field.one_to_many:
            return force_text(field.related_model._meta.verbose_name_plural)
        return force_text(field.verbose_name)

    def get_field_value(self, instance, field, override=None):
        if override and field.name in override:
            return self.get_value_for_type(override[field.name])
        if field.many_to_many:
            return self.get_m2m_value(instance, field)
        elif field.one_to_many:
            return self.get_o2m_value(instance, field)
        elif field.is_relation:
            return self.get_fk_value(instance, field)
        elif getattr(field, 'choices', None):
            return self.get_choice_value(instance, field)
        elif isinstance(field, models.FileField):
            return self.get_file_value(instance, field)
        return self.get_other_value(instance, field)

    def get_m2m_value(self, instance, field):
        return [{
            'db': self.get_value_for_type(x.pk),
            'repr': get_obj_repr(x)
        } for x in getattr(instance, field.name).iterator()]

    def get_o2m_value(self, instance, field):
        return [{
            'db': self.get_value_for_type(x.pk),
            'repr': get_obj_repr(x)
        } for x in getattr(instance, field.name).iterator()]

    def get_fk_value(self, instance, field):
        return {
            'db': self.get_value_for_type(field.value_from_object(instance)),
            'repr': self.get_value_for_type(
                getattr(instance, field.name)
            ) or '',
        }

    def get_choice_value(self, instance, field):
        return {
            'db': self.get_value_for_type(field.value_from_object(instance)),
            'repr': self.get_value_for_type(
                instance._get_FIELD_display(field=field)
            ) or '',
        }

    def get_file_value(self, instance, field):
        value = self.get_value_for_type(field.value_from_object(instance))
        if settings.FILE_NAME_ONLY or instance.simple_log_file_name_only:
            value = os.path.basename(value)
        return value

    def get_other_value(self, instance, field):
        return self.get_value_for_type(field.value_from_object(instance))

    @staticmethod
    def get_value_for_type(value):
        if value is None or isinstance(value, (int, bool, dict, list)):
            return value
        if isinstance(value, datetime.datetime) and settings.DATETIME_FORMAT:
            return value.strftime(settings.DATETIME_FORMAT)
        if isinstance(value, datetime.date) and settings.DATE_FORMAT:
            return value.strftime(settings.DATE_FORMAT)
        if isinstance(value, datetime.time) and settings.TIME_FORMAT:
            return value.strftime(settings.TIME_FORMAT)
        return force_text(value)
