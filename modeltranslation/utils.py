# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import get_language as _get_language
from django.utils.functional import lazy


def get_available_languages():
    """Returns a list of the language codes in settings.LANGUAGES"""
    return [l[0] for l in settings.LANGUAGES]


def get_language():
    """
    Return an active language code that is guaranteed to be in
    settings.LANGUAGES (Django does not seem to guarantee this for us).
    """
    lang = _get_language()
    available_languages = get_available_languages()
    if lang not in available_languages and '-' in lang:
        lang = lang.split('-')[0]
    if lang in available_languages:
        return lang
    return available_languages[0]


def get_default_language():
    """
    Returns the language to use as the default language. This is either
    the value of settings.DEFAULT_LANGUAGE (if it's in the list of
    settings.LANGUAGES) or the first item in settings.LANGUAGES.
    """
    available_languages = get_available_languages()
    default_language = getattr(settings,
                               'MODELTRANSLATION_DEFAULT_LANGUAGE', None)
    if default_language and default_language not in available_languages:
        raise ImproperlyConfigured('MODELTRANSLATION_DEFAULT_LANGUAGE not '
                                   'in LANGUAGES setting.')
    if not default_language:
        default_language = available_languages[0]
    return default_language


def get_translation_fields(field):
    """Returns a list of localized fieldnames for a given field."""
    return [build_localized_fieldname(field, l) for l in\
            get_available_languages()]


def build_localized_fieldname(field_name, lang):
    return '%s_%s' % (field_name, lang.replace('-', '_'))


def _build_localized_verbose_name(verbose_name, lang):
    return u'%s [%s]' % (verbose_name, lang)
build_localized_verbose_name = lazy(_build_localized_verbose_name, unicode)
