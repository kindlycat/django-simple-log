from django.contrib import admin
from django.contrib.admin import register

from simple_log.admin import HistoryModelAdmin, SimpleLogModelAdmin
from simple_log.models import SimpleLog
from tests.test_app.models import (
    OtherModel, RelatedModel, TestModel, TestModelProxy, ThirdModel
)


@register(TestModel)
class TestModelAdmin(HistoryModelAdmin):
    pass


@register(TestModelProxy)
class TestModelAdminProxy(HistoryModelAdmin):
    pass


@register(OtherModel)
class OtherModelAdmin(HistoryModelAdmin):
    pass


class RelatedModelInline(admin.TabularInline):
    model = RelatedModel


@register(ThirdModel)
class ThirdModelAdmin(HistoryModelAdmin):
    inlines = [RelatedModelInline]


admin.site.register(SimpleLog, SimpleLogModelAdmin)
