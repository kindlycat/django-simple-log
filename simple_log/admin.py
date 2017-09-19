# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import update_wrapper

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

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

    def model_history_view(self, request, extra_context=None):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        admin_model = SimpleLogModelAdmin(get_log_model(), self.admin_site)
        admin_model.history_for_model = self.model
        return admin_model.changelist_view(request)
