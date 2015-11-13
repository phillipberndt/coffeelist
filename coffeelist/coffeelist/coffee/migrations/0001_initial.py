# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BankAccountingEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name=b'Date')),
                ('text', models.CharField(help_text=b'A detailed description of the transaction', max_length=255, verbose_name=b'Description')),
                ('amount', models.DecimalField(help_text=b'The amount of money deposited into the bank. Use negative values for spendings.', verbose_name=b'Amount', max_digits=5, decimal_places=2)),
                ('attachment', models.FileField(help_text=b'E.g. a scan of a receipt', upload_to=b'', verbose_name=b'Attachment')),
            ],
        ),
        migrations.CreateModel(
            name='CoffeeDrinker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Name of him (or her) who drinks le coffee', max_length=100)),
                ('email', models.EmailField(help_text=b'A means to reach the coffee enthusiast', max_length=254)),
                ('deposit', models.DecimalField(help_text=b'Assets (Splendid!) or debit (Argh!)', max_digits=5, decimal_places=2)),
                ('active', models.BooleanField(default=True, help_text=b'Whether to include this user on coffee lists')),
            ],
        ),
        migrations.CreateModel(
            name='CoffeeDrinkerAccountingEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name=b'Date')),
                ('text', models.CharField(help_text=b'A detailed description of the transaction', max_length=255, verbose_name=b'Description')),
                ('amount', models.DecimalField(help_text=b"The amount of money deposited into the drinker's account. Use negative values for spendings.", verbose_name=b'Amount', max_digits=5, decimal_places=2)),
                ('coffee_drinker', models.ForeignKey(related_name='custom_accounting', to='coffee.CoffeeDrinker')),
            ],
        ),
        migrations.CreateModel(
            name='CoffeeList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pub_date', models.DateField(auto_now_add=True, verbose_name=b'Publication date')),
                ('processed', models.BooleanField(default=False, help_text=b'Whether all pages were scanned', verbose_name=b'Processed?')),
                ('approved', models.BooleanField(default=False, help_text=b'Whether this was checked by the team and found ok', verbose_name=b'Approved?')),
            ],
        ),
        migrations.CreateModel(
            name='CoffeeListEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('position', models.IntegerField(verbose_name=b'Position')),
                ('position_in_scan', models.IntegerField(default=0, verbose_name=b'Position in scan')),
                ('cross_count', models.IntegerField(default=0, verbose_name=b'Number of crosses on this page')),
                ('coffee_drinker', models.ForeignKey(related_name='listings', to='coffee.CoffeeDrinker')),
            ],
        ),
        migrations.CreateModel(
            name='CoffeeListPage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('page_number', models.SmallIntegerField(verbose_name=b'Page number')),
                ('scan', models.FileField(upload_to=b'', verbose_name=b'Scanned coffee list')),
                ('coffee_list', models.ForeignKey(related_name='pages', to='coffee.CoffeeList')),
            ],
        ),
        migrations.AddField(
            model_name='coffeelistentry',
            name='coffee_list_page',
            field=models.ForeignKey(related_name='entries', to='coffee.CoffeeListPage'),
        ),
        migrations.AddField(
            model_name='coffeedrinkeraccountingentry',
            name='related_sheet_entry',
            field=models.OneToOneField(null=True, to='coffee.CoffeeListEntry'),
        ),
        migrations.AddField(
            model_name='bankaccountingentry',
            name='coffee_drinker',
            field=models.ForeignKey(related_name='bank_accounting', to='coffee.CoffeeDrinker', null=True),
        ),
    ]
