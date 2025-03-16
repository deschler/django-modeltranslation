"""Tests for admin view."""

from django.test import Client
from django.urls import reverse

from modeltranslation.tests.models import ModelWithConstraint


def test_create_duplicate(admin_client: Client):
    """Unique constraint error should be handled by TranslationAdmin."""
    ModelWithConstraint.objects.create(title="1", sub_title="One")
    url = reverse("admin:tests_modelwithconstraint_add")

    response = admin_client.post(
        url,
        {
            "title": "1",
            "sub_title_en": "One",
            "sub_title_de": "Ein",
        },
    )

    error_msg = "Model with constraint with this Title and Sub title [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200
