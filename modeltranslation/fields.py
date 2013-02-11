# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.db.models import fields

from modeltranslation import settings as mt_settings
from modeltranslation.utils import (
    get_language, build_localized_fieldname, build_localized_verbose_name, resolution_order)


SUPPORTED_FIELDS = (
    fields.CharField,
    # Above implies also CommaSeparatedIntegerField, EmailField, FilePathField, SlugField
    # and URLField as they are subclasses of CharField.
    fields.TextField,
    fields.IntegerField,
    # Above implies also BigIntegerField, SmallIntegerField, PositiveIntegerField and
    # PositiveSmallIntegerField, as they are subclasses of IntegerField.
    fields.BooleanField,
    fields.NullBooleanField,
    fields.FloatField,
    fields.DecimalField,
    fields.IPAddressField,
    fields.DateField,
    fields.DateTimeField,
    fields.TimeField,
    fields.files.FileField,
    fields.files.ImageField,
)
try:
    SUPPORTED_FIELDS += (fields.GenericIPAddressField,)  # Django 1.4+ only
except AttributeError:
    pass


def create_translation_field(model, field_name, lang):
    """
    Translation field factory. Returns a ``TranslationField`` based on a
    fieldname and a language.

    The list of supported fields can be extended by defining a tuple of field
    names in the projects settings.py like this::

        MODELTRANSLATION_CUSTOM_FIELDS = ('MyField', 'MyOtherField',)

    If the class is neither a subclass of fields in ``SUPPORTED_FIELDS``, nor
    in ``CUSTOM_FIELDS`` an ``ImproperlyConfigured`` exception will be raised.
    """
    field = model._meta.get_field(field_name)
    cls_name = field.__class__.__name__
    if not (isinstance(field, SUPPORTED_FIELDS) or cls_name in mt_settings.CUSTOM_FIELDS):
        raise ImproperlyConfigured(
            '%s is not supported by modeltranslation.' % cls_name)
    translation_class = field_factory(field.__class__)
    return translation_class(translated_field=field, language=lang)


def field_factory(baseclass):
    class TranslationFieldSpecific(TranslationField, baseclass):
        pass

    # Reflect baseclass name of returned subclass
    TranslationFieldSpecific.__name__ = 'Translation%s' % baseclass.__name__

    return TranslationFieldSpecific


class TranslationField(object):
    """
    The translation field functions as a proxy to the original field which is
    wrapped.

    For every field defined in the model's ``TranslationOptions`` localized
    versions of that field are added to the model depending on the languages
    given in ``settings.LANGUAGES``.

    If for example there is a model ``News`` with a field ``title`` which is
    registered for translation and the ``settings.LANGUAGES`` contains the
    ``de`` and ``en`` languages, the fields ``title_de`` and ``title_en`` will
    be added to the model class. These fields are realized using this
    descriptor.

    The translation field needs to know which language it contains therefore
    that needs to be specified when the field is created.
    """
    def __init__(self, translated_field, language, *args, **kwargs):
        # Update the dict of this field with the content of the original one
        # This might be a bit radical?! Seems to work though...
        self.__dict__.update(translated_field.__dict__)

        # Store the originally wrapped field for later
        self.translated_field = translated_field
        self.language = language

        # Translation are always optional (for now - maybe add some parameters
        # to the translation options for configuring this)

        if not isinstance(self, fields.BooleanField):
            # TODO: Do we really want to enforce null *at all*? Shouldn't this
            # better honour the null setting of the translated field?
            self.null = True
        self.blank = True

        # Adjust the name of this field to reflect the language
        self.attname = build_localized_fieldname(self.translated_field.name, self.language)
        self.name = self.attname

        # Copy the verbose name and append a language suffix
        # (will show up e.g. in the admin).
        self.verbose_name = build_localized_verbose_name(translated_field.verbose_name, language)

    def get_attname_column(self):
        attname = self.get_attname()
        column = build_localized_fieldname(
            self.translated_field.db_column or self.translated_field.name, self.language) or attname
        return attname, column

    def south_field_triple(self):
        """
        Returns a suitable description of this field for South.
        """
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = '%s.%s' % (self.translated_field.__class__.__module__,
                                 self.translated_field.__class__.__name__)
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)


class TranslationFieldDescriptor(object):
    """
    A descriptor used for the original translated field.
    """
    def __init__(self, field, fallback_value=None, fallback_languages=None):
        """
        The ``name`` is the name of the field (which is not available in the
        descriptor by default - this is Python behaviour).
        """
        self.field = field
        self.fallback_value = fallback_value
        self.fallback_languages = fallback_languages

    def __set__(self, instance, value):
        lang = get_language()
        loc_field_name = build_localized_fieldname(self.field.name, lang)
        # also update the translation field of the current language
        setattr(instance, loc_field_name, value)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        langs = resolution_order(get_language(), self.fallback_languages)
        for lang in langs:
            loc_field_name = build_localized_fieldname(self.field.name, lang)
            val = getattr(instance, loc_field_name, None)
            # Here we check only for None and '', because e.g. 0 should not fall back.
            if val is not None and val != '':
                return val
        if self.fallback_value is None:
            return self.field.get_default()
        else:
            return self.fallback_value
