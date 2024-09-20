# Generated by Django 5.0.6 on 2024-09-19 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0057_alter_loan_guarantor1_agreed_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loan',
            name='guarantor1_agreed',
            field=models.CharField(choices=[('PENDING', 'Waiting for guarantor approval'), ('APPROVED', 'Accepted by guarantor'), ('REJECTED', 'Rejected by Guarantor')], default='PENDING', max_length=10),
        ),
        migrations.AlterField(
            model_name='loan',
            name='guarantor2_agreed',
            field=models.CharField(choices=[('PENDING', 'Waiting for guarantor approval'), ('APPROVED', 'Accepted by guarantor'), ('REJECTED', 'Rejected by Guarantor')], default='PENDING', max_length=10),
        ),
    ]
