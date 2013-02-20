# -*- coding: utf-8 -*-
"""
Settings overrided for test time
"""
from django.conf import settings


INSTALLED_APPS = tuple(settings.INSTALLED_APPS) + (
    'modeltranslation.tests',
)
# IMO this is unimportant
#if django.VERSION[0] >= 1 and django.VERSION[1] >= 3:
    #INSTALLED_APPS += ('django.contrib.staticfiles',)

#STATIC_URL = '/static/'

LANGUAGES = (('de', 'Deutsch'),
             ('en', 'English'))
LANGUAGE_CODE = 'de'
MODELTRANSLATION_DEFAULT_LANGUAGE = 'de'

USE_I18N = True
USE_TZ = False

MODELTRANSLATION_AUTO_POPULATE = False
MODELTRANSLATION_FALLBACK_LANGUAGES = ()
