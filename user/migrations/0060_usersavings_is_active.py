# Generated by Django 5.0.6 on 2024-09-21 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0059_userinvestments_interest'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersavings',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
