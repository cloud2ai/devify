# Generated by Django 5.1.4 on 2025-07-25 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jirabot', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailmessage',
            name='summary_title',
            field=models.CharField(blank=True, max_length=500, verbose_name='Summary Title'),
        ),
    ]
