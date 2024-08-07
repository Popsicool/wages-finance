# Generated by Django 5.0.6 on 2024-07-27 13:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0025_rename_title_usersavings_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavingsActivities',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('activity_type', models.CharField(choices=[('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal')], default='DEPOSIT', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('savings', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='savings_activities', to='user.usersavings')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_saving_activity', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
