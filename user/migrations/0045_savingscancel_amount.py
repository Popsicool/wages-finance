# Generated by Django 5.0.6 on 2024-08-21 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0044_savingscancel'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingscancel',
            name='amount',
            field=models.BigIntegerField(default=0),
            preserve_default=False,
        ),
    ]
