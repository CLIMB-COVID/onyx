from operator import xor
from django.db.models import Q
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from projects.testproject.models import TestModel


# TODO: Tests for query endpoint


class TestQueryView(OnyxDataTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        self.endpoint = reverse(
            "projects.testproject.query", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test basic retrieval of all records.
        """

        data = self.client_handle_paginated("POST", self.endpoint)
        self.assertEqualClimbIDs(
            data,
            TestModel.objects.all(),
        )

    def test_operators(self):
        """
        Test a mixture of operators in a query.
        """

        queries = [
            ({"collection_month": "2022-01"}, Q(collection_month="2022-01-01")),
            ({"records__test_end": "2023-05"}, Q(records__test_end="2023-05-01")),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {"records__test_end": "2023-05"},
                    ]
                },
                Q(collection_month="2022-01-01") & Q(records__test_end="2023-05-01"),
            ),
            (
                {
                    "|": [
                        {"collection_month": "2022-01"},
                        {"records__test_end": "2023-05"},
                    ]
                },
                Q(collection_month="2022-01-01") | Q(records__test_end="2023-05-01"),
            ),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {
                            "|": [
                                {"records__test_end": "2023-05"},
                                {"records__test_end": "2023-06"},
                            ]
                        },
                    ]
                },
                Q(collection_month="2022-01-01")
                & (
                    Q(records__test_end="2023-05-01")
                    | Q(records__test_end="2023-03-01")
                ),
            ),
            (
                {
                    "|": [
                        {"collection_month": "2022-01"},
                        {
                            "&": [
                                {"records__test_end__gt": "2023-02"},
                                {"records__test_end__lt": "2023-05"},
                            ],
                        },
                    ]
                },
                Q(collection_month="2022-01-01")
                | (
                    Q(records__test_end__gt="2023-02-01")
                    & Q(records__test_end__lt="2023-05-01")
                ),
            ),
            (
                {"~": {"collection_month": "2022-01"}},
                ~Q(collection_month="2022-01-01"),
            ),
            (
                {
                    "~": {
                        "&": [
                            {"collection_month": "2022-01"},
                            {"records__test_end": "2023-05"},
                        ]
                    }
                },
                ~(Q(collection_month="2022-01-01") & Q(records__test_end="2023-05-01")),
            ),
            (
                {
                    "~": {
                        "|": [
                            {"collection_month": "2022-01"},
                            {"records__test_end": "2023-05"},
                        ]
                    }
                },
                ~(Q(collection_month="2022-01-01") | Q(records__test_end="2023-05-01")),
            ),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {"~": {"records__test_end": "2023-06"}},
                    ]
                },
                Q(collection_month="2022-01-01") & ~Q(records__test_end="2023-06-01"),
            ),
            (
                {
                    "^": [
                        {"collection_month": "2022-01"},
                        {
                            "|": [
                                {"records__test_end": "2023-01"},
                                {"records__test_end": "2023-03"},
                                {"records__test_end": "2023-05"},
                            ]
                        },
                    ]
                },
                xor(
                    Q(collection_month="2022-01-01"),
                    (
                        Q(records__test_end="2023-01-01")
                        | Q(records__test_end="2023-03-01")
                        | Q(records__test_end="2023-05-01")
                    ),
                ),
            ),
        ]

        for query, expected in queries:
            data = self.client_handle_paginated("POST", self.endpoint, data=query)
            self.assertEqualClimbIDs(data, TestModel.objects.filter(expected))

    def test_empty_value(self):
        """
        Test that empty values are handled correctly for each field type.
        """

        for empty in ["", " ", "   ", None]:
            for field in [
                "text_option_1",  # text
                "country",  # choice
                "tests",  # integer
                "score",  # decimal
                "collection_month",  # date (YYYY-MM)
                "submission_date",  # date (YYYY-MM-DD)
                "concern",  # bool
            ]:
                # Equal to empty
                data = self.client_handle_paginated(
                    "POST", self.endpoint, data={field: empty}
                )
                self.assertEqualClimbIDs(
                    data,
                    TestModel.objects.filter(**{f"{field}__isnull": True}),
                )

                # Not equal to empty
                data = self.client_handle_paginated(
                    "POST", self.endpoint, data={"~": {field: empty}}
                )
                self.assertEqualClimbIDs(
                    data,
                    TestModel.objects.filter(**{f"{field}__isnull": False}),
                )
