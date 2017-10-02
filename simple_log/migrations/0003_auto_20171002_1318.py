# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('simple_log', '0002_simplelog_related_logs'),
    ]

    operations = [
        migrations.AddField(
            model_name='simplelog',
            name='change_message',
            field=models.TextField(verbose_name='change message', blank=True),
        )
    ]
