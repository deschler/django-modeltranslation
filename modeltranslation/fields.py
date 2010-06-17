# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models.fields import Field, CharField
from django.db.models.fields.related import (ForeignKey, OneToOneField,
                                             ManyToManyField)

from modeltranslation.utils import (get_default_language,
                                    build_localized_fieldname,
                                    build_localized_verbose_name)


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

        # Common init
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
        build_localized_verbose_name(translated_field.verbose_name,
                                     language)

    def pre_save(self, model_instance, add):
        val = super(TranslationField, self).pre_save(model_instance, add)
        if get_default_language() == self.language and not add:
            # Rule is: 3. Assigning a value to a translation field of the
            # default language also updates the original field
            model_instance.__dict__[self.translated_field.name] = val
        return val

    def get_db_prep_value(self, value, connection, prepared=False):
        if value == "":
            return None
        else:
            return value

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
        self.translated_field_name = \
            build_localized_fieldname(self.translated_field.name,
                                      self.language)

        # Dynamically add a related_name to the original field
        translated_field.rel.related_name = \
            '%s%s' % (self.translated_field.model._meta.module_name,
                      self.field_name)

        TranslationField.__init__(self, self.translated_field, self.language,
                                  *args, **kwargs)

    def _related_post_init(self):
        # Dynamically add a related_name to the translation fields
        self.rel.related_name = \
            '%s%s' % (self.translated_field.model._meta.module_name,
                      self.translated_field_name)

        # ForeignKey's init overrides some essential values from
        # TranslationField, they have to be reassigned.
        TranslationField._post_init(self, self.translated_field, self.language)


class ForeignKeyTranslationField(ForeignKey, TranslationField,
                                 RelatedTranslationField):
    def __init__(self, translated_field, language, to, to_field=None, *args,
                 **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        ForeignKey.__init__(self, to, to_field, **kwargs)
        self._related_post_init()


class OneToOneTranslationField(OneToOneField, TranslationField,
                               RelatedTranslationField):
    def __init__(self, translated_field, language, to, to_field=None, *args,
                 **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        OneToOneField.__init__(self, to, to_field, **kwargs)
        self._related_post_init()


class ManyToManyTranslationField(ManyToManyField, TranslationField,
                                 RelatedTranslationField):
    def __init__(self, translated_field, language, to, *args, **kwargs):
        self._related_pre_init(translated_field, language, *args, **kwargs)
        ManyToManyField.__init__(self, to, **kwargs)
        self._related_post_init()
