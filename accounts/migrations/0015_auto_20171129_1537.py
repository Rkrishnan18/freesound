# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-11-29 15:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_oldusername'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oldusername',
            name='username',
            field=models.CharField(db_index=True, max_length=255),
        ),
    ]