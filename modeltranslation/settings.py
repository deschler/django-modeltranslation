# -*- coding: utf-8 -*-
import sys
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
if not TRANSLATION_FILES:
    raise ImproperlyConfigured(
        "You haven't set the MODELTRANSLATION_TRANSLATION_FILES setting yet.")

AVAILABLE_LANGUAGES = [l[0] for l in settings.LANGUAGES]
DEFAULT_LANGUAGE = getattr(settings, 'MODELTRANSLATION_DEFAULT_LANGUAGE', None)
if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE not in AVAILABLE_LANGUAGES:
    raise ImproperlyConfigured('MODELTRANSLATION_DEFAULT_LANGUAGE not '
                               'in LANGUAGES setting.')
elif not DEFAULT_LANGUAGE:
    DEFAULT_LANGUAGE = AVAILABLE_LANGUAGES[0]

# FIXME: We can't seem to override this particular setting in tests.py
CUSTOM_FIELDS = getattr(settings, 'MODELTRANSLATION_CUSTOM_FIELDS', ())
try:
    if sys.argv[1] == 'test':
        CUSTOM_FIELDS = getattr(
            settings, 'MODELTRANSLATION_CUSTOM_FIELDS', ('BooleanField',))
except IndexError:
    pass

# Don't change this setting unless you really know what you are doing
ENABLE_REGISTRATIONS = getattr(
    settings, 'MODELTRANSLATION_ENABLE_REGISTRATIONS', settings.USE_I18N)
