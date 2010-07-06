# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase
from django.utils.thread_support import currentThread
from django.utils.translation import get_language
from django.utils.translation import trans_real
from django.utils.translation import ugettext_lazy

from modeltranslation import translator
from modeltranslation.settings import *

# TODO: Tests for TranslationAdmin, RelatedTranslationField and subclasses

settings.LANGUAGES = (('de', 'Deutsch'),
                      ('en', 'English'))


class RelatedModel(models.Model):
    reltitle = models.CharField(ugettext_lazy('Related Title'), max_length=255)


class TestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(null=True)
    url = models.URLField(verify_exists=False, null=True)
    email = models.EmailField(null=True)
    xml = models.XMLField(null=True)
    fk = models.ForeignKey(RelatedModel, null=True)
    o2o = models.OneToOneField(RelatedModel, null=True)
    m2m = models.ManyToManyField(RelatedModel, null=True)
    #boolean = models.BooleanField()
    #nullboolean = models.NullBooleanField()
    #integer = models.IntegerField(null=True)
    #biginteger = models.BigIntegerField(null=True)
    #positiveinteger = models.PositiveIntegerField(null=True)
    #positivesmallinteger = models.PositiveSmallIntegerField(null=True)
    #smallinteger = models.SmallIntegerField(null=True)
    #csvinteger = models.CommaSeparatedIntegerField(max_length=255, null=True)


class TestTranslationOptions(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email', 'xml', 'fk', 'o2o', 'm2m',)
    #fields = ('title', 'text', 'url', 'email', 'xml', 'boolean',
              #'nullboolean', 'integer', 'biginteger', 'positiveinteger',
              #'positivesmallinteger', 'smallinteger',
              #'csvinteger',)

translator.translator._registry = {}
translator.translator.register(TestModel, TestTranslationOptions)


class TestModelWithFallback(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(null=True)
    url = models.URLField(verify_exists=False, null=True)
    email = models.EmailField(null=True)
    xml = models.XMLField(null=True)
    fk = models.ForeignKey(RelatedModel, null=True)
    o2o = models.OneToOneField(RelatedModel, null=True)
    m2m = models.ManyToManyField(RelatedModel, null=True)
    #boolean = models.BooleanField()
    #nullboolean = models.NullBooleanField()
    #integer = models.IntegerField(null=True)
    #biginteger = models.BigIntegerField(null=True)
    #positiveinteger = models.PositiveIntegerField(null=True)
    #positivesmallinteger = models.PositiveSmallIntegerField(null=True)
    #smallinteger = models.SmallIntegerField(null=True)
    #csvinteger = models.CommaSeparatedIntegerField(max_length=255, null=True)


class TestTranslationOptionsWithFallback(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email', 'xml', 'fk', 'o2o', 'm2m',)
    #fields = ('title', 'text', 'url', 'email', 'xml', 'boolean',
              #'nullboolean', 'integer', 'biginteger', 'positiveinteger',
              #'positivesmallinteger', 'smallinteger',
              #'csvinteger',)
    fallback_values = ""

translator.translator.register(TestModelWithFallback,
                               TestTranslationOptionsWithFallback)


class TestModelWithFallback2(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(null=True)
    url = models.URLField(verify_exists=False, null=True)
    email = models.EmailField(null=True)
    xml = models.XMLField(null=True)
    fk = models.ForeignKey(RelatedModel, null=True)
    o2o = models.OneToOneField(RelatedModel, null=True)
    m2m = models.ManyToManyField(RelatedModel, null=True)
    #boolean = models.BooleanField()
    #nullboolean = models.NullBooleanField()
    #integer = models.IntegerField(null=True)
    #biginteger = models.BigIntegerField(null=True)
    #positiveinteger = models.PositiveIntegerField(null=True)
    #positivesmallinteger = models.PositiveSmallIntegerField(null=True)
    #smallinteger = models.SmallIntegerField(null=True)
    #csvinteger = models.CommaSeparatedIntegerField(max_length=255, null=True)


class TestTranslationOptionsWithFallback2(translator.TranslationOptions):
    fields = ('title', 'text', 'url', 'email', 'xml', 'fk', 'o2o', 'm2m',)
    #fields = ('title', 'text', 'url', 'email', 'xml', 'boolean',
              #'nullboolean', 'integer', 'biginteger', 'positiveinteger',
              #'positivesmallinteger', 'smallinteger',
              #'csvinteger',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not '
                                             'available.')}

translator.translator.register(TestModelWithFallback2,
                               TestTranslationOptionsWithFallback2)


class ModeltranslationTestBase(TestCase):
    urls = 'modeltranslation.testurls'

    def setUp(self):
        trans_real.activate("de")

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

        # Check that three models are registered for translation
        self.failUnlessEqual(len(translator.translator._registry), 3)

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
        self.failUnless('xml' in field_names)
        self.failUnless('xml_de' in field_names)
        self.failUnless('xml_en' in field_names)
        self.failUnless('fk' in field_names)
        self.failUnless('fk_de' in field_names)
        self.failUnless('fk_en' in field_names)
        self.failUnless('o2o' in field_names)
        self.failUnless('o2o_de' in field_names)
        self.failUnless('o2o_en' in field_names)
        self.failUnless('m2m' in field_names)
        self.failUnless('m2m_de' in field_names)
        self.failUnless('m2m_en' in field_names)
        #self.failUnless('boolean' in field_names)
        #self.failUnless('boolean_de' in field_names)
        #self.failUnless('boolean_en' in field_names)
        #self.failUnless('nullboolean' in field_names)
        #self.failUnless('nullboolean_de' in field_names)
        #self.failUnless('nullboolean_en' in field_names)
        #self.failUnless('integer' in field_names)
        #self.failUnless('integer_de' in field_names)
        #self.failUnless('integer_en' in field_names)
        #self.failUnless('biginteger' in field_names)
        #self.failUnless('biginteger_de' in field_names)
        #self.failUnless('biginteger_en' in field_names)
        #self.failUnless('positiveinteger' in field_names)
        #self.failUnless('positiveinteger_de' in field_names)
        #self.failUnless('positiveinteger_en' in field_names)
        #self.failUnless('positivesmallinteger' in field_names)
        #self.failUnless('positivesmallinteger_de' in field_names)
        #self.failUnless('positivesmallinteger_en' in field_names)
        #self.failUnless('smallinteger' in field_names)
        #self.failUnless('smallinteger_de' in field_names)
        #self.failUnless('smallinteger_en' in field_names)
        #self.failUnless('csvinteger' in field_names)
        #self.failUnless('csvinteger_de' in field_names)
        #self.failUnless('csvinteger_en' in field_names)
        inst.delete()

    def test_verbose_name(self):
        inst = TestModel.objects.create(title="Testtitle", text="Testtext")
        self.assertEquals(\
        unicode(inst._meta.get_field('title_de').verbose_name), u'Titel [de]')
        inst.delete()

    def test_set_translation(self):
        self.failUnlessEqual(get_language(), "de")
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
        self.failUnlessEqual(n.text,\
        TestTranslationOptionsWithFallback2.fallback_values['text'])


class ModeltranslationTestRule1(ModeltranslationTestBase):
    """
    Rule 1: Reading the value from the original field returns the value in
    translated to the current language.
    """
    def _test_field(self, field_name, value_de, value_en, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de',
                  'title_en': 'title en'}
        params[field_name_de] = value_de
        params[field_name_en] = value_en

        n = TestModel.objects.create(**params)
        # Language is set to "de" at this point
        self.failUnlessEqual(get_language(), "de")
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
        trans_real.activate("de")
        self.failUnlessEqual(get_language(), "de")
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

        # Language is set to "de" at this point
        self.failUnlessEqual(get_language(), "de")
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
        trans_real.activate("de")
        self.failUnlessEqual(get_language(), "de")
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

    def test_rule1_xml_field(self):
        self._test_field(field_name='xml',\
        value_de='<?xml version="1.0" encoding="UTF-8" ?><foo>bar</foo>',
        value_en='<?xml version="1.0" encoding="UTF-8" ?><foo>baz</foo>')

    def test_rule1_foreignkey(self):
        rel1 = RelatedModel.objects.create(reltitle='German related title')
        rel2 = RelatedModel.objects.create(reltitle='English related title')
        self._test_field(field_name='fk',
                         value_de=rel1,
                         value_en=rel2)

    def test_rule1_onetoone_field(self):
        # TODO: Required custom field test
        rel1 = RelatedModel.objects.create(reltitle='German related title')
        rel2 = RelatedModel.objects.create(reltitle='English related title')
        self._test_field(field_name='o2o',
                         value_de=rel1,
                         value_en=rel2)

    def test_rule1_manytomany_field(self):
        # TODO: Required custom field test
        rel1 = RelatedModel.objects.create(reltitle='German related title')
        rel2 = RelatedModel.objects.create(reltitle='English related title')
        self._test_field(field_name='m2m',
                         value_de=rel1,
                         value_en=rel2)

    #def test_rule1_boolean_field(self):
        #self._test_field(field_name='boolean',
                         #value_de=True,
                         #value_en=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='boolean',
                         #value_de=False,
                         #value_en=True)

    #def test_rule1_nullboolean_field(self):
        #self._test_field(field_name='nullboolean',
                         #value_de=True,
                         #value_en=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='nullboolean',
                         #value_de=False,
                         #value_en=True)

    #def test_rule1_integer_field(self):
        #self._test_field(field_name='integer',
                         #value_de=42,
                         #value_en=-42)

    #def test_rule1_biginteger_field(self):
        #self._test_field(field_name='biginteger',
                         #value_de=1234567890,
                         #value_en=-1234567890)

    #def test_rule1_positiveinteger_field(self):
        #self._test_field(field_name='positiveinteger',
                         #value_de=23,
                         #value_en=42)

    #def test_rule1_positivesmallinteger_field(self):
        #self._test_field(field_name='positivesmallinteger',
                         #value_de=1,
                         #value_en=2)

    #def test_rule1_smallinteger_field(self):
        #self._test_field(field_name='smallinteger',
                         #value_de=1,
                         #value_en=-1)

    #def test_rule1_csvinteger_field(self):
        #self._test_field(field_name='csvinteger',
                         #value_de='1,2,3,4,5',
                         #value_en='5,4,3,2,1')


class ModeltranslationTestRule2(ModeltranslationTestBase):
    """
    Rule 2: Assigning a value to the original field also updates the value
    in the associated translation field of the default language
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de',
                  'title_en': 'title en'}
        params[field_name_de] = value1_de
        params[field_name_en] = value1_en

        self.failUnlessEqual(get_language(), "de")
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
        self.failUnlessEqual(get_language(), "de")
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

    def test_rule2_xml_field(self):
        self._test_field(field_name='xml',\
        value1_de='<?xml version="1.0" encoding="UTF-8" ?><foo>bar</foo>',
        value1_en='<?xml version="1.0" encoding="UTF-8" ?><foo>baz</foo>',
        value2='<?xml version="1.0" encoding="UTF-8" ?><bar>foo</bar>',
        value3='<?xml version="1.0" encoding="UTF-8" ?><baz>foo</baz>')

    def test_rule2_foreignkey(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='fk',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    def test_rule2_onetoone_field(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='o2o',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    def test_rule2_manytomany_field(self):
        # TODO: Required custom field test
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='m2m',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    #def test_rule2_boolean_field(self):
        #self._test_field(field_name='boolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2=True,
                         #value3=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='boolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2=False,
                         #value3=True)

    #def test_rule2_nullboolean_field(self):
        #self._test_field(field_name='nullboolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2=True,
                         #value3=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='nullboolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2=False,
                         #value3=True)

    #def test_rule2_integer_field(self):
        #self._test_field(field_name='integer',
                         #value1_de=42,
                         #value1_en=-42,
                         #value2=23,
                         #value3=32)

    #def test_rule2_biginteger_field(self):
        #self._test_field(field_name='biginteger',
                         #value1_de=1234567890,
                         #value1_en=-1234567890,
                         #value2=987654321,
                         #value3=-987654321)

    #def test_rule2_positiveinteger_field(self):
        #self._test_field(field_name='positiveinteger',
                         #value1_de=23,
                         #value1_en=42,
                         #value2=123,
                         #value3=321)

    #def test_rule2_positivesmallinteger_field(self):
        #self._test_field(field_name='positivesmallinteger',
                         #value1_de=1,
                         #value1_en=2,
                         #value2=3,
                         #value3=4)

    #def test_rule2_smallinteger_field(self):
        #self._test_field(field_name='smallinteger',
                         #value1_de=1,
                         #value1_en=-1,
                         #value2=2,
                         #value3=-2)

    #def test_rule2_csvinteger_field(self):
        #self._test_field(field_name='csvinteger',
                         #value1_de='1,2,3,4,5',
                         #value1_en='5,4,3,2,1',
                         #value2='6,7,8',
                         #value3='9,8,10')


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
        params = {'title_de': 'title de',
                  'title_en': 'title en'}
        params[field_name_de] = value1_de
        params[field_name_en] = value1_en

        n = TestModel.objects.create(**params)

        self.failUnlessEqual(get_language(), "de")
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
        self.failUnlessEqual(get_language(), "de")
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        n.title_de = "Neuer Titel"
        n.save()
        self.failUnlessEqual(n.title, n.title_de)

        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        n.title_en = "New title"
        # the n.title field is not updated before the instance is saved
        n.save()
        self.failUnlessEqual(n.title, n.title_en)
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

    def test_rule3_xml_field(self):
        self._test_field(field_name='xml',\
        value1_de='<?xml version="1.0" encoding="UTF-8" ?><foo>bar</foo>',
        value1_en='<?xml version="1.0" encoding="UTF-8" ?><foo>baz</foo>',
        value2='<?xml version="1.0" encoding="UTF-8" ?><bar>foo</bar>',
        value3='<?xml version="1.0" encoding="UTF-8" ?><baz>foo</baz>')

    def test_rule3_foreignkey(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='fk',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    def test_rule3_onetoone_field(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='o2o',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    def test_rule3_manytomany_field(self):
        # TODO: Required custom field test
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2 = RelatedModel.objects.create(reltitle='Related title2')
        rel3 = RelatedModel.objects.create(reltitle='Related title3')
        self._test_field(field_name='m2m',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2=rel2,
                         value3=rel3)

    #def test_rule3_boolean_field(self):
        #self._test_field(field_name='boolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2=True,
                         #value3=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='boolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2=False,
                         #value3=True)

    #def test_rule3_nullboolean_field(self):
        #self._test_field(field_name='nullboolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2=True,
                         #value3=False,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='nullboolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2=False,
                         #value3=True)

    #def test_rule3_integer_field(self):
        #self._test_field(field_name='integer',
                         #value1_de=42,
                         #value1_en=-42,
                         #value2=23,
                         #value3=32)

    #def test_rule3_biginteger_field(self):
        #self._test_field(field_name='biginteger',
                         #value1_de=1234567890,
                         #value1_en=-1234567890,
                         #value2=987654321,
                         #value3=-987654321)

    #def test_rule3_positiveinteger_field(self):
        #self._test_field(field_name='positiveinteger',
                         #value1_de=23,
                         #value1_en=42,
                         #value2=123,
                         #value3=321)

    #def test_rule3_positivesmallinteger_field(self):
        #self._test_field(field_name='positivesmallinteger',
                         #value1_de=1,
                         #value1_en=2,
                         #value2=3,
                         #value3=4)

    #def test_rule3_smallinteger_field(self):
        #self._test_field(field_name='smallinteger',
                         #value1_de=1,
                         #value1_en=-1,
                         #value2=2,
                         #value3=-2)

    #def test_rule3_csvinteger_field(self):
        #self._test_field(field_name='csvinteger',
                         #value1_de='1,2,3,4,5',
                         #value1_en='5,4,3,2,1',
                         #value2='6,7,8',
                         #value3='9,8,10')


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
        params = {'title_de': 'title de',
                  'title_en': 'title en'}
        params[field_name_de] = value1_de
        params[field_name_en] = value1_en

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
        self.failUnlessEqual(get_language(), "de")
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

    def test_rule4_xml_field(self):
        self._test_field(field_name='xml',\
        value1_de='<?xml version="1.0" encoding="UTF-8" ?><foo>bar</foo>',
        value1_en='<?xml version="1.0" encoding="UTF-8" ?><foo>baz</foo>',
        value2_de='<?xml version="1.0" encoding="UTF-8" ?><bar>foo</bar>',
        value2_en='<?xml version="1.0" encoding="UTF-8" ?><baz>foo</baz>',
        value3='<?xml version="1.0" encoding="UTF-8" ?><baz>bar</baz>')

    def test_rule4_foreignkey(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2_de = RelatedModel.objects.create(reltitle='Rel German title2')
        rel2_en = RelatedModel.objects.create(reltitle='Rel English title2')
        rel3 = RelatedModel.objects.create(reltitle='Rel title3')
        self._test_field(field_name='fk',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2_de=rel2_de,
                         value2_en=rel2_en,
                         value3=rel3)

    def test_rule4_onetoone_field(self):
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2_de = RelatedModel.objects.create(reltitle='Rel German title2')
        rel2_en = RelatedModel.objects.create(reltitle='Rel English title2')
        rel3 = RelatedModel.objects.create(reltitle='Rel title3')
        self._test_field(field_name='o2o',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2_de=rel2_de,
                         value2_en=rel2_en,
                         value3=rel3)

    def test_rule4_manytomany_field(self):
        # TODO: Required custom field test
        rel1_de = RelatedModel.objects.create(reltitle='German related title')
        rel1_en = RelatedModel.objects.create(reltitle='English related title')
        rel2_de = RelatedModel.objects.create(reltitle='Rel German title2')
        rel2_en = RelatedModel.objects.create(reltitle='Rel English title2')
        rel3 = RelatedModel.objects.create(reltitle='Rel title3')
        self._test_field(field_name='m2m',
                         value1_de=rel1_de,
                         value1_en=rel1_en,
                         value2_de=rel2_de,
                         value2_en=rel2_en,
                         value3=rel3)

    #def test_rule4_boolean_field(self):
        #self._test_field(field_name='boolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2_de=True,
                         #value2_en=False,
                         #value3=True,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='boolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2_de=False,
                         #value2_en=True,
                         #value3=True)

    #def test_rule4_nullboolean_field(self):
        #self._test_field(field_name='nullboolean',
                         #value1_de=True,
                         #value1_en=False,
                         #value2_de=True,
                         #value2_en=False,
                         #value3=True,
                         #deactivate=False)
        ## Now with swapped values
        #self._test_field(field_name='nullboolean',
                         #value1_de=False,
                         #value1_en=True,
                         #value2_de=False,
                         #value2_en=True,
                         #value3=False)

    #def test_rule4_integer_field(self):
        #self._test_field(field_name='integer',
                         #value1_de=42,
                         #value1_en=-42,
                         #value2_de=23,
                         #value2_en=32,
                         #value3=33)

    #def test_rule4_biginteger_field(self):
        #self._test_field(field_name='biginteger',
                         #value1_de=1234567890,
                         #value1_en=-1234567890,
                         #value2_de=987654321,
                         #value2_en=-987654321,
                         #value3=987654322)

    #def test_rule4_positiveinteger_field(self):
        #self._test_field(field_name='positiveinteger',
                         #value1_de=23,
                         #value1_en=42,
                         #value2_de=123,
                         #value2_en=321,
                         #value3=322)

    #def test_rule4_positivesmallinteger_field(self):
        #self._test_field(field_name='positivesmallinteger',
                         #value1_de=1,
                         #value1_en=2,
                         #value2_de=3,
                         #value2_en=4,
                         #value3=5)

    #def test_rule4_smallinteger_field(self):
        #self._test_field(field_name='smallinteger',
                         #value1_de=1,
                         #value1_en=-1,
                         #value2_de=2,
                         #value2_en=-2,
                         #value3=3)

    #def test_rule4_csvinteger_field(self):
        #self._test_field(field_name='csvinteger',
                         #value1_de='1,2,3,4,5',
                         #value1_en='5,4,3,2,1',
                         #value2_de='6,7,8',
                         #value2_en='9,8,10',
                         #value3='9,8,10,11')
