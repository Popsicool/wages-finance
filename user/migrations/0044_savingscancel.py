# Generated by Django 5.0.6 on 2024-08-21 09:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0043_rename_penalty_fee_investmentcancel_penalty'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavingsCancel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('penalty', models.PositiveBigIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('savings', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.usersavings')),
            ],
        ),
    ]
