# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.core.management.base import BaseCommand

from simple_log.utils import get_fields, get_model_list, get_label


class Command(BaseCommand):
    help = 'View all registered models, mark which is tracking'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--with_fields',
            action='store_true',
            default=False,
            help='Show which fields is tracking for every model'
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        for model in apps.get_models():
            tracking = model in get_model_list()
            if not tracking and options['with_fields']:
                continue
            prefix = '[{}] '.format('+' if tracking else '-')
            self.stdout.write(prefix + get_label(model))
            if tracking and options['with_fields']:
                fields = get_fields(model)
                self.stdout.write(
                    '    - ' + '\n    - '.join([x.name for x in fields]),
                )
        self.stdout.write('')
