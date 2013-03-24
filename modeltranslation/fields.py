# -*- coding: utf-8 -*-
from django import forms
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
    fields.related.ForeignKey,
)
try:
    SUPPORTED_FIELDS += (fields.GenericIPAddressField,)  # Django 1.4+ only
except AttributeError:
    pass


class NONE:
    """
    Used for fallback options when they are not provided (``None`` can be
    given as a fallback or undefined value) or to mark that a nullable value
    is not yet known and needs to be computed (e.g. field default).
    """
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


def create_nullable_formfield(form_class):
    """
    Creates a form class subclass that ensures that ``None`` is not cast to
    anything (like the empty string with ``CharField`` and its derivatives).
    """
    class NullableField(form_class):
        def to_python(self, value):
            if value is None:
                return value
            return super(NullableField, self).to_python(value)
    NullableField.__name__ = 'Nullable%s' % form_class.__name__
    return NullableField


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

        # ForeignKey support - rewrite related_name
        if self.rel and self.related and not self.rel.is_hidden():
            import copy
            current = self.related.get_accessor_name()
            self.rel = copy.copy(self.rel)  # Since fields cannot share the same rel object.
            # self.related doesn't need to be copied, as it will be recreated in
            # ``RelatedField.do_related_class``

            if self.rel.related_name is None:
                # For implicit related_name use different query field name
                loc_related_query_name = build_localized_fieldname(
                    self.related_query_name(), self.language)
                self.related_query_name = lambda: loc_related_query_name
            self.rel.related_name = build_localized_fieldname(current, self.language)
            if hasattr(self.rel.to._meta, '_related_objects_cache'):
                del self.rel.to._meta._related_objects_cache

    # Django 1.5 changed definition of __hash__ for fields to be fine with hash requirements.
    # It spoiled our machinery, since TranslationField has the same creation_counter as its
    # original field and fields didn't get added to sets.
    # So here we override __eq__ and __hash__ to fix the issue while retaining fine with
    # http://docs.python.org/2.7/reference/datamodel.html#object.__hash__
    def __eq__(self, other):
        if isinstance(other, fields.Field):
            return (self.creation_counter == other.creation_counter and
                    self.language == getattr(other, 'language', None))
        return super(TranslationField, self).__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.creation_counter, self.language))

    def get_attname_column(self):
        attname = self.get_attname()
        if self.translated_field.db_column:
            column = build_localized_fieldname(self.translated_field.db_column)
        else:
            column = attname
        return attname, column

    def formfield(self, *args, **kwargs):
        """
        If the original field is nullable and uses ``forms.CharField`` subclass
        as its form input, we patch the form field, so it doesn't cast ``None``
        to anything.

        The ``forms.CharField`` somewhat surprising behaviour is documented as a
        "won't fix": https://code.djangoproject.com/ticket/9590.
        """
        formfield = super(TranslationField, self).formfield(*args, **kwargs)
        if (self.translated_field.null and
                issubclass(formfield.__class__, forms.CharField)):
            kwargs['form_class'] = create_nullable_formfield(formfield.__class__)
            formfield = super(TranslationField, self).formfield(*args, **kwargs)
        return formfield

    def south_field_triple(self):
        """
        Returns a suitable description of this field for South.
        """
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        try:
            # Check if the field provides its own 'field_class':
            field_class = self.translated_field.south_field_triple()[0]
        except AttributeError:
            field_class = '%s.%s' % (self.translated_field.__class__.__module__,
                                     self.translated_field.__class__.__name__)
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)


class TranslationFieldDescriptor(object):
    """
    A descriptor used for the original translated field.
    """
    def __init__(self, field, fallback_languages=None, fallback_value=NONE,
                 fallback_undefined=NONE):
        """
        Stores fallback options and the original field, so we know it's name
        and default.
        """
        self.field = field
        self.fallback_languages = fallback_languages
        self.fallback_value = fallback_value
        self.fallback_undefined = fallback_undefined

    def __set__(self, instance, value):
        """
        Updates the translation field for the current language.
        """
        loc_field_name = build_localized_fieldname(self.field.name, get_language())
        setattr(instance, loc_field_name, value)

    def __get__(self, instance, owner):
        """
        Returns value from the translation field for the current language, or
        value for some another language according to fallback languages, or the
        custom fallback value, or field's default value.
        """
        if instance is None:
            return self
        default = NONE
        undefined = self.fallback_undefined
        if undefined is NONE:
            default = self.field.get_default()
            undefined = default
        langs = resolution_order(get_language(), self.fallback_languages)
        for lang in langs:
            loc_field_name = build_localized_fieldname(self.field.name, lang)
            val = getattr(instance, loc_field_name, None)
            if val is not None and val != undefined:
                return val
        if mt_settings.ENABLE_FALLBACKS and self.fallback_value is not NONE:
            return self.fallback_value
        else:
            if default is NONE:
                default = self.field.get_default()
            return default


class TranslatedRelationIdDescriptor(object):
    """
    A descriptor used for the original '_id' attribute of a translated
    ForeignKey field.
    """
    def __init__(self, field_name, fallback_languages):
        self.field_name = field_name  # The name of the original field (excluding '_id')
        self.fallback_languages = fallback_languages

    def __set__(self, instance, value):
        lang = get_language()
        loc_field_name = build_localized_fieldname(self.field_name, lang)
        # Localized field name with '_id'
        loc_attname = instance._meta.get_field(loc_field_name).get_attname()
        setattr(instance, loc_attname, value)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        langs = resolution_order(get_language(), self.fallback_languages)
        for lang in langs:
            loc_field_name = build_localized_fieldname(self.field_name, lang)
            # Localized field name with '_id'
            loc_attname = instance._meta.get_field(loc_field_name).get_attname()
            val = getattr(instance, loc_attname, None)
            if val is not None:
                return val
        return None
