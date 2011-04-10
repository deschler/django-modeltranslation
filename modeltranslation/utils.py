# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import get_language as _get_language
from django.utils.functional import lazy

from modeltranslation.settings import *


def get_language():
    """
    Return an active language code that is guaranteed to be in
    settings.LANGUAGES (Django does not seem to guarantee this for us).
    """
    lang = _get_language()
    if lang not in AVAILABLE_LANGUAGES and '-' in lang:
        lang = lang.split('-')[0]
    if lang in AVAILABLE_LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


def get_translation_fields(field):
    """Returns a list of localized fieldnames for a given field."""
    return [build_localized_fieldname(field, l) for l in AVAILABLE_LANGUAGES]


def build_localized_fieldname(field_name, lang):
    return str('%s_%s' % (field_name, lang.replace('-', '_')))


def _build_localized_verbose_name(verbose_name, lang):
    return u'%s [%s]' % (verbose_name, lang)
build_localized_verbose_name = lazy(_build_localized_verbose_name, unicode)
