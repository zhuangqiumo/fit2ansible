# Generated by Django 2.1.2 on 2019-01-04 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openshift_api', '0002_template_date_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cluster',
            name='template',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.DeleteModel(
            name='Template',
        ),
    ]
