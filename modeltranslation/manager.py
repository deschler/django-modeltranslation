# -*- coding: utf-8 -*-
"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""
from django.db import models
from django.db.models.fields.related import RelatedField
from django.db.models.sql.where import Constraint
from django.utils.tree import Node

from modeltranslation import settings
from modeltranslation.utils import build_localized_fieldname, get_language


def get_translatable_fields_for_model(model):
    from modeltranslation.translator import NotRegistered, translator
    try:
        return translator.get_options_for_model(model).fields
    except NotRegistered:
        return None


def rewrite_lookup_key(model, lookup_key):
    translatable_fields = get_translatable_fields_for_model(model)
    if translatable_fields is not None:
        pieces = lookup_key.split('__')
        # If we are doing a lookup on a translatable field,
        # we want to rewrite it to the actual field name
        # For example, we want to rewrite "name__startswith" to "name_fr__startswith"
        if pieces[0] in translatable_fields:
            lookup_key = build_localized_fieldname(pieces[0], get_language())
            remaining_lookup = '__'.join(pieces[1:])
            if remaining_lookup:
                lookup_key = '%s__%s' % (lookup_key, remaining_lookup)

    pieces = lookup_key.split('__')
    if len(pieces) > 1:
        # Check if we are doing a lookup to a related trans model
        fields_to_trans_models = get_fields_to_translatable_models(model)
        for field_to_trans, transmodel in fields_to_trans_models:
            if pieces[0] == field_to_trans:
                sub_lookup = '__'.join(pieces[1:])
                if sub_lookup:
                    sub_lookup = rewrite_lookup_key(transmodel, sub_lookup)
                    lookup_key = '%s__%s' % (pieces[0], sub_lookup)
                break

    return lookup_key


def rewrite_order_lookup_key(model, lookup_key):
    if lookup_key.startswith('-'):
        return '-' + rewrite_lookup_key(model, lookup_key[1:])
    else:
        return rewrite_lookup_key(model, lookup_key)


def get_fields_to_translatable_models(model):
    from modeltranslation.translator import translator
    results = []
    for field_name in translator.get_options_for_model(model).fields.keys():
        field_object, modelclass, direct, m2m = model._meta.get_field_by_name(field_name)
        if direct and isinstance(field_object, RelatedField):
            if get_translatable_fields_for_model(field_object.related.parent_model) is not None:
                results.append((field_name, field_object.related.parent_model))
    return results


class MultilingualQuerySet(models.query.QuerySet):
    _rewrite = True

    def __init__(self, *args, **kwargs):
        super(MultilingualQuerySet, self).__init__(*args, **kwargs)
        self._post_init()

    def _post_init(self):
        if self.model and (not self.query.order_by):
            if self.model._meta.ordering:
                # If we have default ordering specified on the model, set it now so that
                # it can be rewritten. Otherwise sql.compiler will grab it directly from _meta
                ordering = []
                for key in self.model._meta.ordering:
                    ordering.append(rewrite_order_lookup_key(self.model, key))
                self.query.add_ordering(*ordering)

    # This method was not present in django-linguo
    def _clone(self, *args, **kwargs):
        kwargs.setdefault('_rewrite', self._rewrite)
        return super(MultilingualQuerySet, self)._clone(*args, **kwargs)

    # This method was not present in django-linguo
    def rewrite(self, mode=True):
        return self._clone(_rewrite=mode)

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
            map(self._rewrite_where, q.children)

    def _rewrite_order(self):
        self.query.order_by = [rewrite_order_lookup_key(self.model, field_name)
                               for field_name in self.query.order_by]

    # This method was not present in django-linguo
    def _rewrite_q(self, q):
        """Rewrite field names inside Q call."""
        if isinstance(q, tuple) and len(q) == 2:
            return rewrite_lookup_key(self.model, q[0]), q[1]
        if isinstance(q, Node):
            q.children = map(self._rewrite_q, q.children)
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
            q.children = map(self._rewrite_f, q.children)
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
    def create(self, **kwargs):
        populate = kwargs.pop('_populate', settings.AUTO_POPULATE)
        if populate:
            translatable_fields = get_translatable_fields_for_model(self.model)
            if translatable_fields is not None:
                for key, val in kwargs.items():
                    if key in translatable_fields:
                        # Try to add value in every language
                        for translation_field in translatable_fields[key]:
                            kwargs.setdefault(translation_field.name, val)
        # If not use populate feature, then normal rewriting will occur at model's __init__
        # That's why it is not performed here - no reason to rewrite twice.
        return super(MultilingualQuerySet, self).create(**kwargs)


class MultilingualManager(models.Manager):
    use_for_related_fields = True

    def rewrite(self, *args, **kwargs):
        return self.get_query_set().rewrite(*args, **kwargs)

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
