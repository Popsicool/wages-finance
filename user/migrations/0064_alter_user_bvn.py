# Generated by Django 5.0.6 on 2024-10-25 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0063_alter_usersavings_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='bvn',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]