# -*- coding: utf-8 -*-
"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""
import itertools

from django.db import models
from django.db.models import FieldDoesNotExist
from django.db.models.fields.related import RelatedField, RelatedObject
from django.db.models.sql.where import Constraint
from django.utils.six import moves
from django.utils.tree import Node
try:
    from django.db.models.lookups import Lookup
    from django.db.models.sql.datastructures import Col
    NEW_LOOKUPS = True
except ImportError:
    NEW_LOOKUPS = False

from modeltranslation import settings
from modeltranslation.fields import TranslationField
from modeltranslation.utils import (build_localized_fieldname, get_language,
                                    auto_populate)


def get_translatable_fields_for_model(model):
    from modeltranslation.translator import NotRegistered, translator
    try:
        return translator.get_options_for_model(model).get_field_names()
    except NotRegistered:
        return None


def rewrite_lookup_key(model, lookup_key):
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
    return moves.reduce(set.union, (append_lookup_key(model, field) for field in fields), set())


def rewrite_order_lookup_key(model, lookup_key):
    if lookup_key.startswith('-'):
        return '-' + rewrite_lookup_key(model, lookup_key[1:])
    else:
        return rewrite_lookup_key(model, lookup_key)

_F2TM_CACHE = {}


def get_fields_to_translatable_models(model):
    if model not in _F2TM_CACHE:
        results = []
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

    # This method was not present in django-linguo
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
            new_args.append(rewrite_lookup_key(self.model, key))
        return super(MultilingualQuerySet, self).select_related(*new_args, **kwargs)

    # This method was not present in django-linguo
    def _rewrite_col(self, col):
        """Django 1.7 column name rewriting"""
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
            new = []
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
        return q

    def _filter_or_exclude(self, negate, *args, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)
        args = map(self._rewrite_q, args)
        for key, val in kwargs.items():
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = self._rewrite_f(val)
        return super(MultilingualQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)

    def _get_original_fields(self):
        return [f.attname for f in self.model._meta.fields if not isinstance(f, TranslationField)]

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
        for key, val in kwargs.items():
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

    # This method was not present in django-linguo
    def values(self, *fields):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).values(*fields)
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()
        new_args = []
        for key in fields:
            new_args.append(rewrite_lookup_key(self.model, key))
        vqs = super(MultilingualQuerySet, self).values(*new_args)
        vqs.field_names = list(fields)
        return vqs

    # This method was not present in django-linguo
    def values_list(self, *fields, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).values_list(*fields, **kwargs)
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()
        new_args = []
        for key in fields:
            new_args.append(rewrite_lookup_key(self.model, key))
        return super(MultilingualQuerySet, self).values_list(*new_args, **kwargs)

    # This method was not present in django-linguo
    def dates(self, field_name, *args, **kwargs):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).dates(field_name, *args, **kwargs)
        new_key = rewrite_lookup_key(self.model, field_name)
        return super(MultilingualQuerySet, self).dates(new_key, *args, **kwargs)


def get_queryset(obj):
    if hasattr(obj, 'get_queryset'):
        return obj.get_queryset()
    else:  # Django 1.4 / 1.5 compat
        return obj.get_query_set()


class MultilingualQuerysetManager(models.Manager):
    """
    This class gets hooked in MRO just before plain Manager, so that every call to
    get_queryset returns MultilingualQuerySet.
    """
    def get_queryset(self):
        qs = get_queryset(super(MultilingualQuerysetManager, self))
        return self._patch_queryset(qs)

    def _patch_queryset(self, qs):
        if qs.__class__ == models.query.QuerySet:
            qs.__class__ = MultilingualQuerySet
        else:
            class NewClass(qs.__class__, MultilingualQuerySet):
                pass
            NewClass.__name__ = 'Multilingual%s' % qs.__class__.__name__
            qs.__class__ = NewClass
        qs._post_init()
        qs._rewrite_applied_operations()
        return qs

    get_query_set = get_queryset


class MultilingualManager(MultilingualQuerysetManager):
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
        qs = get_queryset(super(MultilingualManager, self))
        if isinstance(qs, MultilingualQuerySet):
            # Is already patched by MultilingualQuerysetManager - in most of the cases
            # when custom managers use super() properly in get_queryset.
            return qs
        return self._patch_queryset(qs)

    get_query_set = get_queryset
