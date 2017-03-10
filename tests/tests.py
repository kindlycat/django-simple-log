# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.test.utils import isolate_lru_cache
from django.utils.encoding import force_text

from simple_log.utils import (
    get_models_for_log, get_fields, get_simple_log_model
)

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

try:
    from unittest import mock
except ImportError:
    import mock

from simple_log.models import SimpleLog
from simple_log.conf import settings
from .test_app.models import TestModel, OtherModel, CustomSimpleLog


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

    def test_add_object_all_field_filled(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk],
            'choice_field': TestModel.TWO
        }
        self.client.post(self.add_url, data=params)
        new_obj = TestModel.objects.last()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, force_text(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, force_text(new_obj.id))
        self.assertEqual(sl.object_repr, force_text(new_obj))
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
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': force_text(TestModel.TWO),
                        'repr': 'Two'
                    }
                }
            }
        )

    def test_change_object_all_field_filled(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk],
            'choice_field': TestModel.ONE
        }
        self.client.post(self.add_url, data=params)
        obj = TestModel.objects.last()
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO
        }
        self.client.post(self.get_change_url(obj.pk), data=params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        obj.refresh_from_db()
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, force_text(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, force_text(obj.id))
        self.assertEqual(sl.object_repr, force_text(obj))
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
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': force_text(TestModel.ONE),
                        'repr': 'One'
                    }
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
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': force_text(TestModel.TWO),
                        'repr': 'Two'
                    }
                }
            }
        )

    def test_delete_object_check_log(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk],
            'choice_field': TestModel.TWO
        }
        self.client.post(self.add_url, data=params)
        obj = TestModel.objects.last()
        initial_count = SimpleLog.objects.count()
        self.client.post(self.get_delete_url(obj.pk), data={'post': 'yes'})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.DELETE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, force_text(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, force_text(obj.id))
        self.assertEqual(sl.object_repr, force_text(obj))
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
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': force_text(self.other_model.pk),
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': force_text(TestModel.TWO),
                        'repr': 'Two'
                    }
                }
            }
        )

    def test_add_object_with_unicode(self):
        other = OtherModel.objects.create(char_field='★')
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': '★',
            'fk_field': other.pk,
            'm2m_field': [other.pk],
            'choice_field': TestModel.ONE
        }
        self.client.post(self.add_url, data=params)
        new_obj = TestModel.objects.last()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, force_text(self.user))
        self.assertEqual(sl.user_ip, '127.0.0.1')
        self.assertEqual(sl.object_id, force_text(new_obj.id))
        self.assertEqual(sl.object_repr, force_text(new_obj))
        self.assertEqual(sl.content_type,
                         ContentType.objects.get_for_model(new_obj))
        self.assertIsNone(sl.old)
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': '★'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': force_text(other.pk),
                        'repr': force_text(other),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': force_text(other.pk),
                        'repr': force_text(other),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': force_text(TestModel.ONE),
                        'repr': 'One'
                    }
                }
            }
        )

    def test_no_change_no_log(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model.pk,
            'm2m_field': [self.other_model.pk],
            'choice_field': TestModel.ONE
        }
        self.client.post(self.add_url, data=params)
        obj = TestModel.objects.last()
        initial_count = SimpleLog.objects.count()
        self.client.post(self.get_change_url(obj.pk), data=params)
        self.assertEqual(SimpleLog.objects.count(), initial_count)

    @mock.patch.object(
        TestModel,
        'simple_log_fields',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=('char_field',)
    )
    def test_concrete_model_fields_add(self, mocked):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(
                char_field='test',
                fk_field=other_model
            )
            sl = SimpleLog.objects.first()
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertDictEqual(
                sl.new,
                {
                    'char_field': {
                        'label': 'Char field',
                        'value': 'test'
                    }
                }
            )

    @mock.patch.object(
        TestModel,
        'simple_log_exclude_fields',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=('id', 'char_field', 'choice_field')
    )
    def test_concrete_model_exclude_fields_add(self, mocked):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(
                char_field='test',
                fk_field=other_model
            )
            sl = SimpleLog.objects.first()
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertDictEqual(
                sl.new,
                {
                    'fk_field': {
                        'label': 'Fk field',
                        'value': {
                            'db': force_text(other_model.pk),
                            'repr': force_text(other_model)
                        }
                    },
                    'm2m_field': {
                        'label': 'M2m field',
                        'value': []
                    }
                }
            )


class SettingsTestCase(TestCase):
    model = TestModel

    @classmethod
    def tearDown(cls):
        SimpleLog.objects.all().delete()

    @override_settings(SIMPLE_LOG_MODEL_LIST=('test_app.OtherModel',))
    def test_model_list_add(self):
        with isolate_lru_cache(get_models_for_log):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(char_field='test')
            self.assertEqual(SimpleLog.objects.count(), initial_count)

            initial_count = SimpleLog.objects.count()
            OtherModel.objects.create(char_field='test')
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)

    @override_settings(SIMPLE_LOG_EXCLUDE_MODEL_LIST=('test_app.OtherModel',))
    def test_model_exclude_list_add(self):
        with isolate_lru_cache(get_models_for_log):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(char_field='test')
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)

            initial_count = SimpleLog.objects.count()
            OtherModel.objects.create(char_field='test')
            self.assertEqual(SimpleLog.objects.count(), initial_count)

    @override_settings(
        SIMPLE_LOG_EXCLUDE_FIELD_LIST=(
            'id', 'char_field', 'choice_field'
        )
    )
    def test_field_list_add(self):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(
                char_field='test',
                fk_field=other_model
            )
            sl = SimpleLog.objects.first()
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertDictEqual(
                sl.new,
                {
                    'fk_field': {
                        'label': 'Fk field',
                        'value': {
                            'db': force_text(other_model.pk),
                            'repr': force_text(other_model)
                        }
                    },
                    'm2m_field': {
                        'label': 'M2m field',
                        'value': []
                    }
                }
            )

    @override_settings(SIMPLE_LOG_MODEL='test_app.CustomSimpleLog')
    def test_log_model(self):
        with isolate_lru_cache(get_simple_log_model):
            self.assertIs(get_simple_log_model(), CustomSimpleLog)

    @override_settings(SIMPLE_LOG_MODEL=111)
    def test_log_model_wrong_value(self):
        with isolate_lru_cache(get_simple_log_model):
            with self.assertRaises(ImproperlyConfigured) as e:
                get_simple_log_model()
            self.assertEqual(
                force_text(e.exception),
                "SIMPLE_LOG_MODEL must be of the form 'app_label.model_name'"
            )

    @override_settings(SIMPLE_LOG_MODEL='not_exist.Model')
    def test_log_model_not_exist(self):
        with isolate_lru_cache(get_simple_log_model):
            with self.assertRaises(ImproperlyConfigured) as e:
                get_simple_log_model()
            self.assertEqual(
                force_text(e.exception),
                "SIMPLE_LOG_MODEL refers to model 'not_exist.Model' that has "
                "not been installed"
            )

    def test_settings_object(self):
        # Get wrong attribute
        with self.assertRaises(AttributeError) as e:
            test = settings.NOT_EXIST_ATTRIBUTE
        self.assertEqual(
            force_text(e.exception),
            "'Settings' object has no attribute 'NOT_EXIST_ATTRIBUTE'"
        )

        # Override settings, skip not SIMPLE_LOG settings
        with override_settings(SOME_SETTING=111):
            self.assertIsNone(getattr(settings, 'SOME_SETTING', None))

        # Override settings, ignore not in defaults
        with override_settings(SIMPLE_LOG_SOME_SETTING=111):
            self.assertIsNone(getattr(settings, 'SIMPLE_LOG_SOME_SETTING',
                                      None))
