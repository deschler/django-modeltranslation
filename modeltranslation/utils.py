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


class TranslationFieldDescriptor(object):
    """A descriptor used for the original translated field."""
    def __init__(self, name, initial_val="", fallback_value=None):
        """
        The ``name`` is the name of the field (which is not available in the
        descriptor by default - this is Python behaviour).
        """
        self.name = name
        self.val = initial_val
        self.fallback_value = fallback_value
        self.loc_field_name = ""

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
            raise ValueError(u"Translation field '%s' can only be accessed "
                              "via an instance not via a class." % self.name)
        self.loc_field_name = build_localized_fieldname(self.name,
                                                        get_language())
        if hasattr(instance, self.loc_field_name):
            return getattr(instance, self.loc_field_name) or\
                   (self.get_default_instance(instance) if\
                    self.fallback_value is None else\
                    self.fallback_value)

    def get_default_instance(self, instance):
        """
        Returns default instance of the field. Supposed to be overidden by
        related subclasses.
        """
        return instance.__dict__[self.name]
        

class RelatedTranslationFieldDescriptor(TranslationFieldDescriptor):
    def __init__(self, name, initial_val="", fallback_value=None):
        TranslationFieldDescriptor.__init__(self, name, initial_val="",
                                            fallback_value=None)

    def get_default_instance(self, instance):
        # TODO: Implement
        #instance_id = instance.__dict__['%s_id' % self.name]
        pass


class ManyToManyTranslationFieldDescriptor(TranslationFieldDescriptor):
    def __init__(self, name, initial_val="", fallback_value=None):
        TranslationFieldDescriptor.__init__(self, name, initial_val="",
                                            fallback_value=None)

    def get_default_instance(self, instance):
        # TODO: Implement
        pass
