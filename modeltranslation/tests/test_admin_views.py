"""Tests for admin view."""

from django.test import Client
from django.urls import reverse

from modeltranslation.tests.models import ModelWithConstraint
import pytest


def test_create_duplicate(admin_client: Client):
    """Unique constraint error should be handled by TranslationAdmin."""
    ModelWithConstraint.objects.create(title="1", sub_title1="One", sub_title2="Two")
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "1",
            "title_de": "2",
            "sub_title1_en": "One",
            "sub_title1_de": "Ein",
            "sub_title2_en": "Two",
            "sub_title2_de": "Zwei",
            "email": "",
        },
    )
    error_msg = "Model with constraint with this Title [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200
