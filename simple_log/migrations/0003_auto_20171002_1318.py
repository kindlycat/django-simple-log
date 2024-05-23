from django.conf import settings
from django.db import migrations, models


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
