# Generated by Django 5.0.6 on 2024-07-31 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0030_user_account_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawal',
            name='bank_code',
            field=models.CharField(default='000003'),
            preserve_default=False,
        ),
    ]
