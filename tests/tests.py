# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.transaction import atomic
from django.test import override_settings, TransactionTestCase
from django.utils import timezone
from django.utils.encoding import force_text

from simple_log.conf import settings
from simple_log.models import SimpleLog, SimpleLogAbstract
from simple_log.templatetags.simple_log_tags import get_type
from simple_log.utils import (
    get_fields, get_log_model, disable_logging, get_serializer, get_model_list,
    disable_related
)
from .test_app.models import (
    OtherModel, TestModel, SwappableLogModel, CustomSerializer,
    TestModelProxy, ThirdModel, RelatedModel
)
from .utils import isolate_lru_cache

try:
    from unittest import mock
except ImportError:
    import mock

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


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
        with disable_logging():
            params = {
                'char_field': 'test',
                'fk_field': self.other_model,
                'm2m_field': [self.other_model],
                'choice_field': TestModel.TWO
            }
            obj = self.add_object(TestModel, params)
            params = {
                'char_field': 'test2',
                'fk_field': '',
                'm2m_field': [],
                'choice_field': TestModel.ONE
            }
            self.change_object(obj, params)
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


class SettingsTestCase(TransactionTestCase):
    @override_settings(SIMPLE_LOG_MODEL_LIST=('test_app.OtherModel',))
    def test_model_list_add(self):
        with isolate_lru_cache(get_model_list):
            self.assertListEqual(get_model_list(), [OtherModel])

    @override_settings(SIMPLE_LOG_EXCLUDE_MODEL_LIST=('test_app.OtherModel',))
    def test_model_exclude_list_add(self):
        model_list = [
            x for x in apps.get_models()
            if not issubclass(x, SimpleLogAbstract) and x is not OtherModel
        ]
        with isolate_lru_cache(get_model_list):
            self.assertListEqual(get_model_list(), model_list)

    def test_model_serializer(self):
        custom_serializer = 'tests.test_app.models.CustomSerializer'
        with override_settings(SIMPLE_LOG_MODEL_SERIALIZER=custom_serializer):
            with isolate_lru_cache(get_serializer):
                self.assertEqual(get_serializer(TestModel), CustomSerializer)

        with override_settings(SIMPLE_LOG_MODEL_SERIALIZER=CustomSerializer):
            with isolate_lru_cache(get_serializer):
                self.assertEqual(get_serializer(TestModel), CustomSerializer)

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

    @override_settings(SIMPLE_LOG_MODEL='test_app.SwappableLogModel')
    def test_log_model(self):
        with isolate_lru_cache(get_log_model):
            self.assertIs(get_log_model(), SwappableLogModel)
            other_model = OtherModel.objects.create(char_field='other')
            initial_count = SwappableLogModel.objects.count()
            TestModel.objects.create(
                char_field='test',
                fk_field=other_model
            )
            sl = SwappableLogModel.objects.latest('pk')
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
                            'db': other_model.pk,
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
                            'db': TestModel.ONE,
                            'repr': 'One'
                        }
                    }
                }
            )

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

    @override_settings(SIMPLE_LOG_MODEL='test_app.BadLogModel')
    def test_log_model_not_subclass_simplelog(self):
        with isolate_lru_cache(get_log_model):
            msg = 'Log model should be subclass of SimpleLogAbstract.'
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
        all_models = [x for x in apps.get_models()
                      if not issubclass(x, SimpleLogAbstract)]
        with isolate_lru_cache(get_model_list):
            self.assertListEqual(get_model_list(), all_models)

    @override_settings(SIMPLE_LOG_OLD_INSTANCE_ATTR_NAME='old')
    def test_old_instance_attr_name(self):
        TestModel.objects.create(char_field='value')
        initial_count = SimpleLog.objects.count()
        obj = TestModel.objects.all()[0]
        obj.char_field = 'new value'
        obj.save()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        self.assertEqual(obj.old.pk, obj.pk)

    @override_settings(SIMPLE_LOG_PROXY_CONCRETE=True)
    def test_proxy_model_concrete(self):
        initial_count = SimpleLog.objects.count()
        TestModel.objects.create(char_field='test')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(
            sl.content_type,
            ContentType.objects.get_for_model(TestModelProxy, True)
        )

    @override_settings(SIMPLE_LOG_SAVE_ONLY_CHANGED=True)
    def test_only_changed(self):
        obj = TestModel.objects.create(
            char_field='test'
        )
        initial_count = SimpleLog.objects.count()
        obj = TestModel.objects.get(pk=obj.pk)
        obj.char_field = 'changed'
        obj.save()
        self.assertEqual(
            SimpleLog.objects.count(), initial_count + 1
        )
        sl = SimpleLog.objects.latest('pk')
        self.assertDictEqual(
            sl.old,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test'
                },
            }
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'changed'
                },
            }
        )

    @override_settings(
        SIMPLE_LOG_DATETIME_FORMAT='%d.%m.%Y [%H:%M]',
        SIMPLE_LOG_DATE_FORMAT='%d|%m|%Y',
        SIMPLE_LOG_TIME_FORMAT='%H/%M',
    )
    def test_dates_format(self):
        obj = OtherModel.objects.create(
            char_field='test',
            date_time_field=timezone.now(),
            date_field=timezone.now().date(),
            time_field=timezone.now().time(),
        )
        sl = SimpleLog.objects.latest('pk')
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {
                    'label': 'Char field',
                    'value': 'test'
                },
                'date_time_field': {
                    'label': 'Date time field',
                    'value': obj.date_time_field.strftime('%d.%m.%Y [%H:%M]')
                },
                'date_field': {
                    'label': 'Date field',
                    'value': obj.date_field.strftime('%d|%m|%Y')
                },
                'time_field': {
                    'label': 'Time field',
                    'value': obj.time_field.strftime('%H/%M')
                },
                'm2m_field': {
                    'label': 'm2m field',
                    'value': []
                },
                'test_entries_fk': {
                    'label': 'test entries',
                    'value': []
                },
            }
        )


class LogModelTestCase(TransactionTestCase):
    def test_log_get_edited_obj(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.get_edited_object(), obj)

    def test_get_admin_url(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.latest('pk')
        expected_url = reverse('admin:test_app_testmodel_change',
                               args=(quote(obj.pk),))
        self.assertEqual(sl.get_admin_url(), expected_url)
        self.assertIn(sl.get_admin_url(),
                      '/admin/test_app/testmodel/%d/change/' % obj.pk)
        sl.content_type.model = "nonexistent"
        self.assertIsNone(sl.get_admin_url())

    def test_log_str(self):
        TestModel.objects.create(char_field='test')
        obj = TestModel.objects.latest('pk')
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'added'))

        obj.char_field = 'test2'
        obj.save()
        obj = TestModel.objects.latest('pk')
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'changed'))

        obj.delete()
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '%s: %s' % (str(obj), 'deleted'))

    def test_log_changed_fields(self):
        TestModel.objects.create(char_field='test')
        obj = TestModel.objects.latest('pk')
        other_model = OtherModel.objects.create(char_field='test')
        params = {
            'char_field': 'test2',
            'fk_field': other_model,
            'choice_field': TestModel.TWO
        }
        for param, value in params.items():
            setattr(obj, param, value)
        obj.save()
        sl = SimpleLog.objects.latest('pk')
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
        with atomic():
            obj.m2m_field.add(other_model2)
            obj.m2m_field.remove(other_model)

        sl = SimpleLog.objects.latest('pk')
        added, removed = sl.m2m_field_diff('m2m_field')
        self.assertListEqual(added,
                             [{'db': other_model2.pk, 'repr': 'test2'}])
        self.assertListEqual(removed,
                             [{'db': other_model.pk, 'repr': 'test'}])

    def test_log_get_differences(self):
        TestModel.objects.create(char_field='test')
        obj = TestModel.objects.latest('pk')
        other_model = OtherModel.objects.create(char_field='test')
        params = {
            'char_field': 'test2',
            'fk_field': other_model,
            'choice_field': TestModel.TWO
        }
        for param, value in params.items():
            setattr(obj, param, value)
        obj.save()
        sl = SimpleLog.objects.latest('pk')
        differences = sl.get_differences()
        self.assertEqual(len(differences), 3)
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Char field'][0],
            {'label': 'Char field',
             'old': 'test',
             'new': 'test2'},
        )
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Fk field'][0],
            {'label': 'Fk field',
             'old': {'db': None, 'repr': ''},
             'new': {'db': other_model.pk, 'repr': str(other_model)}},
        )
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Choice field'][0],
            {'label': 'Choice field',
             'old': {'db': TestModel.ONE, 'repr': 'One'},
             'new': {'db': TestModel.TWO, 'repr': 'Two'}}
        )


class UtilsTestCase(TransactionTestCase):
    def test_get_type_templatetag(self):
        params = (
            ('string', 'str'),
            (None, 'None'),
            ({'a': 1}, 'dict'),
            (True, 'bool'),
            ([1, 2, 3], 'list'),
            (1, 'int'),
            (TestModel, str(type(TestModel))),
        )
        for value, type_of in params:
            self.assertEqual(get_type(value), type_of)
