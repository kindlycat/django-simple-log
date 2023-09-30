from django.contrib.admin.utils import quote
from django.db.transaction import atomic
from django.test import TransactionTestCase
from django.urls import reverse

from simple_log.models import SimpleLog

from .test_app.models import OtherModel, TestModel


class LogModelTestCase(TransactionTestCase):
    def test_log_get_edited_obj(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(sl.get_edited_object(), obj)

    def test_get_admin_url(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.latest('pk')
        expected_url = reverse(
            'admin:test_app_testmodel_change', args=(quote(obj.pk),)
        )
        self.assertEqual(sl.get_admin_url(), expected_url)
        self.assertIn(
            sl.get_admin_url(), '/admin/test_app/testmodel/%d/change/' % obj.pk
        )
        sl.content_type.model = 'nonexistent'
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
            'choice_field': TestModel.TWO,
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
                'choice_field': 'Choice field',
            },
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
        self.assertListEqual(added, [{'db': other_model2.pk, 'repr': 'test2'}])
        self.assertListEqual(removed, [{'db': other_model.pk, 'repr': 'test'}])

    def test_log_get_differences(self):
        TestModel.objects.create(char_field='test')
        obj = TestModel.objects.latest('pk')
        other_model = OtherModel.objects.create(char_field='test')
        params = {
            'char_field': 'test2',
            'fk_field': other_model,
            'choice_field': TestModel.TWO,
        }
        for param, value in params.items():
            setattr(obj, param, value)
        obj.save()
        sl = SimpleLog.objects.latest('pk')
        differences = sl.get_differences()
        self.assertEqual(len(differences), 3)
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Char field'][0],
            {'label': 'Char field', 'old': 'test', 'new': 'test2'},
        )
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Fk field'][0],
            {
                'label': 'Fk field',
                'old': {'db': None, 'repr': ''},
                'new': {'db': other_model.pk, 'repr': str(other_model)},
            },
        )
        self.assertDictEqual(
            [x for x in differences if x['label'] == 'Choice field'][0],
            {
                'label': 'Choice field',
                'old': {'db': TestModel.ONE, 'repr': 'One'},
                'new': {'db': TestModel.TWO, 'repr': 'Two'},
            },
        )

    def test_log_repr(self):
        obj = TestModel.objects.create(char_field='test')
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '{}: {}'.format(sl.object_repr, 'added'))

        obj = TestModel.objects.get(pk=obj.pk)
        obj.char_field = 'test2'
        obj.save()
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '{}: {}'.format(sl.object_repr, 'changed'))

        obj = TestModel.objects.get(pk=obj.pk)
        obj.delete()
        sl = SimpleLog.objects.latest('pk')
        self.assertEqual(str(sl), '{}: {}'.format(sl.object_repr, 'deleted'))
