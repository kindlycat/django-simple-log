# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.test import TransactionTestCase, override_settings
from django.test.utils import isolate_lru_cache
from django.urls import reverse
from django.utils.encoding import force_text

from simple_log.conf import settings
from simple_log.models import SimpleLog
from simple_log.utils import (
    disable_logging, disable_related, get_fields, get_serializer
)

from .test_app.models import (
    CustomSerializer, OtherModel, RelatedModel, TestModel, TestModelProxy,
    ThirdModel
)


try:
    from unittest import mock
except ImportError:
    import mock


class BaseTestCaseMixin(object):
    namespace = ''

    def setUp(self):
        self.create_initial_objects()
        self.user = User.objects.all()[0]
        self.user_repr = force_text(self.user)
        self.ip = '127.0.0.1'
        self.other_model = OtherModel.objects.all()[0]
        with disable_logging():
            self.client.login(username='user', password='pass')

    def create_initial_objects(self):
        with disable_logging():
            User.objects.create_superuser('user', 'test@example.com', 'pass')
            OtherModel.objects.create(char_field='other')
            tm = ThirdModel.objects.create(char_field='third')
            RelatedModel.objects.create(char_field='related', third_model=tm)

    def prepare_params(self, model, params):
        for k, v in params.items():
            if model._meta.get_field(k).many_to_many:
                params[k] = [x.pk for x in v]
            elif model._meta.get_field(k).is_relation:
                params[k] = v.pk
        return params

    @atomic
    def add_object(self, model, params, **kwargs):
        params = self.prepare_params(model, params)
        params.update(**kwargs.get('additional_params', {}))
        headers = kwargs.get('headers', {})
        self.client.post(self.get_add_url(model), data=params, **headers)
        return model.objects.latest('pk')

    @atomic
    def change_object(self, obj, params, **kwargs):
        headers = kwargs.pop('headers', {})
        params.update(**kwargs.get('additional_params', {}))
        self.client.post(
            self.get_change_url(obj._meta.model, obj.pk),
            data=params, **headers
        )
        return obj._meta.model.objects.get(pk=obj.pk)

    @atomic
    def delete_object(self, obj):
        self.client.post(self.get_delete_url(obj._meta.model, obj.pk),
                         data={'post': 'yes'})

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
        new_obj = self.add_object(TestModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.TWO,
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
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO
        }
        obj = self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.ONE,
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
                        'db': TestModel.TWO,
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
        obj = self.add_object(TestModel, params)
        obj_id = obj.id
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.TWO,
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
        new_obj = self.add_object(TestModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': other.pk,
                        'repr': force_text(other),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': other.pk,
                        'repr': force_text(other),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.ONE,
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
        obj = self.add_object(TestModel, params)
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
            sl = SimpleLog.objects.latest('pk')
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
            sl = SimpleLog.objects.latest('pk')
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertDictEqual(
                sl.new,
                {
                    'fk_field': {
                        'label': 'Fk field',
                        'value': {
                            'db': other_model.pk,
                            'repr': force_text(other_model)
                        }
                    },
                    'm2m_field': {
                        'label': 'M2m field',
                        'value': []
                    }
                }
            )

    @mock.patch.object(
        TestModel,
        'simple_log_serializer',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=CustomSerializer
    )
    def test_concrete_model_serializer(self, mocked):
        with isolate_lru_cache(get_serializer):
            self.assertEqual(get_serializer(TestModel), CustomSerializer)

    def test_log_bad_ip(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test'
        }
        self.add_object(TestModel, params,
                        headers={'HTTP_X_FORWARDED_FOR': '123'})
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        self.assertIsNone(sl.user_ip)

        self.add_object(TestModel, params, headers={'REMOTE_ADDR': '123'})
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        self.assertIsNone(sl.user_ip)

        self.add_object(TestModel, params,
                        headers={'REMOTE_ADDR': '123',
                                 'HTTP_X_FORWARDED_FOR': '123'})
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 3)
        self.assertIsNone(sl.user_ip)

    def test_disable_log(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        with disable_logging():
            obj = self.add_object(TestModel, params)
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.ONE
        }
        with disable_logging():
            self.change_object(obj, params)
        with disable_logging():
            self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count)

    def test_disable_related(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        obj = self.add_object(TestModel, params)
        with atomic():
            with disable_related():
                params = {
                    'char_field': 'test2',
                    'fk_field': '',
                    'm2m_field': [],
                    'choice_field': TestModel.ONE
                }
                self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

    def test_proxy_model(self):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        self.add_object(TestModelProxy, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(
            sl.content_type,
            ContentType.objects.get_for_model(TestModelProxy, False)
        )

    @mock.patch.object(
        TestModel,
        'simple_log_proxy_concrete',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=True
    )
    def test_concrete_model_proxy_concrete(self, mocked):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        self.add_object(TestModelProxy, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(
            sl.content_type,
            ContentType.objects.get_for_model(TestModelProxy, True)
        )

    def test_delete_with_related(self):
        initial_count = SimpleLog.objects.count()
        self.delete_object(ThirdModel.objects.first())
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(),
                                 [repr(second_sl)])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])


class AdminTestCase(BaseTestCaseMixin, TransactionTestCase):
    namespace = 'admin:'

    def test_add_object_with_formset(self):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline'
        }
        self.add_object(ThirdModel, params,
                        additional_params=additional_params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(),
                                 [repr(first_sl)])
        self.assertEqual(first_sl.user, second_sl.user)

    def test_change_object_only_formset(self):
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline'
        }
        obj = self.add_object(ThirdModel, params,
                              additional_params=additional_params)
        related = obj.related_entries.latest('pk')
        initial_count = SimpleLog.objects.count()
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 1,
            'related_entries-0-id': related.pk,
            'related_entries-0-char_field': 'changed_title',
        }
        self.change_object(obj, params, additional_params=additional_params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(),
                                 [repr(first_sl)])
        self.assertEqual(first_sl.user, second_sl.user)


class CustomViewTestCase(BaseTestCaseMixin, TransactionTestCase):
    def test_anonymous_add(self):
        self.client.logout()
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        new_obj = self.add_object(TestModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.TWO,
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
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO
        }
        obj = self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.ONE,
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
                        'db': TestModel.TWO,
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
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
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
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model),
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': TestModel.TWO,
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
        self.add_object(TestModel, params)
        sl = SimpleLog.objects.latest('pk')
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, 'UNKNOWN')


class SystemTestCase(BaseTestCaseMixin, TransactionTestCase):
    def setUp(self):
        self.create_initial_objects()
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

    @atomic
    def add_object(self, model, params, **kwargs):
        params, m2m = self.prepare_params(model, params)
        obj = model.objects.create(**params)
        for k, v in m2m.items():
            getattr(obj, k).add(*v)
        return model.objects.latest('pk')

    @atomic
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

    @atomic
    def delete_object(self, obj):
        obj.delete()

    @override_settings(SIMPLE_LOG_NONE_USER_REPR='GLaDOS')
    def test_system_change_repr(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO
        }
        self.add_object(TestModel, params)
        sl = SimpleLog.objects.latest('pk')
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, 'GLaDOS')

    def test_change_m2m(self):
        params = {
            'char_field': 'test',
            'm2m_field': [self.other_model],
        }
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()

        # clear
        obj.m2m_field.clear()
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
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
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model)
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
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
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': []
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
                        'repr': 'One'
                    }
                }
            }
        )

        # add
        obj = TestModel.objects.latest('pk')
        obj.m2m_field.add(self.other_model)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
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
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': []
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
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
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model)
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
                        'repr': 'One'
                    }
                }
            }
        )

        # delete
        obj = TestModel.objects.latest('pk')
        obj.m2m_field.remove(self.other_model)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 3)
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
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
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{
                        'db': self.other_model.pk,
                        'repr': force_text(self.other_model)
                    }]
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
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
                    'value': 'test'
                },
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': None,
                        'repr': ''
                    }
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': []
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {
                        'db': 1,
                        'repr': 'One'
                    }
                }
            }
        )

    @atomic
    def test_create_log_commit(self):
        initial_count = SimpleLog.objects.count()
        SimpleLog.log(self.other_model, action_flag=1, commit=False)
        self.assertEqual(SimpleLog.objects.count(), initial_count)

        initial_count = SimpleLog.objects.count()
        SimpleLog.log(self.other_model, action_flag=1)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
