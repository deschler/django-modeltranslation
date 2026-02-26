"""Tests for admin view."""

from django.test import Client
from django.urls import reverse

from modeltranslation.tests.models import ModelWithConstraint
import pytest


def test_create_duplicate_Uniquetogether(admin_client: Client):
    """unique together constraint error should be handled."""
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
    error_msg = "Model with constraint with this Title [en] and Sub title1 [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200


def test_create_duplicate_single_field_constraint(admin_client: Client):
    """unique_sfield constraint error should be handled."""
    ModelWithConstraint.objects.create(title="1", sub_title1="One", sub_title2="Two")
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "1",
            "title_de": "2",
            "sub_title1_en": "Other",
            "sub_title1_de": "Andere",
            "sub_title2_en": "Other",
            "sub_title2_de": "Andere",
            "email": "",
        },
    )
    error_msg = "Model with constraint with this Title [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200


def test_create_duplicate_multi_field_constraint(admin_client: Client):
    """unique_mfields constraint error should be handled."""
    ModelWithConstraint.objects.create(title="1", sub_title1="One", sub_title2="Two")
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "1",
            "title_de": "2",
            "sub_title1_en": "Other",
            "sub_title1_de": "Andere",
            "sub_title2_en": "Two",
            "sub_title2_de": "Zwei",
            "email": "",
        },
    )
    error_msg = "Model with constraint with this Title [en] and Sub title2 [en] already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200


def test_create_duplicate_partial_field_constraint(admin_client: Client):
    """unique_partfield (translated + non-translated) constraint error should be handled."""
    ModelWithConstraint.objects.create(
        title="1", sub_title1="One", sub_title2="Two", email="me@example.com"
    )
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "1",
            "title_de": "2",
            "sub_title1_en": "Other",
            "sub_title1_de": "Andere",
            "sub_title2_en": "Other",
            "sub_title2_de": "Andere",
            "email": "me@example.com",
        },
    )
    error_msg = "Model with constraint with this Title [en] and Email already exists."
    assert error_msg in response.context["errors"][0]
    assert response.status_code == 200


def test_create_no_duplicate_succeeds(admin_client: Client):
    """Non-conflicting submission should succeed."""
    ModelWithConstraint.objects.create(title="1", sub_title1="One", sub_title2="Two")
    url = reverse("admin:tests_modelwithconstraint_add")
    response = admin_client.post(
        url,
        {
            "title_en": "2",
            "title_de": "3",
            "sub_title1_en": "Other",
            "sub_title1_de": "Andere",
            "sub_title2_en": "Other",
            "sub_title2_de": "Andere",
            "email": "",
        },
    )
    assert response.status_code == 302
