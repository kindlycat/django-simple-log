# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import jsonfield.fields
from django.conf import settings
import django.db.models.deletion
import simple_log.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BadLogModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomLogModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='action time', editable=False)),
                ('user_repr', models.CharField(max_length=1000, verbose_name='user repr', blank=True)),
                ('user_ip', models.GenericIPAddressField(null=True, verbose_name='IP address')),
                ('object_id', models.TextField(null=True, verbose_name='object id', blank=True)),
                ('object_repr', models.CharField(max_length=1000, verbose_name='object repr')),
                ('action_flag', models.PositiveSmallIntegerField(verbose_name='action flag', choices=[(1, 'added'), (2, 'changed'), (3, 'deleted')])),
                ('old', jsonfield.fields.JSONField(null=True, verbose_name='old values')),
                ('new', jsonfield.fields.JSONField(null=True, verbose_name='new values')),
                ('change_message', models.TextField(verbose_name='change message', blank=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='content type', blank=True, to='contenttypes.ContentType', null=True)),
                ('related_logs', simple_log.fields.SimpleManyToManyField(related_name='related_logs_rel_+', verbose_name='related log', to='self', blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='user', to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('-action_time',),
                'abstract': False,
                'verbose_name': 'log entry',
                'verbose_name_plural': 'logs entries',
            },
        ),
        migrations.CreateModel(
            name='OtherModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('char_field', models.CharField(max_length=100, verbose_name='Char field')),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'other entry',
                'verbose_name_plural': 'other entries',
            },
        ),
        migrations.CreateModel(
            name='RelatedModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('char_field', models.CharField(max_length=100, verbose_name='Char field')),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'related entry',
                'verbose_name_plural': 'related entries',
            },
        ),
        migrations.CreateModel(
            name='SwappableLogModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='action time', editable=False)),
                ('user_repr', models.CharField(max_length=1000, verbose_name='user repr', blank=True)),
                ('user_ip', models.GenericIPAddressField(null=True, verbose_name='IP address')),
                ('object_id', models.TextField(null=True, verbose_name='object id', blank=True)),
                ('object_repr', models.CharField(max_length=1000, verbose_name='object repr')),
                ('action_flag', models.PositiveSmallIntegerField(verbose_name='action flag', choices=[(1, 'added'), (2, 'changed'), (3, 'deleted')])),
                ('old', jsonfield.fields.JSONField(null=True, verbose_name='old values')),
                ('new', jsonfield.fields.JSONField(null=True, verbose_name='new values')),
                ('change_message', models.TextField(verbose_name='change message', blank=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='content type', blank=True, to='contenttypes.ContentType', null=True)),
                ('related_logs', simple_log.fields.SimpleManyToManyField(related_name='related_logs_rel_+', verbose_name='related log', to='self', blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='user', to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('-action_time',),
                'abstract': False,
                'verbose_name': 'log entry',
                'verbose_name_plural': 'logs entries',
            },
        ),
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('char_field', models.CharField(max_length=100, verbose_name='Char field', blank=True)),
                ('choice_field', models.PositiveSmallIntegerField(default=1, null=True, verbose_name='Choice field', blank=True, choices=[(1, 'One'), (2, 'Two')])),
                ('fk_field', models.ForeignKey(related_name='test_entries_fk', verbose_name='Fk field', blank=True, to='test_app.OtherModel', null=True)),
                ('m2m_field', models.ManyToManyField(related_name='test_entries_m2m', verbose_name='M2m field', to='test_app.OtherModel', blank=True)),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'test entry',
                'verbose_name_plural': 'test entries',
            },
        ),
        migrations.CreateModel(
            name='ThirdModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('char_field', models.CharField(max_length=100, verbose_name='Char field')),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'third entry',
                'verbose_name_plural': 'third entries',
            },
        ),
        migrations.AddField(
            model_name='relatedmodel',
            name='third_model',
            field=models.ForeignKey(related_name='related_entries', to='test_app.ThirdModel'),
        ),
        migrations.AddField(
            model_name='othermodel',
            name='m2m_field',
            field=models.ManyToManyField(to='test_app.TestModel', blank=True),
        ),
        migrations.CreateModel(
            name='TestModelProxy',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('test_app.testmodel',),
        ),
    ]
