# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.six import with_metaclass
from django.db.models import Manager, ForeignKey
from django.db.models.base import ModelBase

from modeltranslation import settings as mt_settings
from modeltranslation.fields import (TranslationFieldDescriptor, TranslatedRelationIdDescriptor,
                                     create_translation_field)
from modeltranslation.manager import MultilingualManager, rewrite_lookup_key
from modeltranslation.utils import build_localized_fieldname


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class DescendantRegistered(Exception):
    pass


class FieldsAggregationMetaClass(type):
    """
    Metaclass to handle custom inheritance of fields between classes.
    """
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = set(attrs.get('fields', ()))
        for base in bases:
            if isinstance(base, FieldsAggregationMetaClass):
                attrs['fields'].update(base.fields)
        attrs['fields'] = tuple(attrs['fields'])
        return super(FieldsAggregationMetaClass, cls).__new__(cls, name, bases, attrs)


class TranslationOptions(with_metaclass(FieldsAggregationMetaClass, object)):
    """
    Translatable fields are declared by registering a model using
    ``TranslationOptions`` class with appropriate ``fields`` attribute.
    Model-specific fallback values and languages can also be given as class
    attributes.

    Options instances hold info about translatable fields for a model and its
    superclasses. The ``local_fields`` and ``fields`` attributes are mappings
    from fields to sets of their translation fields; ``local_fields`` contains
    only those fields that are handled in the model's database table (those
    inherited from abstract superclasses, unless there is a concrete superclass
    in between in the inheritance chain), while ``fields`` also includes fields
    inherited from concrete supermodels (giving all translated fields available
    on a model).

    ``related`` attribute inform whether this model is related part of some relation
    with translated model. This model may be not translated itself.
    ``related_fields`` contains names of reverse lookup fields.
    """

    def __init__(self, model):
        """
        Create fields dicts without any translation fields.
        """
        self.model = model
        self.registered = False
        self.related = False
        self.local_fields = dict((f, set()) for f in self.fields)
        self.fields = dict((f, set()) for f in self.fields)
        self.related_fields = []

    def update(self, other):
        """
        Update with options from a superclass.
        """
        if other.model._meta.abstract:
            self.local_fields.update(other.local_fields)
        self.fields.update(other.fields)

    def add_translation_field(self, field, translation_field):
        """
        Add a new translation field to both fields dicts.
        """
        self.local_fields[field].add(translation_field)
        self.fields[field].add(translation_field)

    def get_field_names(self):
        """
        Return name of all fields that can be used in filtering.
        """
        return list(self.fields.keys()) + self.related_fields

    def __str__(self):
        local = tuple(self.local_fields.keys())
        inherited = tuple(set(self.fields.keys()) - set(local))
        return '%s: %s + %s' % (self.__class__.__name__, local, inherited)


def add_translation_fields(model, opts):
    """
    Monkey patches the original model class to provide additional fields for
    every language.

    Adds newly created translation fields to the given translation options.
    """
    for field_name in opts.local_fields.keys():
        for l in settings.LANGUAGES:
            # Create a dynamic translation field
            translation_field = create_translation_field(
                model=model, field_name=field_name, lang=l[0])
            # Construct the name for the localized field
            localized_field_name = build_localized_fieldname(field_name, l[0])
            # Check if the model already has a field by that name
            if hasattr(model, localized_field_name):
                raise ValueError(
                    "Error adding translation field. Model '%s' already contains a field named"
                    "'%s'." % (model._meta.object_name, localized_field_name))
            # This approach implements the translation fields as full valid
            # django model fields and therefore adds them via add_to_class
            model.add_to_class(localized_field_name, translation_field)
            opts.add_translation_field(field_name, translation_field)


def add_manager(model):
    """
    Monkey patches the original model to use MultilingualManager instead of
    default manager (``objects``).

    If model has a custom manager, then merge it with MultilingualManager.
    """
    if not hasattr(model, 'objects'):
        return
    current_manager = model.objects
    if isinstance(current_manager, MultilingualManager):
        return
    if current_manager.__class__ is Manager:
        current_manager.__class__ = MultilingualManager
    else:
        class NewMultilingualManager(MultilingualManager, current_manager.__class__):
            pass
        current_manager.__class__ = NewMultilingualManager


def patch_constructor(model):
    """
    Monkey patches the original model to rewrite fields names in __init__
    """
    old_init = model.__init__

    def new_init(self, *args, **kwargs):
        self._mt_init = True
        if not self._deferred:
            populate_translation_fields(self.__class__, kwargs)
            for key, val in list(kwargs.items()):
                new_key = rewrite_lookup_key(model, key)
                # Old key is intentionally left in case old_init wants to play with it
                kwargs.setdefault(new_key, val)
        old_init(self, *args, **kwargs)
        del self._mt_init
    model.__init__ = new_init


def patch_metaclass(model):
    """
    Monkey patches original model metaclass to exclude translated fields on deferred subclasses.
    """
    old_mcs = model.__class__

    class translation_deferred_mcs(old_mcs):
        """
        This metaclass is essential for deferred subclasses (obtained via only/defer) to work.

        When deferred subclass is created, some translated fields descriptors could be overridden
        by DeferredAttribute - which would cause translation retrieval to fail.
        Prevent this from happening with deleting those attributes from class being created.
        This metaclass would be called from django.db.models.query_utils.deferred_class_factory
        """
        def __new__(cls, name, bases, attrs):
            if attrs.get('_deferred', False):
                opts = translator.get_options_for_model(model)
                for field_name in opts.fields.keys():
                    attrs.pop(field_name, None)
            return super(translation_deferred_mcs, cls).__new__(cls, name, bases, attrs)
    # Assign to __metaclass__ wouldn't work, since metaclass search algorithm check for __class__.
    # http://docs.python.org/2/reference/datamodel.html#__metaclass__
    model.__class__ = translation_deferred_mcs


def delete_cache_fields(model):
    opts = model._meta
    cached_attrs = ('_field_cache', '_field_name_cache', '_name_map', 'fields', 'concrete_fields',
                    'local_concrete_fields')
    for attr in cached_attrs:
        try:
            delattr(opts, attr)
        except AttributeError:
            pass


def populate_translation_fields(sender, kwargs):
    """
    When models are created or loaded from fixtures, replicates values
    provided for translatable fields to some / all empty translation fields,
    according to the current population mode.

    Population is performed only on keys (field names) present in kwargs.
    Nothing is returned, but passed kwargs dictionary is altered.

    With ``mode`` set to:
    -- ``all``: fills all translation fields, skipping just those for
       which a translated value is also provided;
    -- ``default``: fills only the default translation (unless it is
       additionally provided);
    -- ``required``: like ``default``, but only if the original field is
       non-nullable;

    At least the ``required`` mode should be used when loading untranslated
    fixtures to keep the database consistent (note that Django management
    commands are normally forced to run with hardcoded ``en-us`` language
    active). The ``default`` mode is useful if you need to ensure fallback
    values are available, and ``all`` if you need to have all translations
    defined (for example to make lookups / filtering without resorting to
    query fallbacks).
    """
    populate = mt_settings.AUTO_POPULATE
    if not populate:
        return
    if populate is True:
        # What was meant by ``True`` is now called ``all``.
        populate = 'all'

    opts = translator.get_options_for_model(sender)
    for key, val in list(kwargs.items()):
        if key in opts.fields:
            if populate == 'all':
                # Set the value for every language.
                for translation_field in opts.fields[key]:
                    kwargs.setdefault(translation_field.name, val)
            elif populate == 'default':
                default = build_localized_fieldname(key, mt_settings.DEFAULT_LANGUAGE)
                kwargs.setdefault(default, val)
            elif populate == 'required':
                default = build_localized_fieldname(key, mt_settings.DEFAULT_LANGUAGE)
                if not sender._meta.get_field(key).null:
                    kwargs.setdefault(default, val)
            else:
                raise AttributeError("Unknown population mode '%s'." % populate)


class Translator(object):
    """
    A Translator object encapsulates an instance of a translator. Models are
    registered with the Translator using the register() method.
    """
    def __init__(self):
        # All seen models (model class -> ``TranslationOptions`` instance).
        self._registry = {}

    def register(self, model_or_iterable, opts_class=None, **options):
        """
        Registers the given model(s) with the given translation options.

        The model(s) should be Model classes, not instances.

        Fields declared for translation on a base class are inherited by
        subclasses. If the model or one of its subclasses is already
        registered for translation, this will raise an exception.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        for model in model_or_iterable:
            # Ensure that a base is not registered after a subclass (_registry
            # is closed with respect to taking bases, so we can just check if
            # we've seen the model).
            if model in self._registry:
                if self._registry[model].registered:
                    raise AlreadyRegistered(
                        'Model "%s" is already registered for translation' %
                        model.__name__)
                else:
                    descendants = [d.__name__ for d in self._registry.keys()
                                   if issubclass(d, model) and d != model]
                    raise DescendantRegistered(
                        'Model "%s" cannot be registered after its subclass'
                        ' "%s"' % (model.__name__, descendants[0]))

            # Find inherited fields and create options instance for the model.
            opts = self._get_options_for_model(model, opts_class, **options)

            # Mark the object explicitly as registered -- registry caches
            # options of all models, registered or not.
            opts.registered = True

            # Add translation fields to the model.
            add_translation_fields(model, opts)

            # Delete all fields cache for related model (parent and children)
            for related_obj in model._meta.get_all_related_objects():
                delete_cache_fields(related_obj.model)

            # Set MultilingualManager
            add_manager(model)

            # Patch __init__ to rewrite fields
            patch_constructor(model)

            # Patch __metaclass__ to allow deferring to work
            patch_metaclass(model)

            # Substitute original field with descriptor
            model_fallback_values = getattr(opts, 'fallback_values', None)
            model_fallback_languages = getattr(opts, 'fallback_languages', None)
            for field_name in opts.local_fields.keys():
                if model_fallback_values is None:
                    field_fallback_value = None
                elif isinstance(model_fallback_values, dict):
                    field_fallback_value = model_fallback_values.get(field_name, None)
                else:
                    field_fallback_value = model_fallback_values
                field = model._meta.get_field(field_name)
                descriptor = TranslationFieldDescriptor(
                    field,
                    fallback_value=field_fallback_value,
                    fallback_languages=model_fallback_languages)
                setattr(model, field_name, descriptor)
                if isinstance(field, ForeignKey):
                    # We need to use a special descriptor so that
                    # _id fields on translated ForeignKeys work
                    # as expected.
                    desc = TranslatedRelationIdDescriptor(field_name, model_fallback_languages)
                    setattr(model, field.get_attname(), desc)

                    # Set related field names on other model
                    if not field.rel.is_hidden():
                        other_opts = self._get_options_for_model(field.rel.to)
                        other_opts.related = True
                        other_opts.related_fields.append(field.related_query_name())
                        add_manager(field.rel.to)  # Add manager in case of non-registered model

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't registered, this will raise NotRegistered. If one of
        its subclasses is registered, DescendantRegistered will be raised.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            # Check if the model is actually registered (``get_options_for_model``
            # throws an exception if it's not).
            self.get_options_for_model(model)
            # Invalidate all submodels options and forget about
            # the model itself.
            for desc, desc_opts in list(self._registry.items()):
                if not issubclass(desc, model):
                    continue
                if model != desc and desc_opts.registered:
                    # Allowing to unregister a base would necessitate
                    # repatching all submodels.
                    raise DescendantRegistered(
                        'You need to unregister descendant "%s" before'
                        ' unregistering its base "%s"' %
                        (desc.__name__, model.__name__))
                del self._registry[desc]

    def get_registered_models(self, abstract=True):
        """
        Returns a list of all registered models, or just concrete
        registered models.
        """
        return [model for (model, opts) in self._registry.items()
                if opts.registered and (not model._meta.abstract or abstract)]

    def _get_options_for_model(self, model, opts_class=None, **options):
        """
        Returns an instance of translation options with translated fields
        defined for the ``model`` and inherited from superclasses.
        """
        if model not in self._registry:
            # Create a new type for backwards compatibility.
            opts = type("%sTranslationOptions" % model.__name__,
                        (opts_class or TranslationOptions,), options)(model)

            # Fields for translation may be inherited from abstract
            # superclasses, so we need to look at all parents.
            for base in model.__bases__:
                if not hasattr(base, '_meta'):
                    # Things without _meta aren't functional models, so they're
                    # uninteresting parents.
                    continue
                opts.update(self._get_options_for_model(base))

            # Cache options for all models -- we may want to compute options
            # of registered subclasses of unregistered models.
            self._registry[model] = opts

        return self._registry[model]

    def get_options_for_model(self, model):
        """
        Thin wrapper around ``_get_options_for_model`` to preserve the
        semantic of throwing exception for models not directly registered.
        """
        opts = self._get_options_for_model(model)
        if not opts.registered and not opts.related:
            raise NotRegistered('The model "%s" is not registered for '
                                'translation' % model.__name__)
        return opts


# This global object represents the singleton translator object
translator = Translator()
