# Generated by Django 5.0.6 on 2024-07-10 06:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0023_investmentplan_investors'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestments',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Active Investment'), ('MATURED', 'Investment Matured, waiting for payout'), ('PAID-OUT', 'INvestment has been paid out')], default='ACTIVE', max_length=20),
        ),
    ]
