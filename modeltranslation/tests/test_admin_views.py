"""Tests for admin view."""

from django.test import Client
from django.urls import reverse

from modeltranslation.tests.models import ModelWithConstraint
import pytest


@pytest.mark.xfail  # This is temporary until fix merged
def test_create_duplicate_Uniquetogether(admin_client: Client):
    """unique together constraint error should be handled."""
    ModelWithConstraint.objects.create(
        title1="1", title2="2", title3="3", sub_title1="One", sub_title2="Two"
    )
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title1_en": "1",
            "title1_de": "Andere",
            "title2_en": "Other",
            "title2_de": "Andere",
            "title3_en": "Other",
            "title3_de": "Andere",
            "sub_title1_en": "One",
            "sub_title1_de": "Ein",
            "sub_title2_en": "Other",
            "sub_title2_de": "Andere",
            "email": "you@example.com",
        },
    )
    error_msg = "Model with constraint with this Title1 [en] and Sub title1 [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200
