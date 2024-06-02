# Generated by Django 5.0.6 on 2024-05-29 09:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0009_usersavings_created_at_usersavings_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Withdrawal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('bank_name', models.CharField()),
                ('account_number', models.CharField()),
                ('status', models.CharField(choices=[('PENDING', 'Withdrawal yet to be approved'), ('REJECTED', 'Withdrawal Rejected by admin'), ('PROCESSING', 'Withdrawal has been approved by admin, waiting for payout'), ('SUCCESS', 'Withdrawal Successfully done'), ('FAILED', 'Withdrawal failed on payment gateway')], default='PENDING')),
                ('message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('admin_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_withdrawal_approval', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_withdrawal', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]