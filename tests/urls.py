# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url
from django.contrib import admin
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView

from tests.test_app.models import (
    TestModel, OtherModel, TestModelProxy, ThirdModel
)

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(
        r'^test_model/add/$',
        CreateView.as_view(
            model=TestModel,
            fields='__all__',
            success_url='.',
            template_name='form.html'
        ),
        name='test_app_testmodel_add'
    ),
    url(
        r'^test_model/(?P<pk>\d+)/$',
        UpdateView.as_view(
            model=TestModel,
            fields='__all__',
            success_url='.',
            template_name='form.html'
        ),
        name='test_app_testmodel_change'
    ),
    url(
        r'^test_model/(?P<pk>\d+)/delete/$',
        DeleteView.as_view(
            model=TestModel,
            success_url='.'
        ),
        name='test_app_testmodel_delete'
    ),

    url(
        r'^other_model/add/$',
        CreateView.as_view(
            model=OtherModel,
            fields='__all__',
            success_url='.',
            template_name='form.html'
        ),
        name='test_app_othermodel_add'
    ),
    url(
        r'^other_model/(?P<pk>\d+)/$',
        UpdateView.as_view(
            model=OtherModel,
            fields='__all__',
            success_url='.',
            template_name='form.html'
        ),
        name='test_app_othermodel_change'
    ),
    url(
        r'^other_model/(?P<pk>\d+)/delete/$',
        DeleteView.as_view(
            model=OtherModel,
            success_url='.'
        ),
        name='test_app_othermodel_delete'
    ),

    url(
        r'^third_model/(?P<pk>\d+)/delete/$',
        DeleteView.as_view(
            model=ThirdModel,
            success_url='.'
        ),
        name='test_app_thirdmodel_delete'
    ),

    url(
        r'^test_model_proxy/add/$',
        CreateView.as_view(
            model=TestModelProxy,
            fields='__all__',
            success_url='.',
            template_name='form.html'
        ),
        name='test_app_testmodelproxy_add'
    ),
]
