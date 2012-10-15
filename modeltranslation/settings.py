# -*- coding: utf-8 -*-
from warnings import warn

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


TRANSLATION_FILES = tuple(
    getattr(settings, 'MODELTRANSLATION_TRANSLATION_FILES', ()))
TRANSLATION_REGISTRY = getattr(
    settings, 'MODELTRANSLATION_TRANSLATION_REGISTRY', None)
if TRANSLATION_REGISTRY:
    TRANSLATION_FILES += (TRANSLATION_REGISTRY,)
    warn('The setting MODELTRANSLATION_TRANSLATION_REGISTRY is deprecated, '
         'use MODELTRANSLATION_TRANSLATION_FILES instead.', DeprecationWarning)

AVAILABLE_LANGUAGES = [l[0] for l in settings.LANGUAGES]
DEFAULT_LANGUAGE = getattr(settings, 'MODELTRANSLATION_DEFAULT_LANGUAGE', None)
if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE not in AVAILABLE_LANGUAGES:
    raise ImproperlyConfigured('MODELTRANSLATION_DEFAULT_LANGUAGE not '
                               'in LANGUAGES setting.')
elif not DEFAULT_LANGUAGE:
    DEFAULT_LANGUAGE = AVAILABLE_LANGUAGES[0]

# Load allowed CUSTOM_FIELDS from django settings
CUSTOM_FIELDS = getattr(settings, 'MODELTRANSLATION_CUSTOM_FIELDS', ())

# Don't change this setting unless you really know what you are doing
ENABLE_REGISTRATIONS = getattr(
    settings, 'MODELTRANSLATION_ENABLE_REGISTRATIONS', settings.USE_I18N)

# Modeltranslation specific debug setting
DEBUG = getattr(
    settings, 'MODELTRANSLATION_DEBUG', settings.DEBUG)
