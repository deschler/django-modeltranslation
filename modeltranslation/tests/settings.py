# -*- coding: utf-8 -*-
import os
import django


DIRNAME = os.path.dirname(__file__)

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DIRNAME, 'test.db')
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.redirects',
    'modeltranslation',
    'modeltranslation.tests',
)
if django.VERSION[0] >= 1 and django.VERSION[1] >= 3:
    INSTALLED_APPS += ('django.contrib.staticfiles',)

STATIC_URL = '/static/'

ROOT_URLCONF = 'modeltranslation.tests.urls'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(DIRNAME, 'media/')

SITE_ID = 1

LANGUAGES = (('de', 'Deutsch'),
             ('en', 'English'))
DEFAULT_LANGUAGE = 'de'

MODELTRANSLATION_TRANSLATION_REGISTRY = 'modeltranslation.tests'
