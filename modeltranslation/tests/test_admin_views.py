from django.test import Client
from django.urls import reverse
import pytest
from modeltranslation.tests.models import ModelWithConstraint
from django.db import IntegrityError


def test_create_duplicate(admin_client: Client):
    ModelWithConstraint.objects.create(title="1", sub_title="One")
    url = reverse("admin:tests_modelwithconstraint_add")

    with pytest.raises(IntegrityError):
        response = admin_client.post(
            url, {"title": "1", "sub_title_en": "One", "sub_title_de": "Ein"}
        )

        assert response.status_code == 302
