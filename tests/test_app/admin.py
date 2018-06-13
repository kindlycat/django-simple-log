from django.contrib import admin
from django.contrib.admin import register

from simple_log.admin import HistoryModelAdmin, SimpleLogModelAdmin
from simple_log.models import SimpleLog
from simple_log.utils import disable_logging, disable_related
from tests.test_app.models import (
    OtherModel, RelatedModel, TestModel, TestModelProxy, ThirdModel
)
from tests.utils import noop_ctx


class BaseModelAdmin(HistoryModelAdmin):
    def _changeform_view(self, request, object_id, form_url, extra_context):
        dl_ctx = 'disable_logging_context' in request.POST
        dl_dec = 'disable_logging_decorator' in request.POST
        dr_ctx = 'disable_related_context' in request.POST
        dr_dec = 'disable_related_decorator' in request.POST
        super_fn = super(BaseModelAdmin, self)._changeform_view
        with disable_logging() if dl_ctx else noop_ctx(), \
                disable_related() if dr_ctx else noop_ctx():
            if dl_dec:
                super_fn = disable_logging()(super_fn)
            if dr_dec:
                super_fn = disable_related()(super_fn)
            return super_fn(request, object_id, form_url, extra_context)

    def _delete_view(self, request, object_id, extra_context):
        dl_ctx = 'disable_logging_context' in request.POST
        dl_dec = 'disable_logging_decorator' in request.POST
        dr_ctx = 'disable_related_context' in request.POST
        dr_dec = 'disable_related_decorator' in request.POST
        super_fn = super(BaseModelAdmin, self)._delete_view
        with disable_logging() if dl_ctx else noop_ctx(), \
                disable_related() if dr_ctx else noop_ctx():
            if dl_dec:
                super_fn = disable_logging()(super_fn)
            if dr_dec:
                super_fn = disable_related()(super_fn)
            return super_fn(request, object_id, extra_context)


@register(TestModel)
class TestModelAdmin(BaseModelAdmin):
    pass


@register(TestModelProxy)
class TestModelAdminProxy(BaseModelAdmin):
    pass


@register(OtherModel)
class OtherModelAdmin(BaseModelAdmin):
    pass


class RelatedModelInline(admin.TabularInline):
    model = RelatedModel


@register(ThirdModel)
class ThirdModelAdmin(BaseModelAdmin):
    inlines = [RelatedModelInline]


admin.site.register(SimpleLog, SimpleLogModelAdmin)
