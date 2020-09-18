from django.test import TransactionTestCase

from simple_log.templatetags.simple_log_tags import get_type

from .test_app.models import TestModel


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
