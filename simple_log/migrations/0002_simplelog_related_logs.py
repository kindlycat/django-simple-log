# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.SIMPLE_LOG_MODEL),
        ('simple_log', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='simplelog',
            name='related_logs',
            field=models.ManyToManyField(to=settings.SIMPLE_LOG_MODEL, verbose_name='related log', blank=True),
        ),
    ]
