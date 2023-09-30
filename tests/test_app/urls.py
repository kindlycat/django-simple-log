from django.contrib import admin

from tests.test_app.models import (
    OtherModel,
    RelatedModel,
    TestModel,
    TestModelProxy,
    ThirdModel,
)
from tests.test_app.views import TestCreateView, TestDeleteView, TestUpdateView


try:
    from django.conf.urls import url
except ImportError:
    # django < 4.0
    from django.urls import re_path as url


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

for model in (TestModel, OtherModel, ThirdModel, RelatedModel, TestModelProxy):
    urlpatterns += [
        url(
            r'^{}/add/$'.format(model._meta.model_name),
            TestCreateView.as_view(model=model),
            name='test_app_{}_add'.format(model._meta.model_name),
        ),
        url(
            r'^{}/(?P<pk>\d+)/$'.format(model._meta.model_name),
            TestUpdateView.as_view(model=model),
            name='test_app_{}_change'.format(model._meta.model_name),
        ),
        url(
            r'^{}/(?P<pk>\d+)/delete/$'.format(model._meta.model_name),
            TestDeleteView.as_view(model=model),
            name='test_app_{}_delete'.format(model._meta.model_name),
        ),
    ]
