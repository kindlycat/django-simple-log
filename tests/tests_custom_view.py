from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.utils.encoding import force_text

from simple_log.models import SimpleLog
from simple_log.settings import log_settings

from .test_app.models import TestModel
from .tests_admin import AdminTestCase


class CustomViewTestCase(AdminTestCase):
    namespace = ''

    def test_anonymous_add(self):
        self.client.logout()
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
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, log_settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_text(new_obj.id))
        self.assertEqual(sl.object_repr, force_text(new_obj))
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
                        'repr': force_text(self.other_model),
                    },
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
                    'value': {'db': TestModel.TWO, 'repr': 'Two'},
                },
            },
        )

    def test_anonymous_change(self):
        self.client.logout()
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
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, log_settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_text(obj.id))
        self.assertEqual(sl.object_repr, force_text(obj))
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
                        'repr': force_text(self.other_model),
                    },
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

    def test_anonymous_delete(self):
        self.client.logout()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
        }
        obj = self.add_object(TestModel, params)
        initial_count = SimpleLog.objects.count()
        self.delete_object(obj)
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.action_flag, SimpleLog.DELETE)
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, log_settings.ANONYMOUS_REPR)
        self.assertEqual(sl.user_ip, self.ip)
        self.assertEqual(sl.object_id, force_text(obj.id))
        self.assertEqual(sl.object_repr, force_text(obj))
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
                        'repr': force_text(self.other_model),
                    },
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
                    'value': {'db': TestModel.TWO, 'repr': 'Two'},
                },
            },
        )

    @override_settings(SIMPLE_LOG_ANONYMOUS_REPR='UNKNOWN')
    def test_anonymous_repr(self):
        self.client.logout()
        params = {
            'char_field': 'test',
            'fk_field': self.other_model,
            'm2m_field': [self.other_model],
            'choice_field': TestModel.TWO,
        }
        self.add_object(TestModel, params)
        sl = SimpleLog.objects.latest('pk')
        self.assertIsNone(sl.user)
        self.assertEqual(sl.user_repr, 'UNKNOWN')
