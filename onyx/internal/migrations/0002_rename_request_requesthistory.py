# Generated by Django 5.0.4 on 2024-05-02 12:51

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("internal", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Request",
            new_name="RequestHistory",
        ),
    ]