# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-05 20:17
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('gid', models.PositiveIntegerField(primary_key=True, serialize=False, validators=[django.core.validators.MinValueValidator(1000)])),
                ('groupname', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('uid', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1000)])),
                ('gid', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1000)])),
                ('username', models.CharField(max_length=32)),
                ('superuser', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='group',
            name='users',
            field=models.ManyToManyField(related_name='groups', to='users.User'),
        ),
    ]