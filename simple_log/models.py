# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings as django_settings
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.admin.utils import quote
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from .conf import settings
from .utils import (
    get_current_request, get_current_user, get_fields, str_or_none
)

try:
    from django.urls import reverse, NoReverseMatch
except ImportError:
    from django.core.urlresolvers import reverse, NoReverseMatch

try:
    from django.contrib.postgres.fields.jsonb import JSONField
except ImportError:
    from jsonfield import JSONField


__all__ = ['SimpleLogAbstract', 'SimpleLog', 'ModelSerializer']


@python_2_unicode_compatible
class SimpleLogAbstract(models.Model):
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
        blank=True, null=True,
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
    action_flag = models.PositiveSmallIntegerField(
        _('action flag'),
        choices=ACTION_CHOICES
    )
    old = JSONField(_('old values'), null=True)
    new = JSONField(_('new values'), null=True)

    is_add = property(lambda self: self.action_flag == self.ADD)
    is_change = property(lambda self: self.action_flag == self.CHANGE)
    is_delete = property(lambda self: self.action_flag == self.DELETE)

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('logs entries')
        ordering = ('-action_time',)
        abstract = True

    def __str__(self):
        return '%s: %s' % (self.object_repr, self.get_action_flag_display())

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
    def log(cls, instance, commit=True, **kwargs):
        user = kwargs.get('user')
        if 'user' not in kwargs:
            user = get_current_user()
        if 'user_repr' not in kwargs:
            if user is None:
                kwargs['user_repr'] = settings.NONE_USER_REPR
            elif user.is_authenticated():
                kwargs['user_repr'] = force_text(user)
            else:
                kwargs['user_repr'] = settings.ANONYMOUS_REPR
        if 'user_ip' not in kwargs:
            kwargs['user_ip'] = cls.get_ip()
        kwargs.update({
            'content_type': get_content_type_for_model(instance.__class__),
            'object_id': instance.pk,
            'object_repr': force_text(instance),
            'user': user if user and user.is_authenticated() else None
        })
        obj = cls(**kwargs)
        if commit:
            obj.save()
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
        :param old: list with old values
        :param new: list with new values
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
            ip = request.META.get('HTTP_X_REAL_IP') or \
                 request.META.get('REMOTE_ADDR') or \
                 request.META.get('HTTP_X_FORWARDED_FOR')
            try:
                validate_ipv46_address(ip)
                return ip
            except ValidationError:
                pass


class SimpleLog(SimpleLogAbstract):
    class Meta(SimpleLogAbstract.Meta):
        swappable = 'SIMPLE_LOG_MODEL'


class ModelSerializer(object):
    def __call__(self, instance):
        return self.serialize(instance)

    def serialize(self, instance):
        if not instance:
            return {}
        fields = get_fields(instance.__class__)
        ret = {}
        for field in fields:
            ret[field.name] = {
                'label': force_text(field.verbose_name),
                'value': self.get_field_value(instance, field)
            }
        return ret

    def get_field_value(self, instance, field):
        if field.many_to_many:
            return self.get_m2m_value(instance, field)
        elif field.is_relation:
            return self.get_fk_value(instance, field)
        elif getattr(field, 'choices', None):
            return self.get_choice_value(instance, field)
        return self.get_other_value(instance, field)

    @staticmethod
    def get_m2m_value(instance, field):
        return [{
            'db': force_text(x.pk),
            'repr': force_text(x)
        } for x in getattr(instance, field.name).iterator()]

    @staticmethod
    def get_fk_value(instance, field):
        return {
            'db': str_or_none(field.value_from_object(instance)),
            'repr': str_or_none(getattr(instance, field.name)) or '',
        }

    @staticmethod
    def get_choice_value(instance, field):
        return {
            'db': str_or_none(field.value_from_object(instance)),
            'repr': str_or_none(
                instance._get_FIELD_display(field=field)
            ) or '',
        }

    @staticmethod
    def get_other_value(instance, field):
        return str_or_none(field.value_from_object(instance))
