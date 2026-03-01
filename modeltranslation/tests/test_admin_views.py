"""Tests for admin view."""

import pytest
from django.test import Client
from django.urls import reverse

from modeltranslation.tests.models import ModelWithConstraint


@pytest.mark.parametrize(
    "constraint_type,post_data,expected_error",
    [
        (
            "unique_together",
            {
                "title1_en": "1",
                "title1_de": "Andere",
                "title2_en": "Other",
                "title2_de": "Andere",
                "title3_en": "Other",
                "title3_de": "Andere",
                "title4_en": "Other",
                "title4_de": "Andere",
                "sub_title1_en": "One",
                "sub_title1_de": "Ein",
                "sub_title2_en": "Other",
                "sub_title2_de": "Andere",
                "email": "you@example.com",
            },
            "Model with constraint with this Title1 [en] and Sub title1 [en] already exists.",
        ),
        (
            "single_field",
            {
                "title1_en": "Other",
                "title1_de": "Andere",
                "title2_en": "2",
                "title2_de": "Andere",
                "title3_en": "Other",
                "title3_de": "Andere",
                "title4_en": "Other",
                "title4_de": "Andere",
                "sub_title1_en": "Other",
                "sub_title1_de": "Andere",
                "sub_title2_en": "Other",
                "sub_title2_de": "Andere",
                "email": "you@example.com",
            },
            "Model with constraint with this Title2 [en] already exists.",
        ),
        (
            "multi_field",
            {
                "title1_en": "Other",
                "title1_de": "Andere",
                "title2_en": "Other",
                "title2_de": "Andere",
                "title3_en": "3",
                "title3_de": "Andere",
                "title4_en": "Other",
                "title4_de": "Andere",
                "sub_title1_en": "Other",
                "sub_title1_de": "Andere",
                "sub_title2_en": "Two",
                "sub_title2_de": "Andere",
                "email": "you@example.com",
            },
            "Model with constraint with this Title3 [en] and Sub title2 [en] already exists.",
        ),
        (
            "partial_field",
            {
                "title1_en": "Other",
                "title1_de": "Andere",
                "title2_en": "Other",
                "title2_de": "Andere",
                "title3_en": "3",
                "title3_de": "Andere",
                "title4_en": "Other",
                "title4_de": "Andere",
                "sub_title1_en": "Other",
                "sub_title1_de": "Andere",
                "sub_title2_en": "Two",
                "sub_title2_de": "Andere",
                "email": "me@example.com",
            },
            "Model with constraint with this Title3 [en] and Email already exists.",
        ),
    ],
    ids=["unique_together", "single_field", "multi_field", "partial_field"],
)
def test_create_duplicate_constraint_errors(
    admin_client: Client, constraint_type: str, post_data: dict, expected_error: str
):
    """Constraint error handling for different constraint types."""
    ModelWithConstraint.objects.create(**_INITIAL_DATA)
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(url, post_data)
    assert expected_error in response.context["errors"][0]
    assert response.status_code == 200


def test_create_no_duplicate_succeeds(admin_client: Client):
    """Non-conflicting submission should succeed."""
    ModelWithConstraint.objects.create(**_INITIAL_DATA)
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "2",
            "title_de": "3",
            "title1_de": "title1_de",
            "title2_de": "title2_de",
            "title3_de": "title3_de",
            "title4_de": "title4_de",
            "sub_title1_en": "Other",
            "sub_title1_de": "Andere",
            "sub_title2_en": "Other",
            "sub_title2_de": "Andere",
            "email": "me@example.com",
        },
    )
    assert response.status_code == 302


# Common initial data used for all constraint tests
_INITIAL_DATA = {
    "title1": "1",
    "title2": "2",
    "title3": "3",
    "title4": "4",
    "sub_title1": "One",
    "sub_title2": "Two",
    "email": "me@example.com",
}
