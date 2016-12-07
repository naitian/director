# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-07 00:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0010_auto_20161207_0014'),
        ('vms', '0006_auto_20161203_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='site',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='virtual_machine', to='sites.Site'),
        ),
    ]
