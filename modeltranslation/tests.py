# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase
from django.utils.thread_support import currentThread
from django.utils.translation import get_language
from django.utils.translation import trans_real

# TODO: tests for TranslationAdmin

from modeltranslation import translator

settings.LANGUAGES = (('de', 'Deutsch'),
                      ('en', 'English'))


class TestModel(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField(null=True)


class TestTranslationOptions(translator.TranslationOptions):
    fields = ('title', 'text',)


translator.translator._registry = {}
translator.translator.register(TestModel, TestTranslationOptions)


class ModelTranslationTest(TestCase):    
    """Basic tests for the modeltranslation application."""
    
    urls = 'modeltranslation.testurls'
    
    def setUp(self):        
        trans_real.activate("de")
                
    def tearDown(self):
        trans_real.deactivate()


    def test_registration(self):
        self.client.post('/set_language/', data={'language': 'de'})
        #self.client.session['django_language'] = 'de-de'        
        #self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'de-de'
                
        langs = tuple(l[0] for l in settings.LANGUAGES)
        self.failUnlessEqual(2, len(langs))
        self.failUnless('de' in langs)
        self.failUnless('en' in langs)        
        self.failUnless(translator.translator)

        # Check that only one model is registered for translation
        self.failUnlessEqual(len(translator.translator._registry), 1)
                
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
        self.failUnless('text' in field_names)
        self.failUnless('title_de' in field_names)   
        self.failUnless('title_en' in field_names)   
        self.failUnless('text_de' in field_names)   
        self.failUnless('text_en' in field_names)   
        
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
        
    def test_rule1(self):                        
        """
        Rule 1: Reading the value from the original field returns the value in 
        translated to the current language.
        """
        title1_de = "title de"
        title1_en = "title en"
        text_de = "Dies ist ein deutscher Satz"
        text_en = "This is an english sentence"
        
        # Test 1.
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en,
                                     text_de=text_de, text_en=text_en)
        n.save()
        
        # language is set to "de" at this point
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
        # language is set to "en" at this point
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
                
    def test_rule2(self):                                            
        """
        Rule 2: Assigning a value to the original field also updates the value
        in the associated translation field of the default language
        """
        self.failUnlessEqual(get_language(), "de")
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)                            
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)
                    
        title2 =  "Neuer Titel"                   
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
                
    def test_rule3(self):
        """
        Rule 3: Assigning a value to a translation field of the default language
        also updates the original field - note that the value of the original 
        field will not be updated until the model instance is saved.
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
                
    def test_rule4(self):                                
        """
        Rule 4: If both fields - the original and the translation field of the 
        default language - are updated at the same time, the translation field 
        wins.
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
        
