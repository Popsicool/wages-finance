# Generated by Django 5.0.6 on 2024-07-30 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0029_alter_usersavings_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='account_name',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]