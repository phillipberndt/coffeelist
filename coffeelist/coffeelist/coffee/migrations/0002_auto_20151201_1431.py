# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coffee', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bankaccountingentry',
            name='attachment',
            field=models.FileField(help_text=b'E.g. a scan of a receipt', upload_to=b'', verbose_name=b'Attachment', blank=True),
        ),
    ]
