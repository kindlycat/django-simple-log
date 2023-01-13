from django.contrib import admin
from django.urls import path

from tests.test_app.models import (
    OtherModel,
    RelatedModel,
    TestModel,
    TestModelProxy,
    ThirdModel,
)
from tests.test_app.views import TestCreateView, TestDeleteView, TestUpdateView


urlpatterns = [
    path('admin/', admin.site.urls),
]

for model in (TestModel, OtherModel, ThirdModel, RelatedModel, TestModelProxy):
    urlpatterns += [
        path(
            '{}/add/'.format(model._meta.model_name),
            TestCreateView.as_view(model=model),
            name='test_app_{}_add'.format(model._meta.model_name),
        ),
        path(
            '{}/<int:pk>/'.format(model._meta.model_name),
            TestUpdateView.as_view(model=model),
            name='test_app_{}_change'.format(model._meta.model_name),
        ),
        path(
            '{}/<int:pk>/delete/'.format(model._meta.model_name),
            TestDeleteView.as_view(model=model),
            name='test_app_{}_delete'.format(model._meta.model_name),
        ),
    ]
