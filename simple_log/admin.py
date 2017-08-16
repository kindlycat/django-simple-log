# -*- coding: utf-8 -*-
from django.contrib import admin


class SimpleLogModelAdmin(admin.ModelAdmin):
    list_display = ('object_repr', 'content_type', 'action_flag',
                    'action_time', 'user_repr', 'user_ip')
    list_filter = ('action_flag', 'content_type')
    search_fields = ('object_repr', 'user_repr', 'user_ip')
    change_form_template = 'simple_log/detail.html'

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
