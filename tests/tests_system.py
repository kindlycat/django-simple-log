# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.transaction import atomic
from django.test import override_settings
from django.utils.encoding import force_text

from simple_log.models import SimpleLog
from simple_log.utils import disable_logging, disable_related

from .test_app.models import OtherModel, RelatedModel, TestModel, ThirdModel
from .tests_admin import AdminTestCase
from .utils import get_ctx


class SystemTestCase(AdminTestCase):
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
        params = params.copy()
        params, m2m = self.prepare_params(model, params)

        dl_dec = 'disable_logging_decorator' in kwargs.get(
            'additional_params', {}
        )
        dr_dec = 'disable_related_decorator' in kwargs.get(
            'additional_params', {}
        )

        def save_obj():
            obj = model.objects.create(**params)
            for k, v in m2m.items():
                getattr(obj, k).add(*v)

        ctx = get_ctx(
            'disable_logging_context' in kwargs.get('additional_params', {}),
            'disable_related_context' in kwargs.get('additional_params', {}),
        )
        with ctx[0](), ctx[1]():
            if dl_dec:
                save_obj = disable_logging()(save_obj)
            if dr_dec:
                save_obj = disable_related()(save_obj)
            save_obj()
        return model.objects.latest('pk')

    @atomic
    def change_object(self, obj, params, **kwargs):
        params = params.copy()
        params, m2m = self.prepare_params(obj._meta.model, params)
        for k, v in params.items():
            setattr(obj, k, v)

        dl_dec = 'disable_logging_decorator' in kwargs.get(
            'additional_params', {}
        )
        dr_dec = 'disable_related_decorator' in kwargs.get(
            'additional_params', {}
        )

        def save_obj():
            obj.save()
            for k, v in m2m.items():
                if not v:
                    getattr(obj, k).clear()
                else:
                    getattr(obj, k).add(*v)

        ctx = get_ctx(
            'disable_logging_context' in kwargs.get('additional_params', {}),
            'disable_related_context' in kwargs.get('additional_params', {}),
        )
        with ctx[0](), ctx[1]():
            if dl_dec:
                save_obj = disable_logging()(save_obj)
            if dr_dec:
                save_obj = disable_related()(save_obj)
            save_obj()

        return obj._meta.model.objects.get(pk=obj.pk)

    @atomic
    def delete_object(self, obj, params=None):
        params = (params or {}).copy()
        dl_dec = 'disable_logging_decorator' in params
        dr_dec = 'disable_related_decorator' in params

        def delete_obj():
            obj.delete()

        ctx = get_ctx(
            'disable_logging_context' in params,
            'disable_related_context' in params,
        )
        with ctx[0](), ctx[1]():
            if dl_dec:
                delete_obj = disable_logging()(delete_obj)
            if dr_dec:
                delete_obj = disable_related()(delete_obj)
            delete_obj()

    @override_settings(SIMPLE_LOG_NONE_USER_REPR='GLaDOS')
    def test_system_change_repr(self):
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
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
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_text(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {'label': 'M2m field', 'value': []},
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
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
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {'label': 'M2m field', 'value': []},
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_text(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
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
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {
                    'label': 'M2m field',
                    'value': [
                        {
                            'db': self.other_model.pk,
                            'repr': force_text(self.other_model),
                        }
                    ],
                },
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
        )
        self.assertDictEqual(
            sl.new,
            {
                'char_field': {'label': 'Char field', 'value': 'test'},
                'fk_field': {
                    'label': 'Fk field',
                    'value': {'db': None, 'repr': ''},
                },
                'm2m_field': {'label': 'M2m field', 'value': []},
                'choice_field': {
                    'label': 'Choice field',
                    'value': {'db': 1, 'repr': 'One'},
                },
            },
        )

    @atomic
    def test_create_log_commit(self):
        initial_count = SimpleLog.objects.count()
        SimpleLog.log(self.other_model, action_flag=1, commit=False)
        self.assertEqual(SimpleLog.objects.count(), initial_count)

        initial_count = SimpleLog.objects.count()
        SimpleLog.log(self.other_model, action_flag=1)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)

    def test_add_object_with_related(self):
        initial_count = SimpleLog.objects.count()
        with atomic():
            obj = self.add_object(ThirdModel, {'char_field': 'test'})
            obj.related_entries.add(
                RelatedModel(char_field='test_related'), bulk=False
            )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(
            second_sl.related_logs.all(), [repr(first_sl)]
        )
        self.assertEqual(first_sl.user, second_sl.user)

    def test_change_object_only_related(self):
        with atomic():
            obj = self.add_object(ThirdModel, {'char_field': 'test'})
            obj.related_entries.add(
                RelatedModel(char_field='test_related'), bulk=False
            )
        related = obj.related_entries.latest('pk')
        initial_count = SimpleLog.objects.count()
        with atomic():
            self.change_object(obj, {})
            self.change_object(related, {'char_field': 'changed_title'})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(
            second_sl.related_logs.all(), [repr(first_sl)]
        )
        self.assertEqual(first_sl.user, second_sl.user)

    def test_disable_related(self):
        # add as context manager
        initial_count = SimpleLog.objects.count()
        with atomic():
            obj1 = self.add_object(
                ThirdModel,
                {'char_field': 'test'},
                additional_params={'disable_related_context': True},
            )
            obj1.related_entries.add(
                RelatedModel(char_field='test_related'), bulk=False
            )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

        # add as decorator
        initial_count = SimpleLog.objects.count()
        with atomic():
            obj2 = self.add_object(
                ThirdModel,
                {'char_field': 'test'},
                additional_params={'disable_related_decorator': True},
            )
            obj2.related_entries.add(
                RelatedModel(char_field='test_related'), bulk=False
            )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

        # change as context manager
        initial_count = SimpleLog.objects.count()
        related = obj1.related_entries.latest('pk')
        with atomic():
            self.change_object(
                obj1,
                {'char_field': 'changed_title'},
                additional_params={'disable_related_context': True},
            )
            self.change_object(
                related,
                {'char_field': 'changed_title'},
                additional_params={'disable_related_context': True},
            )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

        # change as decorator
        initial_count = SimpleLog.objects.count()
        related = obj2.related_entries.latest('pk')
        with atomic():
            self.change_object(
                obj2,
                {'char_field': 'changed_title2'},
                additional_params={'disable_related_decorator': True},
            )
            self.change_object(
                related,
                {'char_field': 'changed_title2'},
                additional_params={'disable_related_decorator': True},
            )
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

        # delete as context manager
        initial_count = SimpleLog.objects.count()
        with atomic():
            self.delete_object(obj1, {'disable_related_context': True})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])

        # delete as decorator
        initial_count = SimpleLog.objects.count()
        with atomic():
            self.delete_object(obj2, {'disable_related_decorator': True})
        self.assertEqual(SimpleLog.objects.count(), initial_count + 2)
        first_sl = SimpleLog.objects.all()[0]
        second_sl = SimpleLog.objects.all()[1]
        self.assertQuerysetEqual(first_sl.related_logs.all(), [])
        self.assertQuerysetEqual(second_sl.related_logs.all(), [])
