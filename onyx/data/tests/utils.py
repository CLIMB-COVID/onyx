import os
import logging
import itertools
from django.core.management import call_command
from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User, Site
from ..models import Project
from projects.testproject.models import TestModel, TestModelRecord


class OnyxTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        logging.disable(logging.CRITICAL)

        # Set up test project
        call_command(
            "project",
            os.path.join(settings.BASE_DIR, "projects/testproject/project.json"),
            quiet=True,
        )
        cls.project = Project.objects.get(code="testproject")

        # Set up test sites
        call_command(
            "site",
            "create",
            "testsite_1",
            "--projects",
            cls.project.code,
            "--description",
            "Department of Testing 1",
            quiet=True,
        )
        call_command(
            "site",
            "create",
            "testsite_2",
            "--projects",
            cls.project.code,
            "--description",
            "University of Testing 2",
            quiet=True,
        )
        call_command("site", "roles", "testsite_1", "--grant", "is_active", quiet=True)
        call_command("site", "roles", "testsite_2", "--grant", "is_active", quiet=True)
        cls.site = Site.objects.get(code="testsite_1")
        cls.extra_site = Site.objects.get(code="testsite_2")

        # Set up testproject admin staff
        cls.admin_staff = cls.create_user(
            "test_admin_staff",
            cls.site,
            roles=["is_staff"],
            groups=["testproject.admin"],
        )

        # Set up testproject admin user
        cls.admin_user = cls.create_user(
            "test_admin_user",
            cls.site,
            roles=["is_approved"],
            groups=["testproject.admin"],
        )

        # Set up testproject analyst user
        cls.analyst_user = cls.create_user(
            "test_analyst_user",
            cls.site,
            roles=["is_approved"],
            groups=["testproject.analyst"],
        )

    @classmethod
    def create_user(cls, username, site, roles=None, groups=None):
        """
        Create a user with the given username and roles/groups.
        """

        user = User.objects.create(username=username, site=site)

        if roles:
            for role in roles:
                setattr(user, role, True)

        if groups:
            for group in groups:
                g = Group.objects.get(name=group)
                user.groups.add(g)

        return user

    def assertEqualRecords(self, payload, instance, created: bool = False):
        """
        Assert that the values in a payload match the values in an instance.
        """

        # Assert the instance has the correct site
        self.assertEqual(instance.site, self.site)

        # Assert that the instance has the correct values as the payload
        if not created:
            self.assertEqual(payload.get("climb_id", ""), instance.climb_id)
            self.assertEqual(
                payload.get("published_date"),
                (
                    instance.published_date.strftime("%Y-%m-%d")
                    if instance.published_date
                    else None
                ),
            )

        self.assertEqual(payload.get("sample_id", ""), instance.sample_id)
        self.assertEqual(payload.get("run_name", ""), instance.run_name)
        self.assertEqual(
            payload.get("collection_month"),
            (
                instance.collection_month.strftime("%Y-%m")
                if instance.collection_month
                else None
            ),
        )
        self.assertEqual(
            payload.get("received_month"),
            (
                instance.received_month.strftime("%Y-%m")
                if instance.received_month
                else None
            ),
        )
        self.assertEqual(
            payload.get("char_max_length_20", ""), instance.char_max_length_20
        )
        self.assertEqual(payload.get("text_option_1", ""), instance.text_option_1)
        self.assertEqual(payload.get("text_option_2", ""), instance.text_option_2)
        self.assertEqual(
            payload.get("submission_date"),
            (
                instance.submission_date.strftime("%Y-%m-%d")
                if instance.submission_date
                else None
            ),
        )
        self.assertEqual(payload.get("country", ""), instance.country)
        self.assertEqual(payload.get("region", ""), instance.region)
        self.assertEqual(payload.get("concern"), instance.concern)
        self.assertEqual(payload.get("tests"), instance.tests)
        self.assertEqual(payload.get("score"), instance.score)
        self.assertEqual(payload.get("start"), instance.start)
        self.assertEqual(payload.get("end"), instance.end)

        # If the payload has nested records, check the correctness of these
        if payload.get("records"):
            self.assertEqual(len(payload["records"]), instance.records.count())

            for subrecord in payload["records"]:
                subinstance = instance.records.get(test_id=subrecord.get("test_id"))
                self.assertEqual(subrecord.get("test_id"), subinstance.test_id)
                self.assertEqual(subrecord.get("test_pass"), subinstance.test_pass)
                self.assertEqual(
                    subrecord.get("test_start"),
                    (
                        subinstance.test_start.strftime("%Y-%m")
                        if subinstance.test_start
                        else None
                    ),
                )
                self.assertEqual(
                    subrecord.get("test_end"),
                    (
                        subinstance.test_end.strftime("%Y-%m")
                        if subinstance.test_end
                        else None
                    ),
                )
                self.assertEqual(subrecord.get("score_a"), subinstance.score_a)
                self.assertEqual(subrecord.get("score_b"), subinstance.score_b)
                self.assertEqual(subrecord.get("score_c"), subinstance.score_c)

    def assertEqualClimbIDs(self, records, qs):
        """
        Assert that the CLIMB IDs in the records match the CLIMB IDs in the queryset.
        """

        record_values = sorted(record["climb_id"] for record in records)
        qs_values = sorted(qs.order_by().values_list("climb_id", flat=True).distinct())
        self.assertTrue(record_values)
        self.assertTrue(qs_values)
        self.assertEqual(
            record_values,
            qs_values,
        )


def generate_test_data(n: int):
    """
    Generate test data.
    """

    sample_ids = [f"sample-{i}" for i in range(n)]
    run_names = ["run-1", "run-2", "run-3"]
    collection_months = [f"2022-{i}" for i in range(1, 4)] + [None]
    received_months = [f"2023-{i}" for i in range(1, 13)]
    char_max_length_20 = ["X" * 20, "Y" * 15, "Z" * 10]
    text_option_1 = ["hello", "world", "hey", "world world", "y", ""]
    text_option_2 = ["hello", "bye"]
    submission_dates = [f"2023-{i}-{j}" for i in [1, 8, 12] for j in [1, 10, 15]] + [
        None
    ]
    countries = ["eng", "scot", "wales", "ni", ""]
    regions = {
        "eng": lambda i: ["ne", "nw", "se", "sw"][i % 4],
        "scot": lambda: "other",
        "wales": lambda: "other",
        "ni": lambda: "other",
        "": lambda: "",
    }
    concerns = [True, False, None]
    tests = [1, 2, 3, None]
    scores = [x + 0.12345 for x in range(10)] + [None]
    starts = [1, 2, 3, 4, 5]
    ends = [6, 7, 8, 9, 10]
    required_when_publisheds = ["hello", "world"]
    has_nesteds = [True, False]
    nested_ranges = [
        (1, 10),
        (400, 404),
        (2, 5),
        (7, 12),
        (4, 17),
        (20, 25),
        (3, 11),
        (800, 808),
    ]

    data = []
    for i, (
        sample_id,
        run_name,
        collection_month,
        received_month,
        char_max_length_20,
        text_option_1,
        text_option_2,
        submission_date,
        country,
        concern,
        tests,
        score,
        start,
        end,
        required_when_published,
        has_nested,
        nested_range,
    ) in enumerate(
        zip(
            sample_ids,
            itertools.cycle(run_names),
            itertools.cycle(collection_months),
            itertools.cycle(received_months),
            itertools.cycle(char_max_length_20),
            itertools.cycle(text_option_1),
            itertools.cycle(text_option_2),
            itertools.cycle(submission_dates),
            itertools.cycle(countries),
            itertools.cycle(concerns),
            itertools.cycle(tests),
            itertools.cycle(scores),
            itertools.cycle(starts),
            itertools.cycle(ends),
            itertools.cycle(required_when_publisheds),
            itertools.cycle(has_nesteds),
            itertools.cycle(nested_ranges),
        )
    ):
        x = {
            "sample_id": sample_id,
            "run_name": run_name,
            "collection_month": collection_month,
            "received_month": received_month,
            "char_max_length_20": char_max_length_20,
            "text_option_1": text_option_1,
            "text_option_2": text_option_2,
            "submission_date": submission_date,
            "country": country,
            "region": regions[country]() if country != "eng" else regions[country](i),
            "concern": concern,
            "tests": tests,
            "score": score,
            "start": start,
            "end": end,
            "required_when_published": required_when_published,
        }

        if has_nested:
            test_ids = [x for x in range(*nested_range)]
            test_passes = [True, False]
            test_starts = [f"2022-{i}" for i in range(1, 6)]
            test_ends = [f"2023-{i}" for i in range(1, 6)]
            score_as = [
                x + 0.678910 if not (x % 2 == 0) else None for x in range(1, 10)
            ]
            score_bs = [
                x + 0.678910 if not ((x + 1) % 2 == 0) else None for x in range(1, 10)
            ]
            test_results = [
                "details",
                "more details",
                "other details",
                "random details",
                "extra details",
                "additional details",
                "further details",
                "even more details",
                "",
            ]
            for (
                test_id,
                test_pass,
                test_start,
                test_end,
                score_a,
                score_b,
                test_result,
            ) in zip(
                test_ids,
                itertools.cycle(test_passes),
                itertools.cycle(test_starts),
                itertools.cycle(test_ends),
                itertools.cycle(score_as),
                itertools.cycle(score_bs),
                itertools.cycle(test_results),
            ):
                # Satisfy conditional value required validator
                if not test_result.strip():
                    test_pass = False

                x.setdefault("records", []).append(
                    {
                        "test_id": test_id,
                        "test_pass": test_pass,
                        "test_start": test_start,
                        "test_end": test_end,
                        "score_a": score_a,
                        "score_b": score_b,
                        "test_result": test_result,
                    }
                )

        data.append(x)
    return data


class OnyxDataTestCase(OnyxTestCase):
    NUM_RECORDS = 100

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for data in generate_test_data(n=cls.NUM_RECORDS):
            nested_records = data.pop("records", [])
            data["site"] = cls.site
            data["user"] = cls.admin_user

            if data.get("collection_month"):
                data["collection_month"] += "-01"

            if data.get("received_month"):
                data["received_month"] += "-01"

            record = TestModel.objects.create(**data)
            for nested_record in nested_records:
                nested_record["link"] = record
                nested_record["user"] = cls.admin_user

                if nested_record.get("test_start"):
                    nested_record["test_start"] += "-01"

                if nested_record.get("test_end"):
                    nested_record["test_end"] += "-01"

                TestModelRecord.objects.create(**nested_record)

    def client_handle_paginated(self, method, *args, **kwargs):
        if method.upper() == "GET":
            function = self.client.get
        elif method.upper() == "POST":
            function = self.client.post
        else:
            raise ValueError(f"Unsupported method: {method}")

        response = function(*args, **kwargs)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json().get("data")
        _next = response.json().get("next")

        while _next is not None:
            response = function(_next, *args[1:], **kwargs)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data.extend(response.json().get("data"))
            _next = response.json().get("next")

        return data
