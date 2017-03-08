# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from simple_log.models import SimpleLog
from tests.test_app.models import TestModel, OtherModel


class AdminTestCase(TestCase):
    model = TestModel

    def setUp(self):
        self.user = User.objects.create_superuser('user', 'test@example.com',
                                                  'pass')
        self.other_model = OtherModel.objects.create(char_field='other')
        self.client.login(username='user', password='pass')
        self.add_url = reverse(
            'admin:{}_{}_add'.format(self.model._meta.app_label,
                                     self.model._meta.model_name)
        )

    @classmethod
    def tearDown(cls):
        SimpleLog.objects.all().delete()

    def get_change_url(self, *args, **kwargs):
        return reverse(
            'admin:{}_{}_change'.format(self.model._meta.app_label,
                                        self.model._meta.model_name),
            args=args, kwargs=kwargs
        )

    def get_delete_url(self, *args, **kwargs):
        return reverse(
            'admin:{}_{}_delete'.format(self.model._meta.app_label,
                                        self.model._meta.model_name),
            args=args, kwargs=kwargs
        )

    def test_add_object_all_field_filled_check_log(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk]
        }
        self.client.post(self.add_url, data=params)
        new_obj = TestModel.objects.last()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, str(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, str(new_obj.id))
        self.assertEqual(sl.object_repr, str(new_obj))
        self.assertEqual(sl.content_type,
                         ContentType.objects.get_for_model(new_obj))
        self.assertIsNone(sl.old)
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }]
                }
            }
        )

    def test_change_object_all_field_filled_check_log(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk]
        }
        self.client.post(self.add_url, data=params)
        obj = TestModel.objects.last()
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': []
        }
        self.client.post(self.get_change_url(obj.pk), data=params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        obj.refresh_from_db()
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, str(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, str(obj.id))
        self.assertEqual(sl.object_repr, str(obj))
        self.assertEqual(sl.content_type,
                         ContentType.objects.get_for_model(obj))
        self.assertDictEqual(
            sl.old,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }]
                }
            }
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test2'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': None,
                        'repr': '',
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': []
                }
            }
        )

    def test_delete_object_check_log(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk]
        }
        self.client.post(self.add_url, data=params)
        obj = TestModel.objects.last()
        initial_count = SimpleLog.objects.count()
        self.client.post(self.get_delete_url(obj.pk), data={'post': 'yes'})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.DELETE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, str(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, str(obj.id))
        self.assertEqual(sl.object_repr, str(obj))
        self.assertEqual(sl.content_type,
                         ContentType.objects.get_for_model(obj))
        self.assertIsNone(sl.new)
        self.assertDictEqual(
            sl.old,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': str(self.other_model.pk),
                        'repr': str(self.other_model),
                    }]
                }
            }
        )
