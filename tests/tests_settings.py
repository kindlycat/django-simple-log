from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from django.test.utils import isolate_lru_cache
from django.utils import timezone
from django.utils.encoding import force_str

from simple_log.conf import settings
from simple_log.models import SimpleLog, SimpleLogAbstract
from simple_log.utils import (
    get_fields,
    get_log_model,
    get_model_list,
    get_serializer,
)

from .test_app.models import (
    CustomSerializer,
    OtherModel,
    SwappableLogModel,
    TestModel,
    TestModelProxy,
)


class SettingsTestCase(TransactionTestCase):
    @override_settings(SIMPLE_LOG_MODEL_LIST=('test_app.OtherModel',))
    def test_model_list_add(self):
        with isolate_lru_cache(get_model_list):
            self.assertListEqual(get_model_list(), [OtherModel])

    @override_settings(SIMPLE_LOG_EXCLUDE_MODEL_LIST=('test_app.OtherModel',))
    def test_model_exclude_list_add(self):
        model_list = [
            x
            for x in apps.get_models()
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
        SIMPLE_LOG_EXCLUDE_FIELD_LIST=('id', 'char_field', 'choice_field')
    )
    def test_field_list_add(self):
        other_model = OtherModel.objects.create(char_field='other')
        with isolate_lru_cache(get_fields):
            initial_count = SimpleLog.objects.count()
            TestModel.objects.create(char_field='test', fk_field=other_model)
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

    @override_settings(SIMPLE_LOG_MODEL='test_app.SwappableLogModel')
    def test_log_model(self):
        with isolate_lru_cache(get_log_model):
            self.assertIs(get_log_model(), SwappableLogModel)
            other_model = OtherModel.objects.create(char_field='other')
            initial_count = SwappableLogModel.objects.count()
            TestModel.objects.create(char_field='test', fk_field=other_model)
            sl = SwappableLogModel.objects.latest('pk')
            self.assertEqual(
                SwappableLogModel.objects.count(), initial_count + 1
            )
            self.assertDictEqual(
                sl.new,
                {
                    'char_field': {'label': 'Char field', 'value': 'test'},
                    'fk_field': {
                        'label': 'Fk field',
                        'value': {
                            'db': other_model.pk,
                            'repr': force_str(other_model),
                        },
                    },
                    'm2m_field': {'label': 'M2m field', 'value': []},
                    'choice_field': {
                        'label': 'Choice field',
                        'value': {'db': TestModel.ONE, 'repr': 'One'},
                    },
                },
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
            msg = (
                "SIMPLE_LOG_MODEL refers to model 'not_exist.Model' "
                "that has not been installed"
            )
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                get_log_model()

    @override_settings(SIMPLE_LOG_MODEL='test_app.BadLogModel')
    def test_log_model_not_subclass_simplelog(self):
        with isolate_lru_cache(get_log_model):
            msg = 'Log model should be subclass of SimpleLogAbstractBase.'
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
            self.assertIsNone(
                getattr(settings, 'SIMPLE_LOG_SOME_SETTING', None)
            )

    @override_settings(
        SIMPLE_LOG_MODEL_LIST=(), SIMPLE_LOG_EXCLUDE_MODEL_LIST=()
    )
    def test_log_all_models(self):
        all_models = [
            x
            for x in apps.get_models()
            if not issubclass(x, SimpleLogAbstract)
        ]
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
            ContentType.objects.get_for_model(TestModelProxy, True),
        )

    @override_settings(SIMPLE_LOG_SAVE_ONLY_CHANGED=True)
    def test_only_changed(self):
        obj = TestModel.objects.create(char_field='test')
        initial_count = SimpleLog.objects.count()
        obj = TestModel.objects.get(pk=obj.pk)
        obj.char_field = 'changed'
        obj.save()
        self.assertEqual(SimpleLog.objects.count(), initial_count + 1)
        sl = SimpleLog.objects.latest('pk')
        self.assertDictEqual(
            sl.old, {'char_field': {'label': 'Char field', 'value': 'test'}}
        )
        self.assertDictEqual(
            sl.new,
            {'char_field': {'label': 'Char field', 'value': 'changed'}},
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
                'char_field': {'label': 'Char field', 'value': 'test'},
                'date_time_field': {
                    'label': 'Date time field',
                    'value': obj.date_time_field.strftime('%d.%m.%Y [%H:%M]'),
                },
                'date_field': {
                    'label': 'Date field',
                    'value': obj.date_field.strftime('%d|%m|%Y'),
                },
                'time_field': {
                    'label': 'Time field',
                    'value': obj.time_field.strftime('%H/%M'),
                },
                'm2m_field': {'label': 'm2m field', 'value': []},
                'test_entries_fk': {'label': 'test entries', 'value': []},
            },
        )

    @override_settings(SIMPLE_LOG_EXCLUDE_RAW=True)
    def test_exclude_raw(self):
        initial_count = SimpleLog.objects.count()
        fixtures = [
            'tests/fixtures/other_model.json',
            'tests/fixtures/test_model.json',
            'tests/fixtures/third_model.json',
            'tests/fixtures/related_model.json',
        ]
        call_command('loaddata', *fixtures, verbosity=0)
        self.assertEqual(SimpleLog.objects.count(), initial_count)

    @override_settings(SIMPLE_LOG_ENABLED=False)
    def test_enabled(self):
        initial_count = SimpleLog.objects.count()
        TestModel.objects.create(char_field='test')
        OtherModel.objects.create(char_field='test')
        self.assertEqual(SimpleLog.objects.count(), initial_count)
