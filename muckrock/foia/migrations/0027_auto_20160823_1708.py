# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-23 17:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foia', '0026_create_agency_users'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='foiarequest',
            name='email',
        ),
        migrations.RemoveField(
            model_name='foiarequest',
            name='other_emails',
        ),
    ]