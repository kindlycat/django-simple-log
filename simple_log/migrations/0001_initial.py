import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

from simple_log.fields import SimpleJSONField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='SimpleLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_time', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='action time')),
                ('user_repr', models.CharField(blank=True, max_length=1000, verbose_name='user repr')),
                ('user_ip', models.GenericIPAddressField(null=True, verbose_name='IP address')),
                ('object_id', models.TextField(blank=True, null=True, verbose_name='object id')),
                ('object_repr', models.CharField(max_length=1000, verbose_name='object repr')),
                ('action_flag', models.PositiveSmallIntegerField(choices=[(1, 'added'), (2, 'changed'), (3, 'deleted')], verbose_name='action flag')),
                ('old', SimpleJSONField(null=True, verbose_name='old values')),
                ('new', SimpleJSONField(null=True, verbose_name='new values')),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.ContentType', verbose_name='content type')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'log entry',
                'verbose_name_plural': 'logs entries',
                'ordering': ('-action_time',),
                'abstract': False,
                'swappable': 'SIMPLE_LOG_MODEL',
            },
        ),
    ]
