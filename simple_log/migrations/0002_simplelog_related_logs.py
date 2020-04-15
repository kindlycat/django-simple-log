from django.db import migrations
from django.conf import settings

from simple_log.fields import SimpleManyToManyField


class Migration(migrations.Migration):

    dependencies = [
        ('simple_log', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='simplelog',
            name='related_logs',
            field=SimpleManyToManyField(to='self', verbose_name='related log', blank=True),
        ),
    ]
