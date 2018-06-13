# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.contrib import admin

from tests.test_app.models import (
    OtherModel, TestModel, TestModelProxy, ThirdModel
)
from tests.test_app.views import TestCreateView, TestDeleteView, TestUpdateView


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

for model in (TestModel, OtherModel, ThirdModel, TestModelProxy):
    urlpatterns += [
        url(
            r'^{}/add/$'.format(model._meta.model_name),
            TestCreateView.as_view(model=model),
            name='test_app_{}_add'.format(model._meta.model_name)
        ),
        url(
            r'^{}/(?P<pk>\d+)/$'.format(model._meta.model_name),
            TestUpdateView.as_view(model=model),
            name='test_app_{}_change'.format(model._meta.model_name)
        ),
        url(
            r'^{}/(?P<pk>\d+)/delete/$'.format(model._meta.model_name),
            TestDeleteView.as_view(model=model),
            name='test_app_{}_delete'.format(model._meta.model_name)
        ),
    ]
