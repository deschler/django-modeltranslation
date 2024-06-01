"""
The idea of MultilingualManager is taken from
django-linguo by Zach Mathew

https://github.com/zmathew/django-linguo
"""

from __future__ import annotations

import itertools
from functools import reduce
from typing import Any, Literal, TypeVar, cast, overload
from collections.abc import Container, Iterator, Sequence, Iterable

from django.contrib.admin.utils import get_model_from_relation
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.backends.utils import CursorWrapper
from django.db.models import Field, Model, F
from django.db.models.expressions import Col
from django.db.models.functions import Concat, ConcatPair
from django.db.models.lookups import Lookup
from django.db.models.query import QuerySet, ValuesIterable
from django.db.models.utils import create_namedtuple_class
from django.utils.tree import Node

from modeltranslation._typing import Self, AutoPopulate
from modeltranslation.fields import TranslationField
from modeltranslation.thread_context import auto_populate_mode
from modeltranslation.utils import (
    auto_populate,
    build_localized_fieldname,
    get_language,
    resolution_order,
)

_C2F_CACHE: dict[tuple[type[Model], str], Field] = {}
_F2TM_CACHE: dict[type[Model], dict[str, type[Model]]] = {}


def get_translatable_fields_for_model(model: type[Model]) -> list[str] | None:
    from modeltranslation.translator import NotRegistered, translator

    try:
        return translator.get_options_for_model(model).get_field_names()
    except NotRegistered:
        return None


def rewrite_lookup_key(model: type[Model], lookup_key: str) -> str:
    try:
        pieces = lookup_key.split("__", 1)
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
        return "__".join(pieces)
    except AttributeError:
        return lookup_key


def append_fallback(model: type[Model], fields: Sequence[str]) -> tuple[set[str], set[str]]:
    """
    If translated field is encountered, add also all its fallback fields.
    Returns tuple: (set_of_new_fields_to_use, set_of_translated_field_names)
    """
    fields_set = set(fields)
    trans: set[str] = set()
    from modeltranslation.translator import translator

    opts = translator.get_options_for_model(model)
    for key, _ in opts.all_fields.items():
        if key in fields_set:
            langs = resolution_order(get_language(), getattr(model, key).fallback_languages)
            fields_set = fields_set.union(build_localized_fieldname(key, lang) for lang in langs)
            fields_set.remove(key)
            trans.add(key)
    return fields_set, trans


def append_translated(model: type[Model], fields: Iterable[str]) -> set[str]:
    "If translated field is encountered, add also all its translation fields."
    fields_set = set(fields)
    from modeltranslation.translator import translator

    opts = translator.get_options_for_model(model)
    for key, translated in opts.all_fields.items():
        if key in fields_set:
            fields_set = fields_set.union(f.name for f in translated)
    return fields_set


def append_lookup_key(model: type[Model], lookup_key: str) -> set[str]:
    "Transform spanned__lookup__key into all possible translation versions, on all levels"
    pieces = lookup_key.split("__", 1)

    fields = append_translated(model, (pieces[0],))

    if len(pieces) > 1:
        # Check if we are doing a lookup to a related trans model
        fields_to_trans_models = get_fields_to_translatable_models(model)
        if pieces[0] in fields_to_trans_models:
            transmodel = fields_to_trans_models[pieces[0]]
            rest = append_lookup_key(transmodel, pieces[1])
            fields = {"__".join(pr) for pr in itertools.product(fields, rest)}
        else:
            fields = {"%s__%s" % (f, pieces[1]) for f in fields}
    return fields


def append_lookup_keys(model: type[Model], fields: Sequence[str]) -> set[str]:
    new_fields = []
    for field in fields:
        try:
            new_field: Container[str] = append_lookup_key(model, field)
        except AttributeError:
            new_field = (field,)
        new_fields.append(new_field)

    return reduce(set.union, new_fields, set())  # type: ignore[arg-type]


def rewrite_order_lookup_key(model: type[Model], lookup_key: str) -> str:
    try:
        if lookup_key.startswith("-"):
            return "-" + rewrite_lookup_key(model, lookup_key[1:])
        else:
            return rewrite_lookup_key(model, lookup_key)
    except AttributeError:
        return lookup_key


def get_fields_to_translatable_models(model: type[Model]) -> dict[str, type[Model]]:
    if model in _F2TM_CACHE:
        return _F2TM_CACHE[model]

    results: list[tuple[str, type[Model]]] = []
    for f in model._meta.get_fields():
        if f.is_relation and f.related_model:
            # The new get_field() will find GenericForeignKey relations.
            # In that case the 'related_model' attribute is set to None
            # so it is necessary to check for this value before trying to
            # get translatable fields.
            related_model = get_model_from_relation(f)  # type: ignore[arg-type]
            if get_translatable_fields_for_model(related_model) is not None:
                results.append((f.name, related_model))
    _F2TM_CACHE[model] = dict(results)
    return _F2TM_CACHE[model]


def get_field_by_colum_name(model: type[Model], col: str) -> Field:
    # First, try field with the column name
    try:
        field = cast(Field, model._meta.get_field(col))
        if field.column == col:
            return field
    except FieldDoesNotExist:
        pass
    field = _C2F_CACHE.get((model, col), None)  # type: ignore[arg-type]
    if field:
        return field
    # D'oh, need to search through all of them.
    for field in model._meta.fields:
        if field.column == col:
            _C2F_CACHE[(model, col)] = field
            return field
    assert False, "No field found for column %s" % col


_T = TypeVar("_T", bound=Model, covariant=True)


class MultilingualQuerySet(QuerySet[_T]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._post_init()

    def _post_init(self) -> None:
        self._rewrite = True
        self._populate = None
        if self.model and self.query.default_ordering and (not self.query.order_by):
            if self.model._meta.ordering:
                # If we have default ordering specified on the model, set it now so that
                # it can be rewritten. Otherwise sql.compiler will grab it directly from _meta
                ordering = []
                for key in self.model._meta.ordering:
                    ordering.append(rewrite_order_lookup_key(self.model, key))
                self.query.add_ordering(*ordering)

    def __reduce__(self):
        return multilingual_queryset_factory, (self.__class__.__bases__[0],), self.__getstate__()

    def _clone(self) -> Self:
        return self.__clone()

    def __clone(self, **kwargs: Any) -> Self:
        # This method is private, so outside code can use default _clone without `kwargs`,
        # and we're here can use private version with `kwargs`.
        # Refs: https://github.com/deschler/django-modeltranslation/issues/483
        kwargs.setdefault("_rewrite", self._rewrite)
        kwargs.setdefault("_populate", self._populate)
        if hasattr(self, "translation_fields"):
            kwargs.setdefault("translation_fields", self.translation_fields)
        if hasattr(self, "original_fields"):
            kwargs.setdefault("original_fields", self.original_fields)
        cloned = super()._clone()
        cloned.__dict__.update(kwargs)
        return cloned

    def rewrite(self, mode: bool = True) -> Self:
        return self.__clone(_rewrite=mode)

    def populate(self, mode: AutoPopulate = "all") -> Self:
        """
        Overrides the translation fields population mode for this query set.
        """
        return self.__clone(_populate=mode)

    def _rewrite_applied_operations(self) -> None:
        """
        Rewrite fields in already applied filters/ordering.
        Useful when converting any QuerySet into MultilingualQuerySet.
        """
        self._rewrite_where(self.query.where)
        self._rewrite_order()
        self._rewrite_select_related()

    # This method was not present in django-linguo
    def select_related(self, *fields: Any, **kwargs: Any) -> Self:
        if not self._rewrite:
            return super().select_related(*fields, **kwargs)
        # TO CONSIDER: whether this should rewrite only current language, or all languages?
        # fk -> [fk, fk_en] (with en=active) VS fk -> [fk, fk_en, fk_de, fk_fr ...] (for all langs)

        # new_args = append_lookup_keys(self.model, fields)
        new_args: list[str | None] = []
        for key in fields:
            if key is None:
                new_args.append(None)
            else:
                new_args.append(rewrite_lookup_key(self.model, key))
        return super().select_related(*new_args, **kwargs)

    # This method was not present in django-linguo
    def _rewrite_col(self, col: Col) -> None:
        """Django >= 1.7 column name rewriting"""
        if isinstance(col, Col):
            new_name = rewrite_lookup_key(self.model, col.target.name)
            if col.target.name != new_name:
                new_field = self.model._meta.get_field(new_name)
                if col.target is col.source:
                    col.source = new_field
                col.target = new_field
        elif hasattr(col, "col"):
            self._rewrite_col(col.col)
        elif hasattr(col, "lhs"):
            self._rewrite_col(col.lhs)

    def _rewrite_where(self, q: Lookup | Node) -> None:
        """
        Rewrite field names inside WHERE tree.
        """
        if isinstance(q, Lookup):
            self._rewrite_col(q.lhs)
        if isinstance(q, Node):
            for child in q.children:
                self._rewrite_where(child)  # type: ignore[arg-type]

    def _rewrite_order(self) -> None:
        self.query.order_by = [
            rewrite_order_lookup_key(self.model, field_name) for field_name in self.query.order_by
        ]

    def _rewrite_select_related(self) -> None:
        if isinstance(self.query.select_related, dict):
            new = {}
            for field_name, value in self.query.select_related.items():
                new[rewrite_order_lookup_key(self.model, field_name)] = value
            self.query.select_related = new

    # This method was not present in django-linguo
    def _rewrite_q(self, q: Node | tuple[str, Any]) -> Any:
        """Rewrite field names inside Q call."""
        if isinstance(q, tuple) and len(q) == 2:
            return rewrite_lookup_key(self.model, q[0]), q[1]
        if isinstance(q, Node):
            q.children = list(map(self._rewrite_q, q.children))  # type: ignore[arg-type]
        return q

    # This method was not present in django-linguo
    def _rewrite_f(self, q: models.F | Node) -> models.F | Node:
        """
        Rewrite field names inside F call.
        """
        if isinstance(q, models.F):
            q.name = rewrite_lookup_key(self.model, q.name)
            return q
        if isinstance(q, Node):
            q.children = list(map(self._rewrite_f, q.children))  # type: ignore[arg-type]
        # Django >= 1.8
        if hasattr(q, "lhs"):
            q.lhs = self._rewrite_f(q.lhs)
        if hasattr(q, "rhs"):
            q.rhs = self._rewrite_f(q.rhs)
        return q

    def _rewrite_filter_or_exclude(self, args: Any, kwargs: Any) -> tuple[Any, Any]:
        if not self._rewrite:
            return args, kwargs
        args = tuple(map(self._rewrite_q, args))
        for key, val in list(kwargs.items()):
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = self._rewrite_f(val)
        return args, kwargs

    def _filter_or_exclude(self, negate: bool, args: Any, kwargs: Any) -> Self:
        args, kwargs = self._rewrite_filter_or_exclude(args, kwargs)
        return super()._filter_or_exclude(negate, args, kwargs)

    def _get_original_fields(self) -> list[str]:
        source = (
            self.model._meta.concrete_fields
            if hasattr(self.model._meta, "concrete_fields")
            else self.model._meta.fields
        )
        return [f.attname for f in source if not isinstance(f, TranslationField)]

    def order_by(self, *field_names: Any) -> Self:
        """
        Change translatable field names in an ``order_by`` argument
        to translation fields for the current language.
        """
        if not self._rewrite:
            return super().order_by(*field_names)
        new_args = []
        for key in field_names:
            new_args.append(rewrite_order_lookup_key(self.model, key))
        return super().order_by(*new_args)

    def distinct(self, *field_names: Any) -> Self:
        """
        Change translatable field names in an ``distinct`` argument
        to translation fields for the current language.
        """
        if not self._rewrite:
            return super().distinct(*field_names)
        new_args = []
        for key in field_names:
            new_args.append(rewrite_order_lookup_key(self.model, key))
        return super().distinct(*new_args)

    def update(self, **kwargs: Any) -> int:
        if not self._rewrite:
            return super().update(**kwargs)
        for key, val in list(kwargs.items()):
            new_key = rewrite_lookup_key(self.model, key)
            del kwargs[key]
            kwargs[new_key] = self._rewrite_f(val)
        return super().update(**kwargs)

    update.alters_data = True

    def _update(self, values: list[tuple[Field, type[Model] | None, Any]]) -> CursorWrapper:
        """
        This method is called in .save() method to update an existing record.
        Here we force to update translation fields as well if the original
        field only is passed in `save()` in argument `update_fields`.
        """
        # TODO: Should the original field (field without lang code suffix) be updated
        # when only the default translation field (`field_<DEFAULT_LANG_CODE>`) is passed in `update_fields`?
        # Currently, we don't synchronize values of the original and default translation fields in that case.
        field_names_to_update = {field.name for field, *_ in values}

        translation_values: list[tuple[Field, type[Model] | None, Any]] = []
        for field, model, value in values:
            translation_field_name = rewrite_lookup_key(self.model, field.name)
            if translation_field_name not in field_names_to_update:
                translatable_field = cast(Field, self.model._meta.get_field(translation_field_name))
                translation_values.append((translatable_field, model, value))

        values += translation_values
        return super()._update(values)

    # This method was not present in django-linguo
    @property
    def _populate_mode(self) -> AutoPopulate:
        # Populate can be set using a global setting or a manager method.
        if self._populate is None:
            return auto_populate_mode()
        return self._populate

    # This method was not present in django-linguo
    def create(self, **kwargs: Any) -> _T:
        """
        Allows to override population mode with a ``populate`` method.
        """
        with auto_populate(self._populate_mode):
            return super().create(**kwargs)

    # This method was not present in django-linguo
    def get_or_create(self, *args: Any, **kwargs: Any) -> tuple[_T, bool]:
        """
        Allows to override population mode with a ``populate`` method.
        """
        with auto_populate(self._populate_mode):
            return super().get_or_create(*args, **kwargs)

    # This method was not present in django-linguo
    def defer(self, *fields: Any) -> Self:
        fields = append_lookup_keys(self.model, fields)  # type: ignore[assignment]
        return super().defer(*fields)

    # This method was not present in django-linguo
    def only(self, *fields: Any) -> Self:
        fields = append_lookup_keys(self.model, fields)  # type: ignore[assignment]
        return super().only(*fields)

    # This method was not present in django-linguo
    def raw_values(self, *fields: str, **expressions: Any) -> Self:
        return super().values(*fields, **expressions)

    def _values(self, *original: str, **kwargs: Any) -> Self:
        selects_all = kwargs.pop("selects_all", False)
        if not kwargs.pop("prepare", False):
            return super()._values(*original, **kwargs)
        new_fields, translation_fields = append_fallback(self.model, original)
        annotation_keys = set(self.query.annotation_select.keys()) if selects_all else set()
        new_fields.update(annotation_keys)
        clone = super()._values(*list(new_fields), **kwargs)
        clone.original_fields = tuple(original)
        clone.translation_fields = translation_fields
        return clone

    # This method was not present in django-linguo
    def values(self, *fields: str, **expressions: Any) -> Self:
        if not self._rewrite:
            return super().values(*fields, **expressions)
        selects_all = not fields
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()  # type: ignore[assignment]
        fields += tuple(expressions)
        clone = self._values(*fields, prepare=True, selects_all=selects_all, **expressions)
        clone._iterable_class = FallbackValuesIterable
        return clone

    # This method was not present in django-linguo
    def values_list(self, *fields: str, flat: bool = False, named: bool = False) -> Self:
        if not self._rewrite:
            return super().values_list(*fields, flat=flat, named=named)
        if flat and named:
            raise TypeError("'flat' and 'named' can't be used together.")
        if flat and len(fields) > 1:
            raise TypeError(
                "'flat' is not valid when values_list is called with more than one field."
            )
        selects_all = not fields
        if not fields:
            # Emulate original queryset behaviour: get all fields that are not translation fields
            fields = self._get_original_fields()  # type: ignore[assignment]

        field_names = {f for f in fields if not hasattr(f, "resolve_expression")}
        _fields = []
        expressions = {}
        counter = 1
        for field in fields:
            if hasattr(field, "resolve_expression"):
                field_id_prefix = getattr(field, "default_alias", field.__class__.__name__.lower())
                while True:
                    field_id = field_id_prefix + str(counter)
                    counter += 1
                    if field_id not in field_names:
                        break
                expressions[field_id] = field
                _fields.append(field_id)
            else:
                _fields.append(field)

        clone = self._values(*_fields, prepare=True, selects_all=selects_all, **expressions)
        clone._iterable_class = (
            FallbackNamedValuesListIterable
            if named
            else FallbackFlatValuesListIterable
            if flat
            else FallbackValuesListIterable
        )
        return clone

    # This method was not present in django-linguo
    def dates(self, field_name: str, *args: Any, **kwargs: Any) -> Self:
        if not self._rewrite:
            return super().dates(field_name, *args, **kwargs)
        new_key = rewrite_lookup_key(self.model, field_name)
        return super().dates(new_key, *args, **kwargs)

    def _rewrite_concat(self, concat: Concat | ConcatPair):
        new_source_expressions = []
        for exp in concat.source_expressions:
            if isinstance(exp, (Concat, ConcatPair)):
                exp = self._rewrite_concat(exp)
            if isinstance(exp, F):
                exp = self._rewrite_f(exp)
            new_source_expressions.append(exp)
        concat.set_source_expressions(new_source_expressions)
        return concat

    def annotate(self, *args: Any, **kwargs: Any) -> Self:
        if not self._rewrite:
            return super().annotate(*args, **kwargs)
        for key, val in list(kwargs.items()):
            if isinstance(val, models.F):
                kwargs[key] = self._rewrite_f(val)
            if isinstance(val, Concat):
                kwargs[key] = self._rewrite_concat(val)
        return super().annotate(*args, **kwargs)


class FallbackValuesIterable(ValuesIterable):
    queryset: MultilingualQuerySet[Model]

    class X:
        # This stupid class is needed as object use __slots__ and has no __dict__.
        pass

    def __iter__(self) -> Iterator[dict[str, Any]]:
        instance = self.X()

        fields = self.queryset.original_fields
        fields += tuple(f for f in self.queryset.query.annotation_select if f not in fields)

        for row in super().__iter__():
            instance.__dict__.update(row)
            for key in self.queryset.translation_fields:
                row[key] = getattr(self.queryset.model, key).__get__(instance, None)
            # Restore original ordering.
            yield {k: row[k] for k in fields}


class FallbackValuesListIterable(FallbackValuesIterable):
    def __iter__(self) -> Iterator[tuple[Any, ...]]:
        for row in super().__iter__():
            yield tuple(row.values())


class FallbackNamedValuesListIterable(FallbackValuesIterable):
    def __iter__(self) -> Iterator[tuple[Any, ...]]:
        for row in super().__iter__():
            names, values = row.keys(), row.values()
            tuple_class = create_namedtuple_class(*names)
            new = tuple.__new__
            yield new(tuple_class, values)


class FallbackFlatValuesListIterable(FallbackValuesListIterable):
    def __iter__(self) -> Iterator[Any]:
        for row in super().__iter__():
            yield row[0]


@overload
def multilingual_queryset_factory(
    old_cls: type[Any], instantiate: Literal[False]
) -> type[MultilingualQuerySet]: ...


@overload
def multilingual_queryset_factory(
    old_cls: type[Any], instantiate: Literal[True] = ...
) -> MultilingualQuerySet: ...


def multilingual_queryset_factory(
    old_cls: type[Any], instantiate: bool = True
) -> type[MultilingualQuerySet] | MultilingualQuerySet:
    if old_cls == models.query.QuerySet:
        NewClass = MultilingualQuerySet
    else:

        class NewClass(old_cls, MultilingualQuerySet):  # type: ignore[no-redef]
            pass

        NewClass.__name__ = "Multilingual%s" % old_cls.__name__
    return NewClass() if instantiate else NewClass


class MultilingualQuerysetManager(models.Manager[_T]):
    """
    This class gets hooked in MRO just before plain Manager, so that every call to
    get_queryset returns MultilingualQuerySet.
    """

    def get_queryset(self) -> MultilingualQuerySet[_T]:
        qs = super().get_queryset()
        return self._patch_queryset(qs)

    def _patch_queryset(self, qs: QuerySet[_T]) -> MultilingualQuerySet[_T]:
        qs.__class__ = multilingual_queryset_factory(qs.__class__, instantiate=False)
        qs = cast(MultilingualQuerySet[_T], qs)
        qs._post_init()
        qs._rewrite_applied_operations()
        return qs


class MultilingualManager(MultilingualQuerysetManager[_T]):
    def rewrite(self, *args: Any, **kwargs: Any):
        return self.get_queryset().rewrite(*args, **kwargs)

    def populate(self, *args: Any, **kwargs: Any):
        return self.get_queryset().populate(*args, **kwargs)

    def raw_values(self, *args: Any, **kwargs: Any):
        return self.get_queryset().raw_values(*args, **kwargs)

    def get_queryset(self) -> MultilingualQuerySet[_T]:
        """
        This method is repeated because some managers that don't use super() or alter queryset class
        may return queryset that is not subclass of MultilingualQuerySet.
        """
        qs = super().get_queryset()
        if isinstance(qs, MultilingualQuerySet):
            # Is already patched by MultilingualQuerysetManager - in most of the cases
            # when custom managers use super() properly in get_queryset.
            return qs
        return self._patch_queryset(qs)
