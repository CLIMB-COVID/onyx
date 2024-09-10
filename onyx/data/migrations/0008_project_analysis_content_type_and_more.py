# Generated by Django 5.0.8 on 2024-09-02 10:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("data", "0007_analysisid"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="analysis_content_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="analysis_project",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="content_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="project",
                to="contenttypes.contenttype",
            ),
        ),
    ]