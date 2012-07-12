# -*- coding: utf-8 -*-
"""
Tests have to be run with modeltranslation.tests.settings:
./manage.py test --settings=modeltranslation.tests.settings modeltranslation

TODO: Merge autoregister tests from django-modeltranslation-wrapper.
"""
from django import forms
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils.translation import get_language
from django.utils.translation import trans_real
from django.utils.translation import ugettext_lazy

from modeltranslation import translator
from modeltranslation.admin import (TranslationAdmin,
                                    TranslationStackedInline)
from modeltranslation.tests.settings import DEFAULT_LANGUAGE

# None of the following tests really depend on the content of the request,
# so we'll just pass in None.
request = None

# Override LANGUAGES setting
# FIXME: This works for ModeltranslationTest but not for TranslationAdminTest
settings.LANGUAGES = (('de', 'Deutsch'),
                      ('en', 'English'))


class RelatedModel(models.Model):
    reltitle = models.CharField(ugettext_lazy('Related Title'), max_length=255)


class TestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(verify_exists=False, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class TestTranslationOptions(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)

translator.translator._registry = {}
translator.translator.register(TestModel, TestTranslationOptions)


class TestModelWithFallback(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(verify_exists=False, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class TestTranslationOptionsWithFallback(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = ""

translator.translator.register(TestModelWithFallback,
                               TestTranslationOptionsWithFallback)


class TestModelWithFallback2(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(verify_exists=False, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class TestTranslationOptionsWithFallback2(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not '
                                             'available.')}

translator.translator.register(TestModelWithFallback2,
                               TestTranslationOptionsWithFallback2)


class ModeltranslationTestBase(TestCase):
    urls = 'modeltranslation.tests.urls'

    def setUp(self):
        trans_real.activate('de')

    def tearDown(self):
        trans_real.deactivate()


class ModeltranslationTest(ModeltranslationTestBase):
    """Basic tests for the modeltranslation application."""
    def test_registration(self):
        self.client.post('/set_language/', data={'language': 'de'})
        #self.client.session['django_language'] = 'de-de'
        #self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'de-de'

        langs = tuple(l[0] for l in settings.LANGUAGES)
        self.failUnlessEqual(2, len(langs))
        self.failUnless('de' in langs)
        self.failUnless('en' in langs)
        self.failUnless(translator.translator)

        # Check that eight models are registered for translation
        self.failUnlessEqual(len(translator.translator._registry), 8)

        # Try to unregister a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.unregister, User)

        # Try to get options for a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.get_options_for_model, User)

    def test_translated_models(self):
        # First create an instance of the test model to play with
        inst = TestModel.objects.create(title="Testtitle", text="Testtext")
        field_names = dir(inst)
        self.failUnless('id' in field_names)
        self.failUnless('title' in field_names)
        self.failUnless('title_de' in field_names)
        self.failUnless('title_en' in field_names)
        self.failUnless('text' in field_names)
        self.failUnless('text_de' in field_names)
        self.failUnless('text_en' in field_names)
        self.failUnless('url' in field_names)
        self.failUnless('url_de' in field_names)
        self.failUnless('url_en' in field_names)
        self.failUnless('email' in field_names)
        self.failUnless('email_de' in field_names)
        self.failUnless('email_en' in field_names)
        inst.delete()

    def test_verbose_name(self):
        inst = TestModel.objects.create(title="Testtitle", text="Testtext")
        self.assertEquals(unicode(
            inst._meta.get_field('title_de').verbose_name), u'title [de]')
        inst.delete()

    def test_set_translation(self):
        self.failUnlessEqual(get_language(), 'de')
        # First create an instance of the test model to play with
        title1_de = "title de"
        title1_en = "title en"
        title2_de = "title2 de"
        inst1 = TestModel(title_en=title1_en, text="Testtext")
        inst1.title = title1_de
        inst2 = TestModel(title=title2_de, text="Testtext")
        inst1.save()
        inst2.save()

        self.failUnlessEqual(inst1.title, title1_de)
        self.failUnlessEqual(inst1.title_en, title1_en)

        self.failUnlessEqual(inst2.title, title2_de)
        self.failUnlessEqual(inst2.title_en, None)

        del inst1
        del inst2

        # Check that the translation fields are correctly saved and provide the
        # correct value when retrieving them again.
        n = TestModel.objects.get(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

    def test_titleonly(self):
        title1_de = "title de"
        n = TestModel.objects.create(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        # Because the original field "title" was specified in the constructor
        # it is directly passed into the instance's __dict__ and the descriptor
        # which updates the associated default translation field is not called
        # and the default translation will be None.
        self.failUnlessEqual(n.title_de, None)
        self.failUnlessEqual(n.title_en, None)

        # Now assign the title, that triggers the descriptor and the default
        # translation field is updated
        n.title = title1_de
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, None)

    def test_fallback_values_1(self):
        """
        If ``fallback_values`` is set to string, all untranslated fields would
        return this string.
        """
        title1_de = "title de"
        n = TestModelWithFallback()
        n.title = title1_de
        n.save()
        del n
        n = TestModelWithFallback.objects.get(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        trans_real.activate("en")
        self.failUnlessEqual(n.title, "")

    def test_fallback_values_2(self):
        """
        If ``fallback_values`` is set to ``dict``, all untranslated fields in
        ``dict`` would return this mapped value. Fields not in ``dict`` would
        return default translation.
        """
        title1_de = "title de"
        text1_de = "text in german"
        n = TestModelWithFallback2()
        n.title = title1_de
        n.text = text1_de
        n.save()
        del n
        n = TestModelWithFallback2.objects.get(title=title1_de)
        trans_real.activate("en")
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(
            n.text,
            TestTranslationOptionsWithFallback2.fallback_values['text'])


class ModeltranslationTestRule1(ModeltranslationTestBase):
    """
    Rule 1: Reading the value from the original field returns the value in
    translated to the current language.
    """
    def _test_field(self, field_name, value_de, value_en, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value_de, field_name_en: value_en}

        n = TestModel.objects.create(**params)
        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value_de)
        self.failUnlessEqual(getattr(n, field_name_de), value_de)
        self.failUnlessEqual(getattr(n, field_name_en), value_en)
        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        # Should now be return the english one (just by switching the language)
        self.failUnlessEqual(getattr(n, field_name), value_en)

        n = TestModel.objects.create(**params)
        n.save()
        # Language is set to "en" at this point
        self.failUnlessEqual(getattr(n, field_name), value_en)
        self.failUnlessEqual(getattr(n, field_name_de), value_de)
        self.failUnlessEqual(getattr(n, field_name_en), value_en)
        trans_real.activate('de')
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value_de)

        if deactivate:
            trans_real.deactivate()

    def test_rule1(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        title1_de = "title de"
        title1_en = "title en"
        text_de = "Dies ist ein deutscher Satz"
        text_en = "This is an english sentence"

        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en,
                                     text_de=text_de, text_en=text_en)
        n.save()

        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)
        self.failUnlessEqual(n.text, text_de)
        self.failUnlessEqual(n.text_de, text_de)
        self.failUnlessEqual(n.text_en, text_en)
        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        # Title should now be return the english one (just by switching the
        # language)
        self.failUnlessEqual(n.title, title1_en)
        self.failUnlessEqual(n.text, text_en)

        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en,
                                     text_de=text_de, text_en=text_en)
        n.save()
        # Language is set to "en" at this point
        self.failUnlessEqual(n.title, title1_en)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)
        self.failUnlessEqual(n.text, text_en)
        self.failUnlessEqual(n.text_de, text_de)
        self.failUnlessEqual(n.text_en, text_en)
        trans_real.activate('de')
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.text, text_de)

        trans_real.deactivate()

    def test_rule1_url_field(self):
        self._test_field(field_name='url',
                         value_de='http://www.google.de',
                         value_en='http://www.google.com')

    def test_rule1_email_field(self):
        self._test_field(field_name='email',
                         value_de='django-modeltranslation@googlecode.de',
                         value_en='django-modeltranslation@googlecode.com')


class ModeltranslationTestRule2(ModeltranslationTestBase):
    """
    Rule 2: Assigning a value to the original field also updates the value
    in the associated translation field of the default language
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        self.failUnlessEqual(get_language(), 'de')
        n = TestModel.objects.create(**params)
        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value2)
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_de))

        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value1_de)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value3)
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_en))
        self.failUnlessEqual(value1_de, getattr(n, field_name_de))

        if deactivate:
            trans_real.deactivate()

    def test_rule2(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        self.failUnlessEqual(get_language(), 'de')
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        title2 = "Neuer Titel"
        n.title = title2
        n.save()
        self.failUnlessEqual(n.title, title2)
        self.failUnlessEqual(n.title, n.title_de)

        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        title3 = "new title"

        n.title = title3
        n.title_de = title1_de
        n.save()
        self.failUnlessEqual(n.title, title3)
        self.failUnlessEqual(n.title, n.title_en)
        self.failUnlessEqual(title1_de, n.title_de)

        trans_real.deactivate()

    def test_rule2_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2='http://www.google.at',
                         value3='http://www.google.co.uk')

    def test_rule2_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2='django-modeltranslation@googlecode.at',
                         value3='django-modeltranslation@googlecode.co.uk')


class ModeltranslationTestRule3(ModeltranslationTestBase):
    """
    Rule 3: Assigning a value to a translation field of the default
    language also updates the original field - note that the value of the
    original field will not be updated until the model instance is saved.
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        n = TestModel.objects.create(**params)

        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_de))

        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        setattr(n, field_name_en, value3)
        # the n.title field is not updated before the instance is saved
        n.save()
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_en))

        if deactivate:
            trans_real.deactivate()

    def test_rule3(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(DEFAULT_LANGUAGE, 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        n.title_de = "Neuer Titel"
        n.save()
        # We expect that the original field holds the same value as the german
        # one (german is the default language).
        self.failUnlessEqual(n.title, n.title_de)

        # Fetch the updated object and verify all fields
        updated_obj = TestModel.objects.get(id=n.id)
        self.failUnlessEqual(updated_obj.title, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_de, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_en, 'title en')

        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        n.title_en = "New title"
        # the n.title field is not updated before the instance is saved
        n.save()
        # We expect that the original field has *not* been changed as german
        # is the default language and we only changed the value of the english
        # field.
        # FIXME: Demonstrates a wrong behaviour of save when the current
        # language is different than the default language. In this case the
        # original field is set to value of the current language's field.
        # See issue 33 for details.
        self.failUnlessEqual(n.title, n.title_de)

        # Fetch the updated object and verify all fields
        updated_obj = TestModel.objects.get(id=n.id)
        self.failUnlessEqual(updated_obj.title, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_de, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_en, 'New title')

        trans_real.deactivate()

    def test_rule3_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2='http://www.google.at',
                         value3='http://www.google.co.uk')

    def test_rule3_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2='django-modeltranslation@googlecode.at',
                         value3='django-modeltranslation@googlecode.co.uk')


class ModeltranslationTestRule4(ModeltranslationTestBase):
    """
    Rule 4: If both fields - the original and the translation field of the
    default language - are updated at the same time, the translation field
    wins.
    """
    def _test_field(self, field_name, value1_de, value1_en, value2_de,
                    value2_en, value3, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        n = TestModel.objects.create(**params)

        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value2_de)
        setattr(n, field_name_en, value2_en)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value2_de)
        self.failUnlessEqual(getattr(n, field_name_de), value2_de)
        self.failUnlessEqual(getattr(n, field_name_en), value2_en)

        setattr(n, field_name, value3)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value3)
        self.failUnlessEqual(getattr(n, field_name_de), value3)
        self.failUnlessEqual(getattr(n, field_name_en), value2_en)

        if deactivate:
            trans_real.deactivate()

    def test_rule4(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        self.failUnlessEqual(get_language(), 'de')
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        title2_de = "neu de"
        title2_en = "new en"
        title_foo = "foo"
        n.title = title_foo
        n.title_de = title2_de
        n.title_en = title2_en
        n.save()
        self.failUnlessEqual(n.title, title2_de)
        self.failUnlessEqual(n.title_de, title2_de)
        self.failUnlessEqual(n.title_en, title2_en)

        n.title = title_foo
        n.save()
        self.failUnlessEqual(n.title, title_foo)
        self.failUnlessEqual(n.title_de, title_foo)
        self.failUnlessEqual(n.title_en, title2_en)

    def test_rule4_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2_de='http://www.google.at',
                         value2_en='http://www.google.co.uk',
                         value3='http://www.google.net')

    def test_rule4_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2_de='django-modeltranslation@googlecode.at',
                         value2_en='django-modeltranslation@googlecode.co.uk',
                         value3='django-modeltranslation@googlecode.net')


class ModeltranslationTestModelValidation(ModeltranslationTestBase):
    """
    Tests if a translation model field validates correctly.
    """
    def _test_model_validation(self, field_name, invalid_value, valid_value,
                               invalid_value_de):
        """
        Generic model field validation test.
        """
        field_name_de = '%s_de' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name: invalid_value}

        has_error_key = False
        # Create an object with an invalid url
        #n = TestModel.objects.create(title='Title', url='foo')
        n = TestModel.objects.create(**params)

        # First check the original field
        # Expect that the validation object contains an error for url
        try:
            n.full_clean()
        except ValidationError, e:
            if field_name in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)

        # Check the translation field
        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        # Set translation field to a valid url
        #n.url_de = 'http://code.google.com/p/django-modeltranslation/'
        setattr(n, field_name_de, valid_value)
        has_error_key = False
        # Expect that the validation object contains no error for url
        try:
            n.full_clean()
        except ValidationError, e:
            if field_name_de in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

        # Set translation field to an invalid url
        #n.url_de = 'foo'
        setattr(n, field_name_de, invalid_value)
        has_error_key = False
        # Expect that the validation object contains an error for url_de
        try:
            n.full_clean()
        except ValidationError, e:
            #if 'url_de' in e.message_dict:
            if field_name_de in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)

    def test_model_validation(self):
        """
        General test for CharField and TextField.
        """
        has_error_key = False
        # Create an object without title (which is required)
        n = TestModel.objects.create(text='Testtext')

        # First check the original field
        # Expect that the validation object contains an error for title
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title' in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)
        n.save()

        # Check the translation field
        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        # Set translation field to a valid title
        n.title_de = 'Title'
        has_error_key = False
        # Expect that the validation object contains no error for title
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title_de' in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

        # Set translation field to an empty title
        n.title_de = None
        has_error_key = False
        # Even though the original field isn't optional, translation fields are
        # per definition always optional. So we expect that the validation
        # object contains no error for title_de.
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title_de' in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

    def test_model_validation_url_field(self):
        #has_error_key = False
        ## Create an object with an invalid url
        #n = TestModel.objects.create(title='Title', url='foo')

        ## First check the original field
        ## Expect that the validation object contains an error for url
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url' in e.message_dict:
                #has_error_key = True
        #self.assertTrue(has_error_key)

        ## Check the translation field
        ## Language is set to 'de' at this point
        #self.failUnlessEqual(get_language(), 'de')
        ## Set translation field to a valid url
        #n.url_de = 'http://code.google.com/p/django-modeltranslation/'
        #has_error_key = False
        ## Expect that the validation object contains no error for url
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url_de' in e.message_dict:
                #has_error_key = True
        #self.assertFalse(has_error_key)

        ## Set translation field to an invalid url
        #n.url_de = 'foo'
        #has_error_key = False
        ## Expect that the validation object contains an error for url_de
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url_de' in e.message_dict:
                #has_error_key = True
        #self.assertTrue(has_error_key)

        self._test_model_validation(
            field_name='url',
            invalid_value='foo en',
            valid_value='http://code.google.com/p/django-modeltranslation/',
            invalid_value_de='foo de')

    def test_model_validation_email_field(self):
        self._test_model_validation(
            field_name='email', invalid_value='foo en',
            valid_value='django-modeltranslation@googlecode.com',
            invalid_value_de='foo de')


class TestModelMultitableA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)


class TestModelMultitableB(TestModelMultitableA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


class TestModelMultitableC(TestModelMultitableB):
    titlec = models.CharField(ugettext_lazy('title c'), max_length=255)


class TestModelMultitableD(TestModelMultitableB):
    titled = models.CharField(ugettext_lazy('title d'), max_length=255)


class TestModelAbstractA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)
    class Meta:
        abstract = True


class TestModelAbstractB(TestModelAbstractA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


class TranslationOptionsTestModelMultitableA(translator.TranslationOptions):
    fields = ('titlea',)


class TranslationOptionsTestModelMultitableB(translator.TranslationOptions):
    fields = ('titleb',)


class TranslationOptionsTestModelMultitableC(translator.TranslationOptions):
    fields = ('titlec',)


class TranslationOptionsTestModelAbstractA(translator.TranslationOptions):
    fields = ('titlea',)


class TranslationOptionsTestModelAbstractB(translator.TranslationOptions):
    fields = ('titleb',)


translator.translator.register(TestModelMultitableA,
                               TranslationOptionsTestModelMultitableA)
translator.translator.register(TestModelMultitableB,
                               TranslationOptionsTestModelMultitableB)
translator.translator.register(TestModelMultitableC,
                               TranslationOptionsTestModelMultitableC)
translator.translator.register(TestModelAbstractA,
                               TranslationOptionsTestModelAbstractA)
translator.translator.register(TestModelAbstractB,
                               TranslationOptionsTestModelAbstractB)


class ModeltranslationInheritanceTest(ModeltranslationTestBase):
    """Tests for inheritance support in modeltranslation."""
    def test_abstract_inheritance(self):
        field_names_b = TestModelAbstractB._meta.get_all_field_names()
        self.failIf('titled' in field_names_b)
        self.failIf('titled_de' in field_names_b)
        self.failIf('titled_en' in field_names_b)

    def test_multitable_inheritance(self):
        field_names_a = TestModelMultitableA._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_a)
        self.failUnless('titlea_de' in field_names_a)
        self.failUnless('titlea_en' in field_names_a)

        field_names_b = TestModelMultitableB._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_b)
        self.failUnless('titlea_de' in field_names_b)
        self.failUnless('titlea_en' in field_names_b)
        self.failUnless('titleb' in field_names_b)
        self.failUnless('titleb_de' in field_names_b)
        self.failUnless('titleb_en' in field_names_b)

        field_names_c = TestModelMultitableC._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_c)
        self.failUnless('titlea_de' in field_names_c)
        self.failUnless('titlea_en' in field_names_c)
        self.failUnless('titleb' in field_names_c)
        self.failUnless('titleb_de' in field_names_c)
        self.failUnless('titleb_en' in field_names_c)
        self.failUnless('titlec' in field_names_c)
        self.failUnless('titlec_de' in field_names_c)
        self.failUnless('titlec_en' in field_names_c)

        field_names_d = TestModelMultitableD._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_d)
        self.failUnless('titlea_de' in field_names_d)
        self.failUnless('titlea_en' in field_names_d)
        self.failUnless('titleb' in field_names_d)
        self.failUnless('titleb_de' in field_names_d)
        self.failUnless('titleb_en' in field_names_d)
        self.failUnless('titled' in field_names_d)


class TranslationAdminTest(ModeltranslationTestBase):
    def setUp(self):
        trans_real.activate('de')
        self.test_obj = TestModel.objects.create(
            title='Testtitle', text='Testtext')
        self.site = AdminSite()

    def tearDown(self):
        trans_real.deactivate()
        self.test_obj.delete()

    def test_default_fields(self):
        class TestModelAdmin(TranslationAdmin):
            pass

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['title_de', 'title_en', 'text_de', 'text_en',
             'url_de', 'url_en', 'email_de', 'email_en'])

    def test_default_fieldsets(self):
        class TestModelAdmin(TranslationAdmin):
            pass

        ma = TestModelAdmin(TestModel, self.site)
        # We expect that the original field is excluded and only the
        # translation fields are included in fields
        fields = ['title_de', 'title_en', 'text_de', 'text_en',
                  'url_de', 'url_en', 'email_de', 'email_en']
        self.assertEqual(ma.get_fieldsets(request),
            [(None, {'fields': fields})])
        self.assertEqual(ma.get_fieldsets(request, self.test_obj),
            [(None, {'fields': fields})])

    def test_field_arguments(self):
        class TestModelAdmin(TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

    def test_field_arguments_restricted_on_form(self):
        # Using `fields`.
        class TestModelAdmin(TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # Using `fieldsets`.
        class TestModelAdmin(TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # Using `exclude`.
        class TestModelAdmin(TranslationAdmin):
            exclude = ['url', 'email']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)

        # You can also pass a tuple to `exclude`.
        class TestModelAdmin(TranslationAdmin):
            exclude = ('url', 'email')

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # Using `fields` and `exclude`.
        class TestModelAdmin(TranslationAdmin):
            fields = ['title', 'url']
            exclude = ['url']

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['title_de', 'title_en'])

    def test_field_arguments_restricted_on_custom_form(self):
        # Using `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                fields = ['url', 'email']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['url_de', 'url_en', 'email_de', 'email_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # Using `exclude`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                exclude = ['url', 'email']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # If both, the custom form an the ModelAdmin define an `exclude`
        # option, the ModelAdmin wins. This is Django behaviour.
        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm
            exclude = ['url']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en', 'email_de',
                  'email_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

        # Same for `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                fields = ['text', 'title']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm
            fields = ['email']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['email_de', 'email_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            fields)
        self.assertEqual(ma.get_form(request,
            self.test_obj).base_fields.keys(), fields)

    def test_inline_fieldsets(self):
        class DataModel(models.Model):
            data = models.TextField(blank=True, null=True)

        class DataInline(TranslationStackedInline):
            model = DataModel
            fieldsets = [
                ('Test', {'fields': ('data',)})
            ]

        class TestModelAdmin(TranslationAdmin):
            exclude = ('title', 'text',)
            inlines = [DataInline]

        class DataTranslationOptions(translator.TranslationOptions):
            fields = ('data',)

        translator.translator.register(DataModel,
                                       DataTranslationOptions)
        ma = TestModelAdmin(TestModel, self.site)

        fieldsets = [('Test', {'fields': ['data_de', 'data_en']})]
        self.assertEqual(
            ma.get_inline_instances(request)[0].get_fieldsets(request),
            fieldsets)
        self.assertEqual(
            ma.get_inline_instances(request)[0].get_fieldsets(
                request, self.test_obj),
            fieldsets)
