# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-16 15:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_auto_20160615_1510'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='new_question_notifications',
            field=models.BooleanField(default=False),
        ),
    ]
