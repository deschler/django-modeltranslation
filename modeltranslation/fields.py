# -*- coding: utf-8 -*-
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields import Field, CharField
from django.db.models.fields.related import (ForeignKey, OneToOneField,
                                             ManyToManyField)

from modeltranslation.utils import (get_language,
                                    get_default_language,
                                    build_localized_fieldname,
                                    build_localized_verbose_name)

# List of fields which don't have to be subclassed to be supported
STD_TRANSLATION_FIELDS = ('CharField', 'TextField', 'IntegerField',
                          'BooleanField', 'NullBooleanField',)


def create_translation_field(model, field_name, lang):
    """
    Translation field factory.

    Tries to create an object in the form  ``'Translation%s' % cls_name``
    (e.g. ``TranslationForeignKey``, ``TranslationManyToManyField``) based on
    ``model`` and ``field_name``. The class is usually a subclass of
    ``TranslationField`` and is supposed to be implemented in this module. If
    the class is listed in ``STD_TRANSLATION_FIELDS`` then ``TranslationField``
    will be used to instantiate the object. If the class is neither implemented
    nor in ``STD_TRANSLATION_FIELDS`` ``ImproperlyConfigured`` will be raised.
    """
    field = model._meta.get_field(field_name)
    cls_name = field.__class__.__name__
    # No subclass required for text fields
    if cls_name in STD_TRANSLATION_FIELDS:
        return TranslationField(translated_field=field, language=lang)
    # Try to instantiate translation field subclass
    try:
        translation_field = getattr(sys.modules['modeltranslation.fields'],
                                    'Translation%s' % cls_name)
    except AttributeError:
        raise ImproperlyConfigured('%s is not supported by '
                                   'modeltranslation.' % cls_name)
    # Handle related fields
    if cls_name in ('ForeignKey', 'OneToOneField', 'ManyToManyField'):
        to = field.rel.to._meta.object_name
        return translation_field(translated_field=field, language=lang, to=to)
    # TODO: Should never be reached?
    return TranslationField(field, lang)


class TranslationField(Field):
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
        self._post_init(translated_field, language)

    def _post_init(self, translated_field, language):
        """Common init for subclasses of TranslationField."""
        # Store the originally wrapped field for later
        self.translated_field = translated_field
        self.language = language

        # Translation are always optional (for now - maybe add some parameters
        # to the translation options for configuring this)
        self.null = True
        self.blank = True

        # Adjust the name of this field to reflect the language
        self.attname = build_localized_fieldname(self.translated_field.name,
                                                 self.language)
        self.name = self.attname

        # Copy the verbose name and append a language suffix
        # (will show up e.g. in the admin).
        self.verbose_name =\
        build_localized_verbose_name(translated_field.verbose_name, language)

    def pre_save(self, model_instance, add):
        val = super(TranslationField, self).pre_save(model_instance, add)
        if get_default_language() == self.language and not add:
            # Rule is: 3. Assigning a value to a translation field of the
            # default language also updates the original field
            model_instance.__dict__[self.translated_field.name] = val
        return val

    def get_prep_value(self, value):
        if value == '':
            value = None
        return self.translated_field.get_prep_value(value)

    def get_prep_lookup(self, lookup_type, value):
        return self.translated_field.get_prep_lookup(lookup_type, value)

    def to_python(self, value):
        return self.translated_field.to_python(value)

    def get_internal_type(self):
        return self.translated_field.get_internal_type()

    def south_field_triple(self):
        """Returns a suitable description of this field for South."""
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = '%s.%s' % (self.translated_field.__class__.__module__,
                                 self.translated_field.__class__.__name__)
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

    def formfield(self, *args, **kwargs):
        """Preserves the widget of the translated field."""
        trans_formfield = self.translated_field.formfield(*args, **kwargs)
        defaults = {'widget': type(trans_formfield.widget)}
        defaults.update(kwargs)
        return super(TranslationField, self).formfield(*args, **defaults)


class RelatedTranslationField(object):
    """
    Mixin class which handles shared init of a translated relation field.
    """
    def _related_pre_init(self, translated_field, language, *args, **kwargs):
        self.translated_field = translated_field
        self.language = language

        self.field_name = self.translated_field.name
        self.translated_field_name =\
        build_localized_fieldname(self.translated_field.name,
                                  self.language)

        # Dynamically add a related_name to the original field
        translated_field.rel.related_name =\
        '%s%s' % (self.translated_field.model._meta.module_name,
                  self.field_name)

        TranslationField.__init__(self, self.translated_field, self.language,
                                  *args, **kwargs)

    def _related_post_init(self):
        # Dynamically add a related_name to the translation fields
        self.rel.related_name =\
        '%s%s' % (self.translated_field.model._meta.module_name,
                  self.translated_field_name)

        # ForeignKey's init overrides some essential values from
        # TranslationField, they have to be reassigned.
        TranslationField._post_init(self, self.translated_field, self.language)


class TranslationForeignKey(ForeignKey, TranslationField,
                            RelatedTranslationField):
    def __init__(self, translated_field, language, to, to_field=None, *args,
                 **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        ForeignKey.__init__(self, to, to_field, **kwargs)
        self._related_post_init()


class TranslationOneToOneField(OneToOneField, TranslationField,
                               RelatedTranslationField):
    def __init__(self, translated_field, language, to, to_field=None, *args,
                 **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        OneToOneField.__init__(self, to, to_field, **kwargs)
        self._related_post_init()


class TranslationManyToManyField(ManyToManyField, TranslationField,
                                 RelatedTranslationField):
    def __init__(self, translated_field, language, to, *args, **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        ManyToManyField.__init__(self, to, **kwargs)
        self._related_post_init()


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
        loc_field_name = build_localized_fieldname(self.name,
                                                   get_language())
        if hasattr(instance, loc_field_name):
            return getattr(instance, loc_field_name) or\
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
        pass


class ManyToManyTranslationFieldDescriptor(TranslationFieldDescriptor):
    def __init__(self, name, initial_val="", fallback_value=None):
        TranslationFieldDescriptor.__init__(self, name, initial_val="",
                                            fallback_value=None)

    def get_default_instance(self, instance):
        # TODO: Implement
        pass
