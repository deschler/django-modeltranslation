# -*- coding: utf-8 -*-
from warnings import warn

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


TRANSLATION_FILES = tuple(getattr(settings, 'MODELTRANSLATION_TRANSLATION_FILES', ()))
TRANSLATION_REGISTRY = getattr(settings, 'MODELTRANSLATION_TRANSLATION_REGISTRY', None)
if TRANSLATION_REGISTRY:
    TRANSLATION_FILES += (TRANSLATION_REGISTRY,)
    warn('The setting MODELTRANSLATION_TRANSLATION_REGISTRY is deprecated, '
         'use MODELTRANSLATION_TRANSLATION_FILES instead.', DeprecationWarning)

AVAILABLE_LANGUAGES = [l[0] for l in settings.LANGUAGES]
DEFAULT_LANGUAGE = getattr(settings, 'MODELTRANSLATION_DEFAULT_LANGUAGE', None)
if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE not in AVAILABLE_LANGUAGES:
    raise ImproperlyConfigured('MODELTRANSLATION_DEFAULT_LANGUAGE not in LANGUAGES setting.')
elif not DEFAULT_LANGUAGE:
    DEFAULT_LANGUAGE = AVAILABLE_LANGUAGES[0]

# Load allowed CUSTOM_FIELDS from django settings
CUSTOM_FIELDS = getattr(settings, 'MODELTRANSLATION_CUSTOM_FIELDS', ())

# Don't change this setting unless you really know what you are doing
ENABLE_REGISTRATIONS = getattr(settings, 'MODELTRANSLATION_ENABLE_REGISTRATIONS', settings.USE_I18N)

# Modeltranslation specific debug setting
DEBUG = getattr(settings, 'MODELTRANSLATION_DEBUG', settings.DEBUG)

AUTO_POPULATE = getattr(settings, 'MODELTRANSLATION_AUTO_POPULATE', False)

# FALLBACK_LANGUAGES should be in either format:
# MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'de')
# MODELTRANSLATION_FALLBACK_LANGUAGES = {'default': ('en', 'de'), 'fr': ('de',)}
# By default we fallback to the default language
FALLBACK_LANGUAGES = getattr(settings, 'MODELTRANSLATION_FALLBACK_LANGUAGES', (DEFAULT_LANGUAGE,))
if isinstance(FALLBACK_LANGUAGES, (tuple, list)):
    FALLBACK_LANGUAGES = {'default': FALLBACK_LANGUAGES}
if 'default' not in FALLBACK_LANGUAGES:
    raise ImproperlyConfigured(
        'MODELTRANSLATION_FALLBACK_LANGUAGES does not contain "default" key.')
for key, value in FALLBACK_LANGUAGES.iteritems():
    if key != 'default' and key not in AVAILABLE_LANGUAGES:
        raise ImproperlyConfigured(
            'MODELTRANSLATION_FALLBACK_LANGUAGES: "%s" not in LANGUAGES setting.' % key)
    if not isinstance(value, (tuple, list)):
        raise ImproperlyConfigured(
            'MODELTRANSLATION_FALLBACK_LANGUAGES: value for key "%s" is not list nor tuple.' % key)
    for lang in value:
        if lang not in AVAILABLE_LANGUAGES:
            raise ImproperlyConfigured(
                'MODELTRANSLATION_FALLBACK_LANGUAGES: "%s" not in LANGUAGES setting.' % lang)
