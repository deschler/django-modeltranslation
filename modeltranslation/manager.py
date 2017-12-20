# -*- coding: utf-8 -*-
"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""
import itertools

import django
try:
    from django.contrib.admin.utils import get_model_from_relation
except ImportError:
    from django.contrib.admin.util import get_model_from_relation

from django.db import models
from django.db.models import FieldDoesNotExist
try:
    from django.db.models.fields.related import RelatedObject
    from django.db.models.fields.related import RelatedField
    NEW_META_API = False
except ImportError:
    NEW_META_API = True

try:
    from django.db.models.query import ValuesQuerySet
    from django.db.models.sql.where import Constraint
    NEW_RELATED_API = False
except ImportError:
    from django.db.models.query import ValuesIterable
    NEW_RELATED_API = True  # Django 1.9

from django.utils.six import moves
from django.utils.tree import Node
try:
    from django.db.models.lookups import Lookup
    from django.db.models.sql.datastructures import Col
    NEW_LOOKUPS = True  # Django 1.7, 1.8
except ImportError:
    NEW_LOOKUPS = False

from modeltranslation import settings
from modeltranslation.fields import TranslationField
from modeltranslation.utils import (build_localized_fieldname, get_language,
                                    auto_populate, resolution_order)


def get_translatable_fields_for_model(model):
    from modeltranslation.translator import NotRegistered, translator
    try:
        return translator.get_options_for_model(model).get_field_names()
    except NotRegistered:
        return None


def rewrite_lookup_key(model, lookup_key):
    try:
        pieces = lookup_key.split('__', 1)
        original_key = pieces[0]

        translatable_fields = get_translatable_fields_for_model(model)
        if translatable_fields is not None:
            # If we are doing a lookup on a translatable field,
            # we want to rewrite it to the actual field name
            # For example, we want to rewrite "name__startswith" to "name_fr__startswith"
            if pieces[0] in translatable_fields:
                pieces[0] = build_localized_fieldname(pieces[0], get_language())

        if len(pieces) > 1:
            # Check if we are doing a lookup to a related trans model
            fields_to_trans_models = get_fields_to_translatable_models(model)
            # Check ``original key``, as pieces[0] may have been already rewritten.
            if original_key in fields_to_trans_models:
                transmodel = fields_to_trans_models[original_key]
                pieces[1] = rewrite_lookup_key(transmodel, pieces[1])
        return '__'.join(pieces)
    except AttributeError:
        return lookup_key


def append_fallback(model, fields):
    """
    If translated field is encountered, add also all its fallback fields.
    Returns tuple: (set_of_new_fields_to_use, set_of_translated_field_names)
    """
    fields = set(fields)
    trans = set()
    from modeltranslation.translator import translator
    opts = translator.get_options_for_model(model)
    for key, _ in opts.fields.items():
        if key in fields:
            langs = resolution_order(get_language(), getattr(model, key).fallback_languages)
            fields = fields.union(build_localized_fieldname(key, lang) for lang in langs)
            fields.remove(key)
            trans.add(key)
    return fields, trans


def append_translated(model, fields):
    "If translated field is encountered, add also all its translation fields."
    fields = set(fields)
    from modeltranslation.translator import translator
    opts = translator.get_options_for_model(model)
    for key, translated in opts.fields.items():
        if key in fields:
            fields = fields.union(f.name for f in translated)
    return fields


def append_lookup_key(model, lookup_key):
    "Transform spanned__lookup__key into all possible translation versions, on all levels"
    pieces = lookup_key.split('__', 1)

    fields = append_translated(model, (pieces[0],))

    if len(pieces) > 1:
        # Check if we are doing a lookup to a related trans model
        fields_to_trans_models = get_fields_to_translatable_models(model)
        if pieces[0] in fields_to_trans_models:
            transmodel = fields_to_trans_models[pieces[0]]
            rest = append_lookup_key(transmodel, pieces[1])
            fields = set('__'.join(pr) for pr in itertools.product(fields, rest))
        else:
            fields = set('%s__%s' % (f, pieces[1]) for f in fields)
    return fields


def append_lookup_keys(model, fields):
    new_fields = []
    for field in fields:
        try:
            new_field = append_lookup_key(model, field)
        except AttributeError:
            new_field = (field,)
        new_fields.append(new_field)

    return moves.reduce(set.union, new_fields, set())


def rewrite_order_lookup_key(model, lookup_key):
    try:
        if lookup_key.startswith('-'):
            return '-' + rewrite_lookup_key(model, lookup_key[1:])
        else:
            return rewrite_lookup_key(model, lookup_key)
    except AttributeError:
        return lookup_key

_F2TM_CACHE = {}


def get_fields_to_translatable_models(model):
    if model in _F2TM_CACHE:
        return _F2TM_CACHE[model]

    results = []
    if NEW_META_API:
        for f in model._meta.get_fields():
            if f.is_relation and f.related_model:
                # The new get_field() will find GenericForeignKey relations.
                # In that case the 'related_model' attribute is set to None
                # so it is necessary to check for this value before trying to
                # get translatable fields.
                related_model = get_model_from_relation(f)
                if get_translatable_fields_for_model(related_model) is not None:
                    results.append((f.name, related_model))
    else:
        for field_name in model._meta.get_all_field_names():
            field_object, modelclass, direct, m2m = model._meta.get_field_by_name(field_name)
            # Direct relationship
            if direct and isinstance(field_object, RelatedField):
                if get_translatable_fields_for_model(field_object.related.parent_model) is not None:
                    results.append((field_name, field_object.related.parent_model))
            # Reverse relationship
            if isinstance(field_object, RelatedObject):
                if get_translatable_fields_for_model(field_object.model) is not None:
                    results.append((field_name, field_object.model))
    _F2TM_CACHE[model] = dict(results)
    return _F2TM_CACHE[model]

_C2F_CACHE = {}


def get_field_by_colum_name(model, col):
    # First, try field with the column name
    try:
        field = model._meta.get_field(col)
        if field.column == col:
            return field
    except FieldDoesNotExist:
        pass
    field = _C2F_CACHE.get((model, col), None)
    if field:
        return field
    # D'oh, need to search through all of them.
    for field in model._meta.fields:
        if field.column == col:
            _C2F_CACHE[(model, col)] = field
            return field
    assert False, "No field found for column %s" % col


class MultilingualQuerySet(models.query.QuerySet):
    def __init__(self, *args, **kwargs):
        super(MultilingualQuerySet, self).__init__(*args, **kwargs)
        self._post_init()

    def _post_init(self):
        self._rewrite = True
        self._populate = None
        if self.model and (not self.query.order_by):
            if self.model._meta.ordering:
                # If we have default ordering specified on the model, set it now so that
                # it can be rewritten. Otherwise sql.compiler will grab it directly from _meta
                ordering = []
                for key in self.model._meta.ordering:
                    ordering.append(rewrite_order_lookup_key(self.model, key))
                self.query.add_ordering(*ordering)

    def __reduce__(self):
        return multilingual_queryset_factory, (self.__class__.__bases__[0],), self.__getstate__()

    # This method was not present in django-linguo
    if NEW_RELATED_API:
        def _clone(self, klass=None, **kwargs):
            kwargs.setdefault('_rewrite', self._rewrite)
            kwargs.setdefault('_populate', self._populate)
            if hasattr(self, 'translation_fields'):
                kwargs.setdefault('translation_fields', self.translation_fields)
            if hasattr(self, 'fields_to_del'):
                kwargs.setdefault('fields_to_del', self.fields_to_del)
            if hasattr(self, 'original_fields'):
                kwargs.setdefault('original_fields', self.original_fields)
            return super(MultilingualQuerySet, self)._clone(**kwargs)
    else:
        def _clone(self, klass=None, *args, **kwargs):
            if klass is not None and not issubclass(klass, MultilingualQuerySet):
                class NewClass(klass, MultilingualQuerySet):
                    pass
                NewClass.__name__ = 'Multilingual%s' % klass.__name__
                klass = NewClass
            kwargs.setdefault('_rewrite', self._rewrite)
            kwargs.setdefault('_populate', self._populate)
            return super(MultilingualQuerySet, self)._clone(klass, *args, **kwargs)

    # This method was not present in django-linguo
    def rewrite(self, mode=True):
        return self._clone(_rewrite=mode)

    # This method was not present in django-linguo
    def populate(self, mode='all'):
        """
        Overrides the translation fields population mode for this query set.
        """
        return self._clone(_populate=mode)

    def _rewrite_applied_operations(self):
        """
        Rewrite fields in already applied filters/ordering.
        Useful when converting any QuerySet into MultilingualQuerySet.
        """
        self._rewrite_where(self.query.where)
        if not NEW_RELATED_API:
            self._rewrite_where(self.query.having)
        self._rewrite_order()
        self._rewrite_select_related()

    # This method was not present in django-linguo
    def select_related(self, *fields, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).select_related(*fields, **kwargs)
        # TO CONSIDER: whether this should rewrite only current language, or all languages?
        # fk -> [fk, fk_en] (with en=active) VS fk -> [fk, fk_en, fk_de, fk_fr ...] (for all langs)

        # new_args = append_lookup_keys(self.model, fields)
        new_args = []
        for key in fields:
            if key is None:
                new_args.append(None)
            else:
                new_args.append(rewrite_lookup_key(self.model, key))
        return super(MultilingualQuerySet, self).select_related(*new_args, **kwargs)

    # This method was not present in django-linguo
    def _rewrite_col(self, col):
        """Django >= 1.7 column name rewriting"""
        if isinstance(col, Col):
            new_name = rewrite_lookup_key(self.model, col.target.name)
            if col.target.name != new_name:
                new_field = self.model._meta.get_field(new_name)
                if col.target is col.source:
                    col.source = new_field
                col.target = new_field
        elif hasattr(col, 'col'):
            self._rewrite_col(col.col)
        elif hasattr(col, 'lhs'):
            self._rewrite_col(col.lhs)

    def _rewrite_where(self, q):
        """
        Rewrite field names inside WHERE tree.
        """
        if not NEW_LOOKUPS and isinstance(q, tuple) and isinstance(q[0], Constraint):
            c = q[0]
            if c.field is None:
                c.field = get_field_by_colum_name(self.model, c.col)
            new_name = rewrite_lookup_key(self.model, c.field.name)
            if c.field.name != new_name:
                c.field = self.model._meta.get_field(new_name)
                c.col = c.field.column
        elif NEW_LOOKUPS and isinstance(q, Lookup):
            self._rewrite_col(q.lhs)
        if isinstance(q, Node):
            for child in q.children:
                self._rewrite_where(child)

    def _rewrite_order(self):
        self.query.order_by = [rewrite_order_lookup_key(self.model, field_name)
                               for field_name in self.query.order_by]

    def _rewrite_select_related(self):
        if isinstance(self.query.select_related, dict):
            new = {}
            for field_name, value in self.query.select_related.items():
                new[rewrite_order_lookup_key(self.model, field_name)] = value
            self.query.select_related = new

    # This method was not present in django-linguo
    def _rewrite_q(self, q):
        """Rewrite field names inside Q call."""
        if isinstance(q, tuple) and len(q) == 2:
            return rewrite_lookup_key(self.model, q[0]), q[1]
        if isinstance(q, Node):
            q.children = list(map(self._rewrite_q, q.children))
        return q

    # This method was not present in django-linguo
    def _rewrite_f(self, q):
        """
        Rewrite field names inside F call.
        """
        if isinstance(q, models.F):
            q.name = rewrite_lookup_key(self.model, q.name)
            return q
        if isinstance(q, Node):
            q.children = list(map(self._rewrite_f, q.children))
        # Django >= 1.8
        if hasattr(q, 'lhs'):
            q.lhs = self._rewrite_f(q.lhs)
        if hasattr(q, 'rhs'):
            q.rhs = self._rewrite_f(q.rhs)
        return q

    def _filter_or_exclude(self, negate, *args, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)
        args = map(self._rewrite_q, args)
        for key, val in list(kwargs.items()):
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = self._rewrite_f(val)
        return super(MultilingualQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)

    def _get_original_fields(self):
        source = (self.model._meta.concrete_fields if hasattr(self.model._meta, 'concrete_fields')
                  else self.model._meta.fields)
        return [f.attname for f in source if not isinstance(f, TranslationField)]

    def order_by(self, *field_names):
        """
        Change translatable field names in an ``order_by`` argument
        to translation fields for the current language.
        """
        if not self._rewrite:
            return super(MultilingualQuerySet, self).order_by(*field_names)
        new_args = []
        for key in field_names:
            new_args.append(rewrite_order_lookup_key(self.model, key))
        return super(MultilingualQuerySet, self).order_by(*new_args)

    def update(self, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).update(**kwargs)
        for key, val in list(kwargs.items()):
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = self._rewrite_f(val)
        return super(MultilingualQuerySet, self).update(**kwargs)
    update.alters_data = True

    # This method was not present in django-linguo
    @property
    def _populate_mode(self):
        # Populate can be set using a global setting or a manager method.
        if self._populate is None:
            return settings.AUTO_POPULATE
        return self._populate

    # This method was not present in django-linguo
    def create(self, **kwargs):
        """
        Allows to override population mode with a ``populate`` method.
        """
        with auto_populate(self._populate_mode):
            return super(MultilingualQuerySet, self).create(**kwargs)

    # This method was not present in django-linguo
    def get_or_create(self, **kwargs):
        """
        Allows to override population mode with a ``populate`` method.
        """
        with auto_populate(self._populate_mode):
            return super(MultilingualQuerySet, self).get_or_create(**kwargs)

    # This method was not present in django-linguo
    def defer(self, *fields):
        fields = append_lookup_keys(self.model, fields)
        return super(MultilingualQuerySet, self).defer(*fields)

    # This method was not present in django-linguo
    def only(self, *fields):
        fields = append_lookup_keys(self.model, fields)
        return super(MultilingualQuerySet, self).only(*fields)

    # This method was not present in django-linguo
    def raw_values(self, *fields):
        return super(MultilingualQuerySet, self).values(*fields)

    def _values(self, *original, **kwargs):
        if not kwargs.get('prepare', False):
            return super(MultilingualQuerySet, self)._values(*original)
        new_fields, translation_fields = append_fallback(self.model, original)
        clone = super(MultilingualQuerySet, self)._values(*list(new_fields))
        clone.original_fields = tuple(original)
        clone.translation_fields = translation_fields
        clone.fields_to_del = new_fields - set(original)
        return clone

    # This method was not present in django-linguo
    def values(self, *fields):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).values(*fields)
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()
        if NEW_RELATED_API:
            clone = self._values(*fields, prepare=True)
            clone._iterable_class = FallbackValuesIterable
            return clone
        else:
            return self._clone(klass=FallbackValuesQuerySet, setup=True, _fields=fields)

    # This method was not present in django-linguo
    def values_list(self, *fields, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).values_list(*fields, **kwargs)
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s' % (list(kwargs),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is "
                            "called with more than one field.")
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()
        if NEW_RELATED_API:
            clone = self._values(*fields, prepare=True)
            clone._iterable_class = (FallbackFlatValuesListIterable if flat
                                     else FallbackValuesListIterable)
            return clone
        else:
            return self._clone(klass=FallbackValuesListQuerySet, setup=True, flat=flat,
                               _fields=fields)

    # This method was not present in django-linguo
    def dates(self, field_name, *args, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).dates(field_name, *args, **kwargs)
        new_key = rewrite_lookup_key(self.model, field_name)
        return super(MultilingualQuerySet, self).dates(new_key, *args, **kwargs)


if NEW_RELATED_API:
    class FallbackValuesIterable(ValuesIterable):
        class X(object):
            # This stupid class is needed as object use __slots__ and has no __dict__.
            pass

        def __iter__(self):
            instance = self.X()
            for row in super(FallbackValuesIterable, self).__iter__():
                instance.__dict__.update(row)
                for key in self.queryset.translation_fields:
                    row[key] = getattr(self.queryset.model, key).__get__(instance, None)
                for key in self.queryset.fields_to_del:
                    del row[key]
                yield row

    class FallbackValuesListIterable(FallbackValuesIterable):
        def __iter__(self):
            fields = self.queryset.original_fields
            fields += tuple(f for f in self.queryset.query.annotation_select if f not in fields)
            for row in super(FallbackValuesListIterable, self).__iter__():
                yield tuple(row[f] for f in fields)

    class FallbackFlatValuesListIterable(FallbackValuesListIterable):
        def __iter__(self):
            for row in super(FallbackFlatValuesListIterable, self).__iter__():
                yield row[0]

else:
    class FallbackValuesQuerySet(ValuesQuerySet, MultilingualQuerySet):
        def _setup_query(self):
            original = self._fields
            new_fields, self.translation_fields = append_fallback(self.model, original)
            self._fields = list(new_fields)
            self.fields_to_del = new_fields - set(original)
            super(FallbackValuesQuerySet, self)._setup_query()

        class X(object):
            # This stupid class is needed as object use __slots__ and has no __dict__.
            pass

        def iterator(self):
            instance = self.X()
            for row in super(FallbackValuesQuerySet, self).iterator():
                instance.__dict__.update(row)
                for key in self.translation_fields:
                    row[key] = getattr(self.model, key).__get__(instance, None)
                for key in self.fields_to_del:
                    del row[key]
                yield row

        def _clone(self, klass=None, setup=False, **kwargs):
            c = super(FallbackValuesQuerySet, self)._clone(klass, **kwargs)
            c.fields_to_del = self.fields_to_del
            c.translation_fields = self.translation_fields
            if setup and hasattr(c, '_setup_query'):
                c._setup_query()
            return c

    class FallbackValuesListQuerySet(FallbackValuesQuerySet):
        def iterator(self):
            fields = self.original_fields
            if hasattr(self, 'aggregate_names'):
                # Django <1.8
                fields += tuple(f for f in self.aggregate_names if f not in fields)
            if hasattr(self, 'annotation_names'):
                # Django >=1.8
                fields += tuple(f for f in self.annotation_names if f not in fields)
            for row in super(FallbackValuesListQuerySet, self).iterator():
                if self.flat and len(self.original_fields) == 1:
                    yield row[fields[0]]
                else:
                    yield tuple(row[f] for f in fields)

        def _setup_query(self):
            self.original_fields = tuple(self._fields)
            super(FallbackValuesListQuerySet, self)._setup_query()

        def _clone(self, *args, **kwargs):
            clone = super(FallbackValuesListQuerySet, self)._clone(*args, **kwargs)
            clone.original_fields = self.original_fields
            if not hasattr(clone, "flat"):
                # Only assign flat if the clone didn't already get it from kwargs
                clone.flat = self.flat
            return clone


def multilingual_queryset_factory(old_cls, instantiate=True):
    if old_cls == models.query.QuerySet:
        NewClass = MultilingualQuerySet
    else:
        class NewClass(old_cls, MultilingualQuerySet):
            pass
        NewClass.__name__ = 'Multilingual%s' % old_cls.__name__
    return NewClass() if instantiate else NewClass


class MultilingualQuerysetManager(models.Manager):
    """
    This class gets hooked in MRO just before plain Manager, so that every call to
    get_queryset returns MultilingualQuerySet.
    """
    def get_queryset(self):
        qs = super(MultilingualQuerysetManager, self).get_queryset()
        return self._patch_queryset(qs)

    def _patch_queryset(self, qs):
        qs.__class__ = multilingual_queryset_factory(qs.__class__, instantiate=False)
        qs._post_init()
        qs._rewrite_applied_operations()
        return qs


class MultilingualManager(MultilingualQuerysetManager):
    if django.VERSION < (1, 10):
        use_for_related_fields = True

    def rewrite(self, *args, **kwargs):
        return self.get_queryset().rewrite(*args, **kwargs)

    def populate(self, *args, **kwargs):
        return self.get_queryset().populate(*args, **kwargs)

    def raw_values(self, *args, **kwargs):
        return self.get_queryset().raw_values(*args, **kwargs)

    def get_queryset(self):
        """
        This method is repeated because some managers that don't use super() or alter queryset class
        may return queryset that is not subclass of MultilingualQuerySet.
        """
        qs = super(MultilingualManager, self).get_queryset()
        if isinstance(qs, MultilingualQuerySet):
            # Is already patched by MultilingualQuerysetManager - in most of the cases
            # when custom managers use super() properly in get_queryset.
            return qs
        return self._patch_queryset(qs)
