# Generated by Django 2.1.2 on 2018-12-25 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openshift_api', '0002_auto_20181225_0614'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offline',
            name='name',
            field=models.CharField(max_length=20, unique=True, verbose_name='Name'),
        ),
    ]
