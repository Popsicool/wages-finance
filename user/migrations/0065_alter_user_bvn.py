# Generated by Django 5.0.6 on 2024-10-25 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0064_alter_user_bvn'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='bvn',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]