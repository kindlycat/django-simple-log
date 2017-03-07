# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from simple_log.models import SimpleLog
from tests.test_app.models import TestModel


class AdminTestCase(TestCase):
    model = TestModel

    def setUp(self):
        self.user = User.objects.create_superuser('user', 'test@example.com',
                                                  'pass')
        self.client.login(username='user', password='pass')
        self.add_url = reverse(
            'admin:{}_{}_add'.format(self.model._meta.app_label,
                                     self.model._meta.model_name)
        )

    def get_change_url(self, *args, **kwargs):
        return reverse(
            'admin:{}_{}_change'.format(self.model._meta.app_label,
                                        self.model._meta.model_name),
            *args, **kwargs
        )

    def test_add_object_check_log(self):
        initial_count = SimpleLog.objects.count()
        self.client.post(self.add_url)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
