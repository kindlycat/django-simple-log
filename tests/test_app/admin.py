from django.contrib import admin
from django.contrib.admin import register

from tests.test_app.models import OtherModel, TestModel


@register(TestModel)
class TestModelAdmin(admin.ModelAdmin):
    pass


@register(OtherModel)
class OtherModelAdmin(admin.ModelAdmin):
    pass
