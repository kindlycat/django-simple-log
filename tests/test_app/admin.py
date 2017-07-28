from django.contrib import admin
from django.contrib.admin import register

from tests.test_app.models import (
    OtherModel, TestModel, TestModelProxy, RelatedModel,
    ThirdModel
)


@register(TestModel)
class TestModelAdmin(admin.ModelAdmin):
    pass


@register(TestModelProxy)
class TestModelAdminProxy(admin.ModelAdmin):
    pass


@register(OtherModel)
class OtherModelAdmin(admin.ModelAdmin):
    pass


class RelatedModelInline(admin.TabularInline):
    model = RelatedModel


@register(ThirdModel)
class ThirdModelAdmin(admin.ModelAdmin):
    inlines = [RelatedModelInline]
