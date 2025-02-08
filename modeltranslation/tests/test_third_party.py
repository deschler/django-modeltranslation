# pyright: reportGeneralTypeIssues=warning, reportOptionalMemberAccess=warning, reportOptionalOperand=warning

from django import forms
from django.test import TestCase

from modeltranslation.tests import models


class ThirdPartyAppIntegrationTest(TestCase):
    """
    This test case and a test case below have identical tests. The models they test have the same
    definition - but in this case the model is not registered for translation and in the other
    case it is.
    """

    registered = False

    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super().setUpClass()
        cls.model = models.ThirdPartyModel

    def test_form(self):
        class CreationForm(forms.ModelForm):
            class Meta:
                model = self.model
                fields = "__all__"

        creation_form = CreationForm({"name": "abc"})
        inst = creation_form.save()
        assert "abc" == inst.name
        assert 1 == self.model.objects.count()


class ThirdPartyAppIntegrationRegisteredTest(ThirdPartyAppIntegrationTest):
    registered = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = models.ThirdPartyRegisteredModel
