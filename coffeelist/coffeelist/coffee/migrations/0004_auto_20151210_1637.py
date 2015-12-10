# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coffee', '0003_auto_20151210_1635'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coffeedrinker',
            name='prefill',
            field=models.IntegerField(default=0, help_text=b'Pre-fill some crosses for this drinker in new lists, for flatrates. If set, only these crosses count, the scan is ignored!'),
        ),
    ]
