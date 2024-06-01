from __future__ import annotations

from functools import partial
from typing import Any, Callable, ClassVar, cast
from collections.abc import Collection, Iterable, Sequence

from django.core.exceptions import ImproperlyConfigured
from django.db.models import (
    Field,
    ForeignKey,
    Manager,
    ManyToManyField,
    Model,
    OneToOneField,
    options,
)
from django.db.models.base import ModelBase
from django.db.models.signals import post_init
from django.utils.functional import cached_property

from modeltranslation import settings as mt_settings
from modeltranslation.fields import (
    NONE,
    LanguageCacheSingleObjectDescriptor,
    TranslatedManyToManyDescriptor,
    TranslatedRelationIdDescriptor,
    TranslationFieldDescriptor,
    TranslationField,
    create_translation_field,
)
from modeltranslation.manager import (
    MultilingualManager,
    MultilingualQuerysetManager,
    append_translated,
    rewrite_lookup_key,
)
from modeltranslation.thread_context import auto_populate_mode
from modeltranslation.utils import build_localized_fieldname, parse_field

# Re-export the decorator for convenience
from modeltranslation.decorators import register

from ._typing import _ListOrTuple

__all__ = [
    "AlreadyRegistered",
    "DescendantRegistered",
    "NotRegistered",
    "TranslationOptions",
    "Translator",
    "register",
    "translator",
]


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

    fields: Sequence[str]

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type:
        attrs["fields"] = set(attrs.get("fields", ()))
        for base in bases:
            if isinstance(base, FieldsAggregationMetaClass):
                attrs["fields"].update(base.fields)
        attrs["fields"] = tuple(attrs["fields"])
        return super().__new__(cls, name, bases, attrs)


class TranslationOptions(metaclass=FieldsAggregationMetaClass):
    """
    Translatable fields are declared by registering a model using
    ``TranslationOptions`` class with appropriate ``fields`` attribute.
    Model-specific fallback values and languages can also be given as class
    attributes.

    Options instances hold info about translatable fields for a model and its
    superclasses. The ``local_fields`` and ``all_fields`` attributes are mappings
    from fields to sets of their translation fields; ``local_fields`` contains
    only those fields that are handled in the model's database table (those
    inherited from abstract superclasses, unless there is a concrete superclass
    in between in the inheritance chain), while ``all_fields`` also includes fields
    inherited from concrete supermodels (giving all translated fields available
    on a model).

    ``related`` attribute inform whether this model is related part of some relation
    with translated model. This model may be not translated itself.
    ``related_fields`` contains names of reverse lookup fields.
    """

    required_languages: ClassVar[_ListOrTuple[str] | dict[str, _ListOrTuple[str]]] = ()

    def __init__(self, model: Model) -> None:
        """
        Create fields dicts without any translation fields.
        """
        self.model = model
        self.registered = False
        self.related = False
        self.local_fields: dict[str, set[TranslationField]] = {f: set() for f in self.fields}
        self.all_fields: dict[str, set[TranslationField]] = {f: set() for f in self.fields}
        self.related_fields: list[str] = []

    def validate(self) -> None:
        """
        Perform options validation.
        """
        # TODO: at the moment only required_languages is validated.
        # Maybe check other options as well?
        if self.required_languages:
            if isinstance(self.required_languages, (tuple, list)):
                self._check_languages(self.required_languages)
            else:
                self._check_languages(self.required_languages.keys(), extra=("default",))
                for fieldnames in self.required_languages.values():
                    if any(f not in self.all_fields for f in fieldnames):
                        raise ImproperlyConfigured(
                            "Fieldname in required_languages which is not in fields option."
                        )

    def _check_languages(
        self,
        languages: Collection[str],
        extra: tuple[str, ...] = (),
    ) -> None:
        correct = list(mt_settings.AVAILABLE_LANGUAGES) + list(extra)
        if any(lang not in correct for lang in languages):
            raise ImproperlyConfigured(
                "Language in required_languages which is not in AVAILABLE_LANGUAGES."
            )

    def update(self, other: TranslationOptions):
        """
        Update with options from a superclass.
        """
        if other.model._meta.abstract:
            self.local_fields.update(other.local_fields)
        self.all_fields.update(other.all_fields)

    def add_translation_field(self, field: str, translation_field):
        """
        Add a new translation field to both fields dicts.
        """
        self.local_fields[field].add(translation_field)
        self.all_fields[field].add(translation_field)

    def get_field_names(self) -> list[str]:
        """
        Return name of all fields that can be used in filtering.
        """
        return list(self.all_fields.keys()) + self.related_fields

    def __str__(self) -> str:
        local = tuple(self.local_fields.keys())
        inherited = tuple(set(self.all_fields.keys()) - set(local))
        return "%s: %s + %s" % (self.__class__.__name__, local, inherited)


class MultilingualOptions(options.Options):
    @cached_property
    def base_manager(self):
        manager = super().base_manager
        patch_manager_class(manager)
        return manager


def add_translation_fields(model: type[Model], opts: TranslationOptions) -> None:
    """
    Monkey patches the original model class to provide additional fields for
    every language.

    Adds newly created translation fields to the given translation options.
    """
    model_empty_values = getattr(opts, "empty_values", NONE)
    for field_name in opts.local_fields.keys():
        field_empty_value = parse_field(model_empty_values, field_name, NONE)
        for lang in mt_settings.AVAILABLE_LANGUAGES:
            # Create a dynamic translation field
            translation_field = create_translation_field(
                model=model, field_name=field_name, lang=lang, empty_value=field_empty_value
            )
            # Construct the name for the localized field
            localized_field_name = build_localized_fieldname(field_name, lang)
            # Check if the model already has a field by that name

            if hasattr(model, localized_field_name):
                # Check if are not dealing with abstract field inherited.
                for cls in model.__mro__:
                    if hasattr(cls, "_meta") and cls.__dict__.get(localized_field_name, None):
                        cls_opts = translator._get_options_for_model(cls)
                        if not cls._meta.abstract or field_name not in cls_opts.local_fields:
                            raise ValueError(
                                "Error adding translation field. Model '%s' already"
                                " contains a field named '%s'."
                                % (model._meta.object_name, localized_field_name)
                            )
            # This approach implements the translation fields as full valid
            # django model fields and therefore adds them via add_to_class
            model.add_to_class(localized_field_name, translation_field)
            opts.add_translation_field(field_name, translation_field)

    # Rebuild information about parents fields. If there are opts.local_fields, field cache would be
    # invalidated (by model._meta.add_field() function). Otherwise, we need to do it manually.
    if len(opts.local_fields) == 0:
        model._meta._expire_cache()
        model._meta.get_fields()


def patch_manager_class(manager):
    if isinstance(manager, MultilingualManager):
        return
    if manager.__class__ is Manager:
        manager.__class__ = MultilingualManager
    else:

        class NewMultilingualManager(
            MultilingualManager, manager.__class__, MultilingualQuerysetManager
        ):
            _old_module = manager.__module__
            _old_class = manager.__class__.__name__

            def deconstruct(self):
                return (
                    False,  # as_manager
                    "%s.%s" % (self._old_module, self._old_class),  # manager_class
                    None,  # qs_class
                    self._constructor_args[0],  # args
                    self._constructor_args[1],  # kwargs
                )

            def __hash__(self):
                return id(self)

            def __eq__(self, other):
                if isinstance(other, NewMultilingualManager):
                    return (
                        self._old_module == other._old_module
                        and self._old_class == other._old_class
                    )
                if hasattr(other, "__module__") and hasattr(other, "__class__"):
                    return (
                        self._old_module == other.__module__
                        and self._old_class == other.__class__.__name__
                    )
                return False

        manager.__class__ = NewMultilingualManager


def add_manager(model: type[Model]) -> None:
    """
    Monkey patches the original model to use MultilingualManager instead of
    default managers (not only ``objects``, but also every manager defined and inherited).

    Custom managers are merged with MultilingualManager.
    """
    if model._meta.abstract:
        return
    # Make all managers local for this model to fix patching parent model managers
    added = set(model._meta.managers) - set(model._meta.local_managers)
    model._meta.local_managers = model._meta.managers  # type: ignore[assignment]

    for current_manager in model._meta.local_managers:
        prev_class = current_manager.__class__
        patch_manager_class(current_manager)
        if current_manager in added:
            # Since default_manager is fetched by order of creation, any manager
            # moved from parent class to child class needs to receive a new creation_counter
            # in order to be ordered after the original local managers
            current_manager._set_creation_counter()
        if model._default_manager.__class__ is prev_class:
            # Normally model._default_manager is a reference to one of model's managers
            # (and would be patched by the way).
            # However, in some rare situations (mostly proxy models)
            # model._default_manager is not the same instance as one of managers, but it
            # share the same class.
            model._default_manager.__class__ = current_manager.__class__

    model._meta.__class__ = MultilingualOptions
    model._meta._expire_cache()


def patch_constructor(model: type[Model]) -> None:
    """
    Monkey patches the original model to rewrite fields names in __init__
    """
    old_init = model.__init__

    def new_init(self, *args, **kwargs):
        self._mt_init = True
        populate_translation_fields(self.__class__, kwargs)
        for key, val in list(kwargs.items()):
            new_key = rewrite_lookup_key(model, key)
            # Old key is intentionally left in case old_init wants to play with it
            kwargs.setdefault(new_key, val)
        old_init(self, *args, **kwargs)

    model.__init__ = new_init


def delete_mt_init(sender: type[Model], instance: Model, **kwargs: Any) -> None:
    if hasattr(instance, "_mt_init"):
        del instance._mt_init


def patch_clean_fields(model: type[Model]):
    """
    Patch clean_fields method to handle different form types submission.
    """
    old_clean_fields = model.clean_fields

    def new_clean_fields(self, exclude: Collection[str] | None = None) -> None:
        if hasattr(self, "_mt_form_pending_clear") and exclude is not None:
            # Some form translation fields has been marked as clearing value.
            # Check if corresponding translated field was also saved (not excluded):
            # - if yes, it seems like form for MT-unaware app. Ignore clearing (left value from
            #   translated field unchanged), as if field was omitted from form
            # - if no, then proceed as normally: clear the field
            for field_name, value in self._mt_form_pending_clear.items():
                field = self._meta.get_field(field_name)
                orig_field_name = field.translated_field.name
                if orig_field_name in exclude:
                    field.save_form_data(self, value, check=False)
            delattr(self, "_mt_form_pending_clear")
        try:
            setattr(self, "_mt_disable", True)
            old_clean_fields(self, exclude)
        finally:
            setattr(self, "_mt_disable", False)

    model.clean_fields = new_clean_fields


def patch_get_deferred_fields(model: type[Model]) -> None:
    """
    Django >= 1.8: patch detecting deferred fields. Crucial for only/defer to work.
    """
    if not hasattr(model, "get_deferred_fields"):
        return
    old_get_deferred_fields = model.get_deferred_fields

    def new_get_deferred_fields(self) -> set[str]:
        sup = old_get_deferred_fields(self)
        if hasattr(self, "_fields_were_deferred"):
            sup.update(self._fields_were_deferred)
        return sup

    model.get_deferred_fields = new_get_deferred_fields


def patch_refresh_from_db(model: type[Model]) -> None:
    """
    Django >= 1.10: patch refreshing deferred fields. Crucial for only/defer to work.
    """
    if not hasattr(model, "refresh_from_db"):
        return
    old_refresh_from_db = model.refresh_from_db

    def new_refresh_from_db(
        self, using: str | None = None, fields: Iterable[str] | None = None
    ) -> None:
        if fields is not None:
            fields = append_translated(self.__class__, fields)
        return old_refresh_from_db(self, using, fields)

    model.refresh_from_db = new_refresh_from_db


def delete_cache_fields(model: type[Model]) -> None:
    opts = model._meta
    cached_attrs = (
        "_field_cache",
        "_field_name_cache",
        "_name_map",
        "fields",
        "concrete_fields",
        "local_concrete_fields",
    )
    for attr in cached_attrs:
        try:
            delattr(opts, attr)
        except AttributeError:
            pass

    if hasattr(model._meta, "_expire_cache"):
        model._meta._expire_cache()


def populate_translation_fields(sender: type[Model], kwargs: Any):
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
    populate = auto_populate_mode()
    if not populate:
        return
    if populate is True:
        # What was meant by ``True`` is now called ``all``.
        populate = "all"

    opts = translator.get_options_for_model(sender)
    for key, val in list(kwargs.items()):
        if key in opts.all_fields:
            if populate == "all":
                # Set the value for every language.
                for translation_field in opts.all_fields[key]:
                    kwargs.setdefault(translation_field.name, val)
            elif populate == "default":
                default = build_localized_fieldname(key, mt_settings.DEFAULT_LANGUAGE)
                kwargs.setdefault(default, val)
            elif populate == "required":
                default = build_localized_fieldname(key, mt_settings.DEFAULT_LANGUAGE)
                if not sender._meta.get_field(key).null:  # type: ignore[union-attr]
                    kwargs.setdefault(default, val)
            else:
                raise AttributeError("Unknown population mode '%s'." % populate)


def patch_related_object_descriptor_caching(ro_descriptor):
    """
    Patch SingleRelatedObjectDescriptor or ReverseSingleRelatedObjectDescriptor to use
    language-aware caching.
    """

    class NewSingleObjectDescriptor(LanguageCacheSingleObjectDescriptor, ro_descriptor.__class__):
        pass

    ro_descriptor.related.get_cache_name = partial(
        NewSingleObjectDescriptor.get_cache_name,
        ro_descriptor,
    )

    ro_descriptor.accessor = ro_descriptor.related.get_accessor_name()
    ro_descriptor.__class__ = NewSingleObjectDescriptor


class Translator:
    """
    A Translator object encapsulates an instance of a translator. Models are
    registered with the Translator using the register() method.
    """

    def __init__(self) -> None:
        # All seen models (model class -> ``TranslationOptions`` instance).
        self._registry: dict[type[Model], TranslationOptions] = {}
        # List of funcs to execute after all imports are done.
        self._lazy_operations: list[Callable[..., Any]] = []

    def register(
        self,
        model_or_iterable: type[Model] | Iterable[type[Model]],
        opts_class: type[TranslationOptions] | None = None,
        **options: Any,
    ) -> None:
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
                        'Model "%s" is already registered for translation' % model.__name__
                    )
                else:
                    descendants = [
                        d.__name__
                        for d in self._registry.keys()
                        if issubclass(d, model) and d != model
                    ]
                    if descendants:
                        raise DescendantRegistered(
                            'Model "%s" cannot be registered after its subclass'
                            ' "%s"' % (model.__name__, descendants[0])
                        )

            # Find inherited fields and create options instance for the model.
            opts = self._get_options_for_model(model, opts_class, **options)

            # If an exception is raised during registration, mark model as not-registered
            try:
                self._register_single_model(model, opts)
            except Exception:
                self._registry[model].registered = False
                raise

    def _register_single_model(self, model: type[Model], opts: TranslationOptions) -> None:
        # Now, when all fields are initialized and inherited, validate configuration.
        opts.validate()

        # Mark the object explicitly as registered -- registry caches
        # options of all models, registered or not.
        opts.registered = True

        # Add translation fields to the model.
        if model._meta.proxy:
            delete_cache_fields(model)
        else:
            add_translation_fields(model, opts)

        # Delete all fields cache for related model (parent and children)
        related = (
            f
            for f in model._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created
        )

        for related_obj in related:
            delete_cache_fields(related_obj.model)

        # Set MultilingualManager
        add_manager(model)

        # Patch __init__ to rewrite fields
        patch_constructor(model)

        # Connect signal for model
        post_init.connect(delete_mt_init, sender=model)

        # Patch clean_fields to verify form field clearing
        patch_clean_fields(model)

        # Patch __metaclass__ and other methods to allow deferring to work
        patch_get_deferred_fields(model)
        patch_refresh_from_db(model)

        # Substitute original field with descriptor
        model_fallback_languages = getattr(opts, "fallback_languages", None)
        model_fallback_values = getattr(opts, "fallback_values", NONE)
        model_fallback_undefined = getattr(opts, "fallback_undefined", NONE)
        for field_name in opts.local_fields.keys():
            field = cast(Field, model._meta.get_field(field_name))
            field_fallback_value = parse_field(model_fallback_values, field_name, NONE)
            field_fallback_undefined = parse_field(model_fallback_undefined, field_name, NONE)
            descriptor = TranslationFieldDescriptor(
                field,
                fallback_languages=model_fallback_languages,
                fallback_value=field_fallback_value,
                fallback_undefined=field_fallback_undefined,
            )
            setattr(model, field_name, descriptor)
            if isinstance(field, (ForeignKey, ManyToManyField)):
                # We need to use a special descriptor so that
                # _id fields on translated ForeignKeys work
                # as expected.
                desc_class = (
                    TranslatedManyToManyDescriptor
                    if isinstance(field, ManyToManyField)
                    else TranslatedRelationIdDescriptor
                )
                desc = desc_class(field_name, model_fallback_languages)
                setattr(model, field.get_attname(), desc)

                # Set related field names on other model
                if not field.remote_field.is_hidden():
                    other_opts = self._get_options_for_model(field.remote_field.model)
                    other_opts.related = True
                    other_opts.related_fields.append(field.related_query_name())
                    # Add manager in case of non-registered model
                    add_manager(field.remote_field.model)

            if isinstance(field, OneToOneField):
                # Fix translated_field caching for SingleRelatedObjectDescriptor
                sro_descriptor = getattr(
                    field.remote_field.model,
                    field.remote_field.get_accessor_name(),
                )
                patch_related_object_descriptor_caching(sro_descriptor)

    def unregister(self, model_or_iterable: type[Model] | Iterable[type[Model]]) -> None:
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
                        ' unregistering its base "%s"' % (desc.__name__, model.__name__)
                    )
                del self._registry[desc]

    def get_registered_models(self, abstract: bool = True) -> list[type[Model]]:
        """
        Returns a list of all registered models, or just concrete
        registered models.
        """
        return [
            model
            for (model, opts) in self._registry.items()
            if opts.registered and (not model._meta.abstract or abstract)
        ]

    def _get_options_for_model(
        self, model: type[Model], opts_class: type[TranslationOptions] | None = None, **options: Any
    ) -> TranslationOptions:
        """
        Returns an instance of translation options with translated fields
        defined for the ``model`` and inherited from superclasses.
        """
        if model not in self._registry:
            # Create a new type for backwards compatibility.

            opts = type(
                "%sTranslationOptions" % model.__name__,
                (opts_class or TranslationOptions,),
                options,
            )(model)

            # Fields for translation may be inherited from abstract
            # superclasses, so we need to look at all parents.
            for base in model.__bases__:
                if not hasattr(base, "_meta"):
                    # Things without _meta aren't functional models, so they're
                    # uninteresting parents.
                    continue
                opts.update(self._get_options_for_model(base))

            # Cache options for all models -- we may want to compute options
            # of registered subclasses of unregistered models.
            self._registry[model] = opts

        return self._registry[model]

    def get_options_for_model(self, model: type[Model]) -> TranslationOptions:
        """
        Thin wrapper around ``_get_options_for_model`` to preserve the
        semantic of throwing exception for models not directly registered.
        """
        opts = self._get_options_for_model(model)
        if not opts.registered and not opts.related:
            raise NotRegistered(
                'The model "%s" is not registered for ' "translation" % model.__name__
            )
        return opts

    def execute_lazy_operations(self) -> None:
        while self._lazy_operations:
            self._lazy_operations.pop(0)(translator=self)

    def lazy_operation(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self._lazy_operations.append(partial(func, *args, **kwargs))


# This global object represents the singleton translator object
translator = Translator()
