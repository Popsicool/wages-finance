# Generated by Django 5.0.6 on 2024-08-06 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0032_coporativeactivities_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersavings',
            name='cycle',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='userinvestments',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Active Investment'), ('MATURED', 'Investment Matured, waiting for payout'), ('WITHDRAWN', 'Investment has been withdrawn')], default='ACTIVE', max_length=20),
        ),
    ]
