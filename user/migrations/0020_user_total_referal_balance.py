# Generated by Django 5.0.6 on 2024-06-24 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0019_forgetpasswordtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='total_referal_balance',
            field=models.BigIntegerField(default=0),
        ),
    ]