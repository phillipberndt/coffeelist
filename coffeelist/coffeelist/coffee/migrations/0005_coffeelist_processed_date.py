# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coffee', '0004_auto_20151210_1637'),
    ]

    operations = [
        migrations.AddField(
            model_name='coffeelist',
            name='processed_date',
            field=models.DateField(null=True, verbose_name=b'Date of processing', blank=True),
        ),
    ]
