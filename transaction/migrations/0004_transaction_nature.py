# Generated by Django 5.0.6 on 2024-07-25 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0003_transaction_revenue'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='nature',
            field=models.CharField(choices=[('Others', 'OTHERS'), ('SAVINGS', 'Savings'), ('LOAN_REPAYMENT', 'Loan Repayment')], default='Others', max_length=250),
        ),
    ]