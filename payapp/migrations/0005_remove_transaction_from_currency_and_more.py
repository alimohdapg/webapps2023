# Generated by Django 4.1.7 on 2023-03-08 13:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payapp', '0004_rename_currency_transaction_from_currency_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='from_currency',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='to_currency',
        ),
    ]