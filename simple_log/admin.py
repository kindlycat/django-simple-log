# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import update_wrapper

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _

from simple_log.utils import get_log_model


class SimpleLogModelAdmin(admin.ModelAdmin):
    list_display = ('object_repr', 'content_type', 'action_flag',
                    'action_time', 'user_repr', 'user_ip')
    list_filter = ('action_flag', 'content_type')
    search_fields = ('object_repr', 'user_repr', 'user_ip')
    change_form_template = 'simple_log/detail.html'
    history_for_model = None
    history_for_object = None

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        return []

    def get_list_filter(self, request):
        ret = super(SimpleLogModelAdmin, self).get_list_filter(request)
        if self.history_for_model:
            ret = [x for x in ret if x != 'content_type']
        return ret

    def get_queryset(self, request):
        qs = super(SimpleLogModelAdmin, self).get_queryset(request)
        if self.history_for_model:
            ct = ContentType.objects.get_for_model(self.history_for_model)
            qs = qs.filter(content_type=ct)
            if self.history_for_object:
                qs = qs.filter(object_id=self.history_for_object)
        return qs


class HistoryModelAdmin(admin.ModelAdmin):
    change_list_template = 'simple_log/change_list.html'
    history_change_list_template = 'simple_log/history_change_list.html'

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urlpatterns = super(HistoryModelAdmin, self).get_urls()
        custom_urlpatterns = [
            url(r'^history/$', wrap(self.model_history_view),
                name='%s_%s_model_history' % info),
        ]
        return custom_urlpatterns + urlpatterns

    def get_simple_log_model_admin(self, model=None, object_id=None):
        admin_model = SimpleLogModelAdmin(get_log_model(), self.admin_site)
        admin_model.change_list_template = self.history_change_list_template
        admin_model.history_for_model = model
        admin_model.history_for_object = object_id
        return admin_model

    def model_history_view(self, request, extra_context=None):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        admin_model = self.get_simple_log_model_admin(model=self.model)
        extra_context = {
            'history_model_opts': self.model._meta
        }
        return admin_model.changelist_view(request, extra_context)

    def history_view(self, request, object_id, extra_context=None):
        if not self.has_change_permission(request):
            raise PermissionDenied

        obj = self.get_object(request, object_id, extra_context)
        admin_model = self.get_simple_log_model_admin(model=self.model,
                                                      object_id=object_id)
        extra_context = {
            'history_model_opts': self.model._meta,
            'history_object': obj
        }
        return admin_model.changelist_view(request, extra_context)
