# Generated by Django 5.0.6 on 2024-08-11 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0036_remove_usersavings_balance_savingsactivities_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='repayment_details',
            field=models.JSONField(blank=True, null=True),
        ),
    ]