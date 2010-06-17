# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import get_language as _get_language
from django.utils.functional import lazy


def get_language():
    """
    Return an active language code that is guaranteed to be in
    settings.LANGUAGES (Django does not seem to guarantee this for us.)
    """
    lang = _get_language()
    available_languages = [l[0] for l in settings.LANGUAGES]
    if lang not in available_languages and '-' in lang:
        lang = lang.split('-')[0]
    if lang in available_languages:
        return lang
    return available_languages[0]


def get_default_language():
    return settings.LANGUAGES[0][0]


def get_translation_fields(field):
    """Returns a list of localized fieldnames for a given field."""
    return [build_localized_fieldname(field, l[0]) for l in settings.LANGUAGES]


def build_localized_fieldname(field_name, lang):
    return '%s_%s' % (field_name, lang.replace('-', '_'))


def _build_localized_verbose_name(verbose_name, lang):
    return u'%s [%s]' % (verbose_name, lang)
build_localized_verbose_name = lazy(_build_localized_verbose_name, unicode)


class TranslationFieldDescriptor(object):
    """A descriptor used for the original translated field."""
    def __init__(self, name, initial_val=""):
        """
        The ``name`` is the name of the field (which is not available in the
        descriptor by default - this is Python behaviour).
        """
        self.name = name
        self.val = initial_val

    def __set__(self, instance, value):
        lang = get_language()
        loc_field_name = build_localized_fieldname(self.name, lang)
        # also update the translation field of the current language
        setattr(instance, loc_field_name, value)
        # update the original field via the __dict__ to prevent calling the
        # descriptor
        instance.__dict__[self.name] = value

    def __get__(self, instance, owner):
        if not instance:
            raise ValueError(u"Translation field '%s' can only be "
                              "accessed via an instance not via "
                              "a class." % self.name)
        lang = get_language()
        loc_field_name = build_localized_fieldname(self.name, lang)
        if hasattr(instance, loc_field_name):
            return getattr(instance, loc_field_name) or \
                   instance.__dict__[self.name]
        #return instance.__dict__[self.name]
        # FIXME: KeyError raised for ForeignKeyTanslationField
        #        in admin list view
        try:
            return instance.__dict__[self.name]
        except KeyError:
            return None
