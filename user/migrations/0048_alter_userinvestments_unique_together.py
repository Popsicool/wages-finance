# Generated by Django 5.0.6 on 2024-08-24 05:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0047_savingsactivities_interest_usersavings_interest'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='userinvestments',
            unique_together=set(),
        ),
    ]
