# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coffee', '0002_auto_20151201_1431'),
    ]

    operations = [
        migrations.AddField(
            model_name='coffeedrinker',
            name='note',
            field=models.TextField(verbose_name=b'Note (for admins)', blank=True),
        ),
        migrations.AddField(
            model_name='coffeedrinker',
            name='prefill',
            field=models.IntegerField(default=0, help_text=b'Pre-fill some crosses for this drinker in new lists, for flatrates'),
        ),
    ]
