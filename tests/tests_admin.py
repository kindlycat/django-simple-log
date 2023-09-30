from unittest import mock

import django
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase
from django.test.utils import isolate_lru_cache
from django.urls import reverse
from django.utils.encoding import force_str

from simple_log.models import SimpleLog
from simple_log.utils import disable_logging, get_fields, get_serializer

from .test_app.models import (
    CustomSerializer,
    OtherModel,
    RelatedModel,
    TestModel,
    TestModelProxy,
    ThirdModel,
)


class AdminTestCase(TransactionTestCase):
    namespace = 'admin:'

    def setUp(self):
        self.create_initial_objects()
        self.user = User.objects.all()[0]
        self.user_repr = force_str(self.user)
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

    def assertQuerySetEqual(self, *args, **kwargs):
        if django.get_version() > '4.2':
            func = super().assertQuerySetEqual
        else:
            func = self.assertQuerysetEqual
        return func(*args, **kwargs)

    def prepare_params(self, model, params):
        for k, v in [(k, v) for k, v in params.items() if v]:
            if model._meta.get_field(k).many_to_many:
                params[k] = [x.pk for x in v]
            elif model._meta.get_field(k).is_relation:
                params[k] = v.pk
        return params

    def add_object(self, model, params, **kwargs):
        params = params.copy()
        params = self.prepare_params(model, params)
        params.update(**kwargs.get('additional_params', {}))
        headers = kwargs.get('headers', {})
        self.client.post(self.get_add_url(model), data=params, **headers)
        return model.objects.latest('pk')

    def change_object(self, obj, params, **kwargs):
        params = params.copy()
        params = self.prepare_params(obj.__class__, params)
        headers = kwargs.pop('headers', {})
        params.update(**kwargs.get('additional_params', {}))
        self.client.post(
            self.get_change_url(obj._meta.model, obj.pk),
            data=params,
            **headers
        )
        return obj._meta.model.objects.get(pk=obj.pk)

    def delete_object(self, obj, params=None):
        data = {'post': 'yes'}
        data.update(params or {})
        self.client.post(
            self.get_delete_url(obj._meta.model, obj.pk), data=data
        )

    def get_add_url(self, model):
        return reverse(
            '{}{}_{}_add'.format(
                self.namespace, model._meta.app_label, model._meta.model_name
            )
        )

    def get_change_url(self, model, *args, **kwargs):
        return reverse(
            '{}{}_{}_change'.format(
                self.namespace, model._meta.app_label, model._meta.model_name
            ),
            args=args,
            kwargs=kwargs,
        )

    def get_delete_url(self, model, *args, **kwargs):
        return reverse(
            '{}{}_{}_delete'.format(
                self.namespace, model._meta.app_label, model._meta.model_name
            ),
            args=args,
            kwargs=kwargs,
        )

    def test_add_object_all_field_filled(self):
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
        }
        new_obj = self.add_object(TestModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_str(new_obj.id))
        self.assertEqual(sl.object_repr, force_str(new_obj))
        self.assertEqual(
            sl.content_type, ContentType.objects.get_for_model(new_obj)
        )
        self.assertIsNone(sl.old)
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': self.other_model.pk,
                        'repr': force_str(self.other_model),
                    },
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_str(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': TestModel.TWO, 'repr': 'Two'},
                },
            },
        )

    def test_change_object_all_field_filled(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.ONE,
        }
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.TWO,
        }
        obj = self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_str(obj.id))
        self.assertEqual(sl.object_repr, force_str(obj))
        self.assertEqual(
            sl.content_type, ContentType.objects.get_for_model(obj)
        )
        self.assertDictEqual(
            sl.old,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': self.other_model.pk,
                        'repr': force_str(self.other_model),
                    },
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_str(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': TestModel.ONE, 'repr': 'One'},
                },
            },
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': 'test2'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {'label': 'M2m field', 'value': []},
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': TestModel.TWO, 'repr': 'Two'},
                },
            },
        )

    def test_delete_object(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
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
        self.assertEqual(sl.object_id, force_str(obj_id))
        self.assertEqual(sl.object_repr, force_str(obj))
        self.assertEqual(
            sl.content_type, ContentType.objects.get_for_model(obj)
        )
        self.assertIsNone(sl.new)
        self.assertDictEqual(
            sl.old,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {
                        'db': self.other_model.pk,
                        'repr': force_str(self.other_model),
                    },
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_str(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': TestModel.TWO, 'repr': 'Two'},
                },
            },
        )

    def test_add_object_with_unicode(self):
        other = OtherModel.objects.create(char_field='★')
        initial_count = SimpleLog.objects.count()
        params = {
            'char_field': '★',
            'fk_field': other,
            'm2m_field': [other],
            'choice_field': TestModel.ONE,
        }
        new_obj = self.add_object(TestModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.action_flag, SimpleLog.ADD)
        self.assertEqual(sl.user, self.user)
        self.assertEqual(sl.user_repr, self.user_repr)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_str(new_obj.id))
        self.assertEqual(sl.object_repr, force_str(new_obj))
        self.assertEqual(
            sl.content_type, ContentType.objects.get_for_model(new_obj)
        )
        self.assertIsNone(sl.old)
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': '★'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': other.pk, 'repr': force_str(other)},
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [{'db': other.pk, 'repr': force_str(other)}],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': TestModel.ONE, 'repr': 'One'},
                },
            },
        )

    def test_no_change_no_log(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.ONE,
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
        return_value=('char_field',),
    )
    def test_concrete_model_fields_add(self, mocked):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            self.add_object(
                TestModel, {'char_field': 'test', 'fk_field': other_model}
            )
            sl = SimpleLog.objects.latest('pk')
            self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
            self.assertDictEqual(
                sl.new,
                {'char_field': {'label': 'Char field', 'value': 'test'}},
            )

    @mock.patch.object(
        TestModel,
        'simple_log_exclude_fields',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=('id', 'char_field', 'choice_field'),
    )
    def test_concrete_model_exclude_fields_add(self, mocked):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            self.add_object(
                TestModel, {'char_field': 'test', 'fk_field': other_model}
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
                            'repr': force_str(other_model),
                        },
                    },
                    'm2m_field': {'label': 'M2m field', 'value': []},
                },
            )

    @mock.patch.object(
        TestModel,
        'simple_log_serializer',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=CustomSerializer,
    )
    def test_concrete_model_serializer(self, mocked):
        with isolate_lru_cache(get_serializer):
            self.assertEqual(get_serializer(TestModel), CustomSerializer)

    def test_log_bad_ip(self):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        self.add_object(
            TestModel, params, headers={'HTTP_X_FORWARDED_FOR': '123'}
        )
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        self.assertIsNone(sl.user_ip)

        self.add_object(TestModel, params, headers={'REMOTE_ADDR': '123'})
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        self.assertIsNone(sl.user_ip)

        self.add_object(
            TestModel,
            params,
            headers={'REMOTE_ADDR': '123', 'HTTP_X_FORWARDED_FOR': '123'},
        )
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(SimpleLog.objects.count(), initial_count + 3)
        self.assertIsNone(sl.user_ip)

    def test_disable_logging(self):
        initial_count = SimpleLog.objects.count()

        # test as context manager
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
        }
        obj = self.add_object(
            TestModel,
            params,
            additional_params={'disable_logging_context': True},
        )
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.ONE,
        }
        self.change_object(
            obj, params, additional_params={'disable_logging_context': True}
        )
        self.delete_object(obj, {'disable_logging_context': True})

        # test as decorator
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
        }
        obj = self.add_object(
            TestModel,
            params,
            additional_params={'disable_logging_decorator': True},
        )
        params = {
            'char_field': 'test2',
            'fk_field': '',
            'm2m_field': [],
            'choice_field': TestModel.ONE,
        }
        self.change_object(
            obj, params, additional_params={'disable_logging_decorator': True}
        )
        self.delete_object(obj, {'disable_logging_decorator': True})

        self.assertEqual(SimpleLog.objects.count(), initial_count)

    def test_proxy_model(self):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        self.add_object(TestModelProxy, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(
            sl.content_type,
            ContentType.objects.get_for_model(TestModelProxy, False),
        )

    @mock.patch.object(
        TestModel,
        'simple_log_proxy_concrete',
        new_callable=mock.PropertyMock,
        create=True,
        return_value=True,
    )
    def test_concrete_model_proxy_concrete(self, mocked):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        self.add_object(TestModelProxy, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(
            sl.content_type,
            ContentType.objects.get_for_model(TestModelProxy, True),
        )

    def test_delete_with_related(self):
        initial_count = SimpleLog.objects.count()
        self.delete_object(ThirdModel.objects.first())
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(
            first_sl.related_logs.all(), [second_sl], transform=None
        )
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

    def test_add_object_with_related(self):
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline',
        }
        self.add_object(
            ThirdModel, params, additional_params=additional_params
        )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(
            second_sl.related_logs.all(), [first_sl], transform=None
        )
        self.assertEqual(first_sl.user, second_sl.user)

    def test_change_object_only_related(self):
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline',
        }
        obj = self.add_object(
            ThirdModel, params, additional_params=additional_params
        )
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
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(
            second_sl.related_logs.all(), [first_sl], transform=None
        )
        self.assertEqual(first_sl.user, second_sl.user)

    def test_disable_related(self):
        # add as context manager
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline',
            'disable_related_context': True,
        }
        obj1 = self.add_object(
            ThirdModel, params, additional_params=additional_params
        )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

        # add as decorator
        initial_count = SimpleLog.objects.count()
        params = {'char_field': 'test'}
        additional_params = {
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 0,
            'related_entries-0-char_field': 'test_inline',
            'disable_related_decorator': True,
        }
        obj2 = self.add_object(
            ThirdModel, params, additional_params=additional_params
        )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

        # change as context manager
        initial_count = SimpleLog.objects.count()
        related = obj1.related_entries.latest('pk')
        additional_params = {
            'char_field': 'changed_title',
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 1,
            'related_entries-0-id': related.pk,
            'related_entries-0-char_field': 'changed_title',
            'disable_related_context': True,
        }
        self.change_object(obj1, params, additional_params=additional_params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

        # change as decorator
        related = obj2.related_entries.latest('pk')
        initial_count = SimpleLog.objects.count()
        additional_params = {
            'char_field': 'changed_title2',
            'related_entries-TOTAL_FORMS': 1,
            'related_entries-INITIAL_FORMS': 1,
            'related_entries-0-id': related.pk,
            'related_entries-0-char_field': 'changed_title2',
            'disable_related_decorator': True,
        }
        self.change_object(obj2, params, additional_params=additional_params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

        # delete as context manager
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj1, {'disable_related_context': True})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

        # delete as decorator
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj2, {'disable_related_decorator': True})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerySetEqual(first_sl.related_logs.all(), [])
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

    def test_create_object_with_parent(self):
        third_instance = ThirdModel.objects.create(char_field='test')
        params = {
            'char_field': 'test',
            'third_model': third_instance,
        }
        initial_count = SimpleLog.objects.count()
        obj = self.add_object(RelatedModel, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertEqual(first_sl.get_edited_object(), third_instance)
        self.assertEqual(first_sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(second_sl.get_edited_object(), obj)
        self.assertEqual(second_sl.action_flag, SimpleLog.ADD)
        self.assertQuerySetEqual(
            first_sl.related_logs.all(), [second_sl], transform=None
        )
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

    def test_change_object_with_parent(self):
        third_instance = ThirdModel.objects.create(char_field='test')
        params = {
            'char_field': 'test',
            'third_model': third_instance,
        }
        obj = self.add_object(RelatedModel, params)
        initial_count = SimpleLog.objects.count()
        params.update(char_field='test2')
        self.change_object(obj, params)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertEqual(first_sl.get_edited_object(), third_instance)
        self.assertEqual(first_sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(second_sl.get_edited_object(), obj)
        self.assertEqual(second_sl.action_flag, SimpleLog.CHANGE)
        self.assertQuerySetEqual(
            first_sl.related_logs.all(), [second_sl], transform=None
        )
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

    def test_delete_object_with_parent(self):
        third_instance = ThirdModel.objects.create(char_field='test')
        params = {
            'char_field': 'test',
            'third_model': third_instance,
        }
        obj = self.add_object(RelatedModel, params)
        obj_pk = obj.pk
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertEqual(first_sl.get_edited_object(), third_instance)
        self.assertEqual(first_sl.action_flag, SimpleLog.CHANGE)
        self.assertEqual(second_sl.object_id, str(obj_pk))
        self.assertEqual(
            second_sl.content_type,
            ContentType.objects.get_for_model(RelatedModel),
        )
        self.assertEqual(second_sl.action_flag, SimpleLog.DELETE)
        self.assertQuerySetEqual(
            first_sl.related_logs.all(), [second_sl], transform=None
        )
        self.assertQuerySetEqual(second_sl.related_logs.all(), [])

    @mock.patch.object(
        TestModel,
        'simple_log_repr',
        new_callable=mock.PropertyMock,
        create=True,
        return_value='Test repr',
    )
    def test_simple_log_repr_property(self, mocked):
        self.add_object(TestModel, {'char_field': 'test'})
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.object_repr, 'Test repr')
