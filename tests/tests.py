# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager

from threading import local

from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db.models.signals import (
    post_save, pre_save, post_delete, m2m_changed
)
from django.test import override_settings, TestCase
from django.test.utils import isolate_lru_cache, modify_settings
from django.utils.encoding import force_text

from simple_log import register
from simple_log.conf import settings
from simple_log.models import SimpleLog
from simple_log.signals import (
    log_pre_save_delete, log_post_save, log_post_delete, log_m2m_change
)
from simple_log import utils
from simple_log.utils import (
    get_fields, get_models_for_log, get_log_model
)
from simple_log import middleware
from .test_app.models import OtherModel, TestModel

try:
    from unittest import mock
except ImportError:
    import mock

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


@contextmanager
def disconnect_signals(sender=None):
    pre_save.disconnect(receiver=log_pre_save_delete, sender=sender)
    post_save.disconnect(receiver=log_post_save, sender=sender)
    post_delete.disconnect(receiver=log_post_delete, sender=sender)
    m2m_changed.disconnect(receiver=log_m2m_change, sender=sender)


class BaseTestCaseMixin(object):
    model = TestModel
    namespace = ''

    def prepare_params(self, model, params):
        for k, v in params.items():
            if model._meta.get_field(k).many_to_many:
                params[k] = [x.pk for x in v]
            elif model._meta.get_field(k).is_relation:
                params[k] = v.pk
        return params

    def setUp(self):
        self.user = User.objects.all()[0]
        self.user_repr = force_text(self.user)
        self.ip = '127.0.0.1'
        self.other_model = OtherModel.objects.all()[0]
        self.client.login(username='user', password='pass')

    @classmethod
    def tearDown(cls):
        SimpleLog.objects.all().delete()

    def add_object(self, model, params, **kwargs):
        params = self.prepare_params(model, params)
        headers = kwargs.get('headers', {})
        self.client.post(self.get_add_url(self.model), data=params, **headers)
        return self.model.objects.last()

    def change_object(self, obj, params, **kwargs):
        headers = kwargs.get('headers', {})
        self.client.post(
            self.get_change_url(obj._meta.model, obj.pk),
            data=params, **headers
        )
        return obj._meta.model.objects.get(pk=obj.pk)

    def delete_object(self, obj):
        self.client.post(self.get_delete_url(obj._meta.model, obj.pk),
                         data={'post': 'yes'})

    @classmethod
    def setUpTestData(cls):
        User.objects.create_superuser('user', 'test@example.com', 'pass')
        OtherModel.objects.create(char_field='other')

    def get_add_url(self, model):
        return reverse(
            '{}{}_{}_add'.format(self.namespace, model._meta.app_label,
                                 model._meta.model_name)
        )

    def get_change_url(self, model, *args, **kwargs):
        return reverse(
            '{}{}_{}_change'.format(self.namespace, model._meta.app_label,
                                    model._meta.model_name),
            args=args, kwargs=kwargs
        )

    def get_delete_url(self, model, *args, **kwargs):
        return reverse(
            '{}{}_{}_delete'.format(self.namespace, model._meta.app_label,
                                    model._meta.model_name),
            args=args, kwargs=kwargs
        )

    def test_add_object_all_field_filled(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        new_obj = self.add_object(self.model, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
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
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.ONE
        }
        obj = self.add_object(self.model, params)
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO
        }
        obj = self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
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

    def test_delete_object(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        obj = self.add_object(self.model, params)
        obj_id = obj.id
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.DELETE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_text(obj_id))
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
            'fk_field': other,
            'm2m_field': [other],
            'choice_field': TestModel.ONE
        }
        new_obj = self.add_object(self.model, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
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
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.ONE
        }
        obj = self.add_object(self.model, params)
        initial_count = SimpleLog.objects.count()
        self.change_object(obj, params)
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

    def test_register_concrete_model(self):
        disconnect_signals()
        try:
            with isolate_lru_cache(get_models_for_log):
                register(TestModel)
                initial_count = SimpleLog.objects.count()
                params = {
                    'char_field': 'test',
                }
                self.add_object(self.model, params)
                self.assertEqual(SimpleLog.objects.count(), initial_count + 1)

                params['m2m_field'] = [TestModel.objects.all()[0]]
                initial_count = SimpleLog.objects.count()
                self.add_object(OtherModel, params)
                self.assertEqual(SimpleLog.objects.count(), initial_count)
                self.assertListEqual(get_models_for_log(), [TestModel])
        except Exception:
            raise
        finally:
            disconnect_signals(TestModel)
            utils.registered_models.clear()
            register()

    @modify_settings(INSTALLED_APPS={'append': 'tests.swappable'})
    def test_register_with_custom_log_model(self):
        disconnect_signals()
        try:
            call_command('migrate', verbosity=0, run_syncdb=True)
            from .swappable.models import CustomLogModel
            with isolate_lru_cache(get_log_model):
                register(TestModel, log_model=CustomLogModel)
                sl_initial_count = SimpleLog.objects.count()
                initial_count = CustomLogModel.objects.count()
                params = {
                    'char_field': 'test',
                    'fk_field': self.other_model,
                    'm2m_field': [self.other_model],
                    'choice_field': TestModel.TWO
                }
                self.add_object(self.model, params)
                self.assertEqual(SimpleLog.objects.count(), sl_initial_count)
                self.assertEqual(CustomLogModel.objects.count(),
                                 initial_count + 1)
        except Exception:
            raise
        finally:
            disconnect_signals(TestModel)
            utils.registered_models.clear()
            register()

    def test_log_bad_ip(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test'
        }
        self.add_object(self.model, params, headers={'HTTP_X_REAL_IP': '123'})
        sl = SimpleLog.objects.first()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        self.assertIsNone(sl.user_ip)

        self.add_object(self.model, params, headers={'REMOTE_ADDR': '123'})
        sl = SimpleLog.objects.first()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        self.assertIsNone(sl.user_ip)

        self.add_object(self.model, params,
                        headers={'REMOTE_ADDR': '123',
                                 'HTTP_X_FORWARDED_FOR': '123'})
        sl = SimpleLog.objects.first()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 3)
        self.assertIsNone(sl.user_ip)


class AdminTestCase(BaseTestCaseMixin, TestCase):
    namespace = 'admin:'


class CustomViewTestCase(BaseTestCaseMixin, TestCase):
    def test_anonymous_add(self):
        self.client.logout()
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        new_obj = self.add_object(self.model, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
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

    def test_anonymous_change(self):
        self.client.logout()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.ONE
        }
        obj = self.add_object(self.model, params)
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO
        }
        obj = self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
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

    def test_anonymous_delelte(self):
        self.client.logout()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        obj = self.add_object(self.model, params)
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.action_flag, SimpleLog.DELETE)
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
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

    @override_settings(SIMPLE_LOG_ANONYMOUS_REPR='UNKNOWN')
    def test_anonymous_change_repr(self):
        self.client.logout()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        self.add_object(self.model, params)
        sl = SimpleLog.objects.first()
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, 'UNKNOWN')


class SystemTestCase(BaseTestCaseMixin, TestCase):
    def setUp(self):
        middleware._thread_locals = local()
        self.user = None
        self.user_repr = 'System'
        self.ip = None
        self.other_model = OtherModel.objects.all()[0]

    def prepare_params(self, model, params):
        new_params = {}
        m2m = {}
        for k, v in params.items():
            if model._meta.get_field(k).many_to_many:
                m2m[k] = v
            elif model._meta.get_field(k).is_relation:
                new_params[k] = v if v else None
            else:
                new_params[k] = v
        return new_params, m2m

    def add_object(self, model, params, **kwargs):
        params, m2m = self.prepare_params(model, params)
        obj = model.objects.create(**params)
        for k, v in m2m.items():
            getattr(obj, k).add(*v)
        return obj

    def change_object(self, obj, params, **kwargs):
        params, m2m = self.prepare_params(obj._meta.model, params)
        for k, v in params.items():
            setattr(obj, k, v)
        obj.save()
        for k, v in m2m.items():
            if not v:
                getattr(obj, k).clear()
            else:
                getattr(obj, k).add(*v)
        return obj._meta.model.objects.get(pk=obj.pk)

    def delete_object(self, obj):
        obj.delete()


class SettingsTestCase(TestCase):
    model = TestModel

    @classmethod
    def tearDown(cls):
        SimpleLog.objects.all().delete()

    @override_settings(SIMPLE_LOG_MODEL_LIST=('test_app.OtherModel',))
    def test_model_list_add(self):
        with isolate_lru_cache(get_models_for_log):
            initial_count = SimpleLog.objects.count()
            other_obj = OtherModel.objects.create(char_field='test')
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertListEqual(get_models_for_log(), [OtherModel])

            initial_count = SimpleLog.objects.count()
            obj = TestModel.objects.create(char_field='test')
            obj.m2m_field.add(other_obj)
            self.assertEqual(SimpleLog.objects.count(), initial_count)

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

    @override_settings(SIMPLE_LOG_MODEL='swappable.SwappableLogModel')
    @modify_settings(INSTALLED_APPS={'append': 'tests.swappable'})
    def test_log_model(self):
        call_command('migrate', verbosity=0, run_syncdb=True)
        from .swappable.models import SwappableLogModel
        with isolate_lru_cache(get_log_model):
            self.assertIs(get_log_model(), SwappableLogModel)
            other_model = OtherModel.objects.create(char_field='other')
            initial_count = SwappableLogModel.objects.count()
            TestModel.objects.create(
                char_field='test',
                fk_field=other_model
            )
            sl = SwappableLogModel.objects.first()
            self.assertEqual(
                SwappableLogModel.objects.count(),
                initial_count + 1
            )
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
                            'db': force_text(other_model.pk),
                            'repr': force_text(other_model),
                        }
                    },
                    'm2m_field': {
                        'label': 'M2m field',
                        'value': []
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
        SwappableLogModel.objects.all().delete()

    @override_settings(SIMPLE_LOG_MODEL=111)
    def test_log_model_wrong_value(self):
        with isolate_lru_cache(get_log_model):
            msg = "SIMPLE_LOG_MODEL must be of the form 'app_label.model_name'"
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                get_log_model()

    @override_settings(SIMPLE_LOG_MODEL='not_exist.Model')
    def test_log_model_not_exist(self):
        with isolate_lru_cache(get_log_model):
            msg = "SIMPLE_LOG_MODEL refers to model 'not_exist.Model' " \
                  "that has not been installed"
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                get_log_model()

    def test_settings_object(self):
        # Get wrong attribute
        msg = "'Settings' object has no attribute 'NOT_EXIST_ATTRIBUTE'"
        with self.assertRaisesMessage(AttributeError, msg):
            getattr(settings, 'NOT_EXIST_ATTRIBUTE')

        # Override settings, skip not SIMPLE_LOG settings
        with override_settings(SOME_SETTING=111):
            self.assertIsNone(getattr(settings, 'SOME_SETTING', None))

        # Override settings, ignore not in defaults
        with override_settings(SIMPLE_LOG_SOME_SETTING=111):
            self.assertIsNone(getattr(settings, 'SIMPLE_LOG_SOME_SETTING',
                                      None))

    @override_settings(
        SIMPLE_LOG_MODEL_LIST=(),
        SIMPLE_LOG_EXCLUDE_MODEL_LIST=(),
    )
    def test_log_all_models(self):
        all_models = [x for x in apps.get_models() if x != SimpleLog]
        with isolate_lru_cache(get_models_for_log):
            self.assertListEqual(get_models_for_log(), all_models)


class LogModelTestCase(TestCase):
    @classmethod
    def tearDown(cls):
        SimpleLog.objects.all().delete()

    def test_log_get_edited_obj(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.first()
        self.assertEqual(sl.get_edited_object(), obj)

    def test_log_str(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.first()
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'added'))

        obj.char_field = 'test2'
        obj.save()
        sl = SimpleLog.objects.first()
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'changed'))

        obj.delete()
        sl = SimpleLog.objects.first()
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'deleted'))

    def test_log_changed_fields(self):
        obj = TestModel.objects.create(char_field='test')
        other_model = OtherModel.objects.create(char_field='test')
        params = {
            'char_field': 'test2',
            'fk_field': other_model,
            'choice_field': TestModel.TWO
        }
        for param, value in params.items():
            setattr(obj, param, value)
        obj.save()
        sl = SimpleLog.objects.first()
        self.assertDictEqual(
            sl.changed_fields,
            {
                'char_field': 'Char field',
                'fk_field': 'Fk field',
                'choice_field': 'Choice field'
            }
        )

    def test_log_m2m_diff(self):
        other_model = OtherModel.objects.create(char_field='test')
        other_model2 = OtherModel.objects.create(char_field='test2')
        obj = TestModel.objects.create(char_field='test')
        obj.m2m_field.add(other_model)
        obj = TestModel.objects.get(pk=obj.pk)
        obj.m2m_field.add(other_model2)
        obj.m2m_field.remove(other_model)
        sl = SimpleLog.objects.first()
        added, removed = sl.m2m_field_diff('m2m_field')

        self.assertListEqual(added,
                             [{'db': str(other_model2.pk), 'repr': 'test2'}])
        self.assertListEqual(removed,
                             [{'db': str(other_model.pk), 'repr': 'test'}])
