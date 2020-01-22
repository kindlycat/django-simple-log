# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import update_wrapper

from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from simple_log.conf import settings
from simple_log.utils import get_log_model


def filter_ct(val):
    if isinstance(val, (list, tuple)):
        val = val[0]
    return val != 'content_type'


class SimpleLogChangeList(ChangeList):
    def url_for_result(self, result):
        history_for_model = getattr(
            self.model_admin, 'history_for_model', None
        )
        if history_for_model:
            object_opts = history_for_model._meta
            pk = getattr(result, self.pk_attname)
            object_pk = getattr(result, 'object_id')
            return reverse(
                'admin:%s_%s_history_detail'
                % (object_opts.app_label, object_opts.model_name),
                args=(quote(object_pk), quote(pk),),
                current_app=self.model_admin.admin_site.name,
            )
        return super(SimpleLogChangeList, self).url_for_result(result)


class SimpleLogModelAdmin(admin.ModelAdmin):
    list_display = (
        'object_repr',
        'content_type',
        'action_flag',
        'action_time',
        'user_repr',
        'user_ip',
    )
    list_filter = ('action_flag', 'content_type')
    search_fields = ('object_repr', 'user_repr', 'user_ip')
    change_form_template = 'simple_log/admin/detail.html'

    def __init__(
        self,
        model,
        admin_site,
        change_list_template=None,
        history_for_model=None,
        history_for_object=None,
    ):
        super(SimpleLogModelAdmin, self).__init__(model, admin_site)
        self.history_for_model = history_for_model
        self.history_for_object = history_for_object
        if change_list_template:
            self.change_list_template = change_list_template

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        return []

    def get_list_filter(self, request):
        ret = super(SimpleLogModelAdmin, self).get_list_filter(request)
        if self.history_for_model:
            ret = filter(filter_ct, ret)
        return ret

    def get_queryset(self, request):
        qs = super(SimpleLogModelAdmin, self).get_queryset(request)
        if self.history_for_model:
            ct = ContentType.objects.get_for_model(
                self.history_for_model,
                for_concrete_model=getattr(
                    self.model,
                    'simple_log_proxy_concrete',
                    settings.PROXY_CONCRETE,
                ),
            )
            qs = qs.filter(content_type=ct)
            if self.history_for_object:
                qs = qs.filter(object_id=self.history_for_object)
        return qs.select_related('content_type', 'user')

    def get_changelist(self, request, **kwargs):
        return SimpleLogChangeList


class HistoryModelAdmin(admin.ModelAdmin):
    change_list_template = 'simple_log/admin/change_list.html'
    history_change_list_template = 'simple_log/admin/history_change_list.html'

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urlpatterns = super(HistoryModelAdmin, self).get_urls()
        custom_urlpatterns = [
            url(
                r'^history/$',
                wrap(self.model_history_view),
                name='%s_%s_model_history' % info,
            ),
            url(
                r'^(.+)/history/(.+)/$',
                wrap(self.history_detail_view),
                name='%s_%s_history_detail' % info,
            ),
        ]
        return custom_urlpatterns + urlpatterns

    def get_simple_log_admin_model(self, model=None, object_id=None):
        simple_log_model = get_log_model()
        model_admin = admin.site._registry.get(simple_log_model)
        if model_admin:
            model_admin_class = model_admin.__class__
        else:
            model_admin_class = SimpleLogModelAdmin
        return model_admin_class(
            simple_log_model,
            self.admin_site,
            self.history_change_list_template,
            model,
            object_id,
        )

    def model_history_view(self, request, extra_context=None):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        admin_model = self.get_simple_log_admin_model(model=self.model)
        return admin_model.changelist_view(
            request, extra_context={'history_model_opts': self.model._meta}
        )

    def history_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id, extra_context)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        admin_model = self.get_simple_log_admin_model(
            model=self.model, object_id=object_id
        )
        return admin_model.changelist_view(
            request,
            extra_context={
                'history_model_opts': self.model._meta,
                'history_object': obj,
            },
        )

    def history_detail_view(
        self, request, object_id, history_id, extra_context=None
    ):
        obj = self.get_object(request, object_id, extra_context)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        admin_model = self.get_simple_log_admin_model(
            model=self.model, object_id=object_id
        )
        return admin_model.changeform_view(
            request,
            history_id,
            extra_context={
                'history_model_opts': self.model._meta,
                'history_object': obj,
            },
        )
