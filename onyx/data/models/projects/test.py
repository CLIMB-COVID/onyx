from django.db import models
from ..models import BaseRecord, ProjectRecord, Anonymiser
from utils.fields import YearMonthField, UpperCharField, ChoiceField
from utils.constraints import (
    unique_together,
    optional_value_group,
    ordering,
    non_futures,
    conditional_required,
    conditional_value_required,
)


__version__ = "0.1.0"


class TestSampleID(Anonymiser):
    @classmethod
    def get_identifier_prefix(cls):
        return "S"

    class Meta:
        default_permissions = []
        indexes = [
            models.Index(fields=["hash"]),
        ]


class TestRunName(Anonymiser):
    @classmethod
    def get_identifier_prefix(cls):
        return "R"

    class Meta:
        default_permissions = []
        indexes = [
            models.Index(fields=["hash"]),
        ]


class BaseTestModel(ProjectRecord):
    @classmethod
    def version(cls):
        return __version__

    sample_id = UpperCharField()
    run_name = UpperCharField()
    collection_month = YearMonthField(null=True)
    received_month = YearMonthField(null=True)
    char_max_length_20 = models.CharField(max_length=20)
    text_option_1 = models.TextField(blank=True)
    text_option_2 = models.TextField(blank=True)
    submission_date = models.DateField(null=True)
    country = ChoiceField(max_length=20, blank=True)
    region = ChoiceField(max_length=20, blank=True)
    concern = models.BooleanField(null=True)
    tests = models.IntegerField(null=True)
    score = models.FloatField(null=True)
    start = models.IntegerField()
    end = models.IntegerField()
    required_when_published = models.TextField(blank=True)

    class Meta:
        default_permissions = []
        indexes = [
            models.Index(fields=["created"]),
            models.Index(fields=["climb_id"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["published_date"]),
            models.Index(fields=["is_suppressed"]),
            models.Index(fields=["is_site_restricted"]),
            models.Index(fields=["sample_id", "run_name"]),
            models.Index(fields=["sample_id"]),
            models.Index(fields=["run_name"]),
            models.Index(fields=["collection_month"]),
            models.Index(fields=["received_month"]),
        ]
        constraints = [
            unique_together(
                fields=["sample_id", "run_name"],
            ),
            optional_value_group(
                fields=["collection_month", "received_month"],
            ),
            optional_value_group(
                fields=["text_option_1", "text_option_2"],
            ),
            ordering(
                fields=("collection_month", "received_month"),
            ),
            ordering(
                fields=("start", "end"),
            ),
            non_futures(
                fields=["collection_month", "received_month", "submission_date"],
            ),
            conditional_required(
                field="region",
                required=["country"],
            ),
            conditional_value_required(
                field="is_published",
                value=True,
                required=["published_date"],
            ),
            conditional_value_required(
                field="is_published",
                value=True,
                required=["required_when_published"],
            ),
        ]


class TestModel(BaseTestModel):
    class Meta:
        default_permissions = []


class TestModelRecord(BaseRecord):
    link = models.ForeignKey(
        TestModel, on_delete=models.CASCADE, related_name="records"
    )
    test_id = models.IntegerField()
    test_pass = models.BooleanField()
    test_start = YearMonthField()
    test_end = YearMonthField()
    score_a = models.FloatField(null=True)
    score_b = models.FloatField(null=True)
    score_c = models.FloatField(null=True)
    test_result = models.TextField(blank=True)

    class Meta:
        default_permissions = []
        indexes = [
            models.Index(fields=["created"]),
            models.Index(fields=["link", "test_id"]),
        ]
        constraints = [
            unique_together(
                fields=["link", "test_id"],
            ),
            optional_value_group(
                fields=["score_a", "score_b"],
            ),
            ordering(
                fields=("test_start", "test_end"),
            ),
            conditional_required(
                field="score_c",
                required=["score_a", "score_b"],
            ),
            conditional_value_required(
                field="test_pass",
                value=True,
                required=["test_result"],
            ),
        ]
