# -*- coding: utf-8 -*-
"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""
from django.db import models
from django.db.models.fields.related import RelatedField, RelatedObject
from django.db.models.sql.where import Constraint
from django.utils.tree import Node

from modeltranslation import settings
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
        for field_to_trans, transmodel in fields_to_trans_models:
            # Check ``original key``, as pieces[0] may have been already rewritten.
            if original_key == field_to_trans:
                pieces[1] = rewrite_lookup_key(transmodel, pieces[1])
                break
    return '__'.join(pieces)


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
        _F2TM_CACHE[model] = results
    return _F2TM_CACHE[model]


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

    def _rewrite_where(self, q):
        """
        Rewrite field names inside WHERE tree.
        """
        if isinstance(q, tuple) and isinstance(q[0], Constraint):
            c = q[0]
            new_name = rewrite_lookup_key(self.model, c.field.name)
            if c.field.name != new_name:
                c.field = self.model._meta.get_field(new_name)
                c.col = c.field.column
        if isinstance(q, Node):
            for child in q.children:
                self._rewrite_where(child)

    def _rewrite_order(self):
        self.query.order_by = [rewrite_order_lookup_key(self.model, field_name)
                               for field_name in self.query.order_by]

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

    def _append_translated(self, fields):
        "If translated field is encountered, add also all its translation fields."
        fields = set(fields)
        from modeltranslation.translator import translator
        opts = translator.get_options_for_model(self.model)
        for key, translated in opts.fields.items():
            if key in fields:
                fields = fields.union(f.name for f in translated)
        return fields

    # This method was not present in django-linguo
    def defer(self, *fields):
        fields = self._append_translated(fields)
        return super(MultilingualQuerySet, self).defer(*fields)

    # This method was not present in django-linguo
    def only(self, *fields):
        fields = self._append_translated(fields)
        return super(MultilingualQuerySet, self).only(*fields)

    # This method was not present in django-linguo
    def raw_values(self, *fields):
        return super(MultilingualQuerySet, self).values(*fields)

    # This method was not present in django-linguo
    def values(self, *fields):
        if not self._rewrite:
            return super(MultilingualQuerySet, self).values(*fields)
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


class MultilingualManager(models.Manager):
    use_for_related_fields = True

    def rewrite(self, *args, **kwargs):
        return self.get_query_set().rewrite(*args, **kwargs)

    def populate(self, *args, **kwargs):
        return self.get_query_set().populate(*args, **kwargs)

    def raw_values(self, *args, **kwargs):
        return self.get_query_set().raw_values(*args, **kwargs)

    def get_query_set(self):
        qs = super(MultilingualManager, self).get_query_set()
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
