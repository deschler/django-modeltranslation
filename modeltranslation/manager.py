"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""
from django.db import models
from django.db.models.fields.related import RelatedField
from django.utils.tree import Node

from modeltranslation.utils import build_localized_fieldname, get_language
from modeltranslation import settings


_registry = {}


def get_translatable_fields_for_model(model):
    from modeltranslation import translator
    if model not in _registry:
        try:
            _registry[model] = dict(
                translator.translator.get_options_for_model(model).localized_fieldnames)
        except translator.NotRegistered:
            _registry[model] = None
    return _registry[model]


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


def get_fields_to_translatable_models(model):
    results = []
    for field_name in model._meta.get_all_field_names():
        field_object, modelclass, direct, m2m = model._meta.get_field_by_name(field_name)
        if direct and isinstance(field_object, RelatedField):
            if get_translatable_fields_for_model(field_object.related.parent_model) is not None:
                results.append((field_name, field_object.related.parent_model))
    return results


class MultilingualQuerySet(models.query.QuerySet):
    _rewrite = True

    def __init__(self, *args, **kwargs):
        super(MultilingualQuerySet, self).__init__(*args, **kwargs)
        if self.model and (not self.query.order_by):
            if self.model._meta.ordering:
                # If we have default ordering specified on the model, set it now so that
                # it can be rewritten. Otherwise sql.compiler will grab it directly from _meta
                ordering = []
                for key in self.model._meta.ordering:
                    ordering.append(rewrite_lookup_key(self.model, key))
                self.query.add_ordering(*ordering)

    # This method was not present in django-linguo
    def _clone(self, *args, **kwargs):
        kwargs.setdefault('_rewrite', self._rewrite)
        return super(MultilingualQuerySet, self)._clone(*args, **kwargs)

    # This method was not present in django-linguo
    def rewrite(self, mode=True):
        return self._clone(_rewrite=mode)

    # This method was not present in django-linguo
    def _rewrite_q(self, q):
        "Rewrite field names inside Q call."
        if isinstance(q, tuple) and len(q) == 2:
            return rewrite_lookup_key(self.model, q[0]), q[1]
        if isinstance(q, Node):
            q.children = map(self._rewrite_q, q.children)
        return q

    # This method was not present in django-linguo
    def _rewrite_f(self, q):
        "Rewrite field names inside F call."
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
        if not self._rewrite:
            return super(MultilingualQuerySet, self).order_by(*field_names)
        new_args = []
        for key in field_names:
            new_args.append(rewrite_lookup_key(self.model, key))
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
                        for new_key in translatable_fields[key]:
                            kwargs.setdefault(new_key, val)
        else:
            # If not use populate feature, then perform normal rewriting
            for key, val in kwargs.items():
                new_key = rewrite_lookup_key(self.model, key)
                del kwargs[key]
                kwargs.setdefault(new_key, val)
        return super(MultilingualQuerySet, self).create(**kwargs)


class MultilingualManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        return MultilingualQuerySet(self.model)
