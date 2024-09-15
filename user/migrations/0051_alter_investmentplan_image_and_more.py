# Generated by Django 5.0.6 on 2024-09-14 15:25

import user.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0050_alter_forgetpasswordtoken_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investmentplan',
            name='image',
            field=models.ImageField(upload_to=user.models.upload_to_investment_images),
        ),
        migrations.AlterField(
            model_name='user',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to=user.models.upload_to_profile_pic),
        ),
    ]