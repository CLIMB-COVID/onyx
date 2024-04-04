# Generated by Django 5.0.3 on 2024-04-04 14:26

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
        ("testproject", "0006_remove_testmodel_basetestmodel_ptr_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="HistoricalBaseTestModel",
            new_name="HistoricalTestModel",
        ),
        migrations.RenameModel(
            old_name="BaseTestModel",
            new_name="TestModel",
        ),
        migrations.AlterModelOptions(
            name="historicaltestmodel",
            options={
                "get_latest_by": ("history_date", "history_id"),
                "ordering": ("-history_date", "-history_id"),
                "verbose_name": "historical test model",
                "verbose_name_plural": "historical test models",
            },
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_sample__401e0b_ut",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_collect_a6369e_ovg",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_text_op_d4965a_ovg",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_collect_c39c65_ord",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_start_e_d47778_ord",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_collect_d74368_nf",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_region__97e2cd_cr",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_is_publ_975e9c_cvr",
        ),
        migrations.RemoveConstraint(
            model_name="testmodel",
            name="testproject_basetestmodel_is_publ_16d558_cvr",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_created_6899af_idx",
            old_name="testproject_created_4cf37a_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_climb_i_cdc763_idx",
            old_name="testproject_climb_i_3ebdce_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_is_publ_fa963e_idx",
            old_name="testproject_is_publ_bd1b2d_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_publish_163a20_idx",
            old_name="testproject_publish_f18b97_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_is_supp_6a5d87_idx",
            old_name="testproject_is_supp_487401_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_site_id_125b38_idx",
            old_name="testproject_site_id_98b893_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_is_site_0182e6_idx",
            old_name="testproject_is_site_9bbbf1_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_sample__f02fdb_idx",
            old_name="testproject_sample__a4c10d_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_sample__d547e0_idx",
            old_name="testproject_sample__7cacea_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_run_nam_f17891_idx",
            old_name="testproject_run_nam_71a1f9_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_collect_71ff32_idx",
            old_name="testproject_collect_340ba7_idx",
        ),
        migrations.RenameIndex(
            model_name="testmodel",
            new_name="testproject_receive_3676a3_idx",
            old_name="testproject_receive_aa2cac_idx",
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.UniqueConstraint(
                fields=("sample_id", "run_name"),
                name="testproject_testmodel_sample__401e0b_ut",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("collection_month__isnull", False),
                    ("received_month__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testmodel_collect_a6369e_ovg",
                violation_error_message="At least one of collection_month, received_month is required.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("text_option_1__isnull", False),
                    ("text_option_2__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testmodel_text_op_d4965a_ovg",
                violation_error_message="At least one of text_option_1, text_option_2 is required.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("collection_month__isnull", True),
                    ("received_month__isnull", True),
                    ("collection_month__lte", models.F("received_month")),
                    _connector="OR",
                ),
                name="testproject_testmodel_collect_c39c65_ord",
                violation_error_message="The collection_month must be less than or equal to received_month.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("start__isnull", True),
                    ("end__isnull", True),
                    ("start__lte", models.F("end")),
                    _connector="OR",
                ),
                name="testproject_testmodel_start_e_d47778_ord",
                violation_error_message="The start must be less than or equal to end.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("collection_month__isnull", True),
                        ("collection_month__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                    models.Q(
                        ("received_month__isnull", True),
                        ("received_month__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                    models.Q(
                        ("submission_date__isnull", True),
                        ("submission_date__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                ),
                name="testproject_testmodel_collect_d74368_nf",
                violation_error_message="At least one of collection_month, received_month, submission_date is from the future.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("region__isnull", False), _negated=True),
                    ("country__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testmodel_region__97e2cd_cr",
                violation_error_message="Each of country are required in order to set region.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("is_published", True), _negated=True),
                    ("published_date__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testmodel_is_publ_975e9c_cvr",
                violation_error_message="Each of published_date are required in order to set is_published to the value.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testmodel",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("is_published", True), _negated=True),
                    ("required_when_published__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testmodel_is_publ_16d558_cvr",
                violation_error_message="Each of required_when_published are required in order to set is_published to the value.",
            ),
        ),
    ]