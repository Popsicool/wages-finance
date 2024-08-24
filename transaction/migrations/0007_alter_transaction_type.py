# Generated by Django 5.0.6 on 2024-08-24 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0006_rename_created_date_transaction_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='type',
            field=models.CharField(choices=[('WALLET-CREDIT', 'Wallet Credit'), ('WITHDRAWAL', 'Withdrawal'), ('DATA_PURCHASE', 'Data purchase')], default='WALLET-CREDIT', max_length=250),
        ),
    ]
