# Generated by Django 5.0.6 on 2024-08-14 06:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0038_usersavings_payment_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersavings',
            name='target_amount',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
