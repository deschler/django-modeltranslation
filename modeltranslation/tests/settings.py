# -*- coding: utf-8 -*-
"""
Settings overrided for test time
"""
from django.conf import settings


INSTALLED_APPS = tuple(settings.INSTALLED_APPS) + (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'modeltranslation.tests',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

LANGUAGES = (('de', 'Deutsch'),
             ('en', 'English'))
LANGUAGE_CODE = 'de'
MODELTRANSLATION_DEFAULT_LANGUAGE = 'de'

USE_I18N = True
USE_TZ = False

MODELTRANSLATION_AUTO_POPULATE = False
MODELTRANSLATION_FALLBACK_LANGUAGES = ()
