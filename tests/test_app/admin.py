from django.contrib import admin
from django.contrib.admin import register

from simple_log.admin import HistoryModelAdmin, SimpleLogModelAdmin
from simple_log.models import SimpleLog
from tests.test_app.models import (
    OtherModel,
    RelatedModel,
    TestModel,
    TestModelProxy,
    ThirdModel,
)
from tests.test_app.views import WrapViewMixin


class BaseModelAdmin(WrapViewMixin, HistoryModelAdmin):
    def _changeform_view(self, request, *args, **kwargs):
        return self._wrap_view(
            super(BaseModelAdmin, self)._changeform_view,
            request,
            *args,
            **kwargs
        )

    def _delete_view(self, request, *args, **kwargs):
        return self._wrap_view(
            super(BaseModelAdmin, self)._delete_view, request, *args, **kwargs
        )


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

