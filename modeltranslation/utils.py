from contextlib import contextmanager

from django.db import models
from django.utils.encoding import force_str
from django.utils.functional import lazy
from django.utils.translation import get_language as _get_language
from django.utils.translation import get_language_info

from modeltranslation import settings
from modeltranslation.thread_context import (
    fallbacks_enabled,
    set_auto_populate,
    set_enable_fallbacks,
)


def get_language():
    """
    Return an active language code that is guaranteed to be in
    settings.LANGUAGES (Django does not seem to guarantee this for us).
    """
    lang = _get_language()
    if lang is None:  # Django >= 1.8
        return settings.DEFAULT_LANGUAGE
    if lang not in settings.AVAILABLE_LANGUAGES and '-' in lang:
        lang = lang.split('-')[0]
    if lang in settings.AVAILABLE_LANGUAGES:
        return lang
    return settings.DEFAULT_LANGUAGE


def get_language_bidi(lang):
    """
    Check if a language is bi-directional.
    """
    lang_info = get_language_info(lang)
    return lang_info['bidi']


def get_translation_fields(field):
    """
    Returns a list of localized fieldnames for a given field.
    """
    return [build_localized_fieldname(field, lang) for lang in settings.AVAILABLE_LANGUAGES]


def build_localized_fieldname(field_name, lang):
    if lang == 'id':
        # The 2-letter Indonesian language code is problematic with the
        # current naming scheme as Django foreign keys also add "id" suffix.
        lang = 'ind'
    return str('%s_%s' % (field_name, lang.replace('-', '_')))


def _build_localized_verbose_name(verbose_name, lang):
    if lang == 'id':
        lang = 'ind'
    return force_str('%s [%s]') % (force_str(verbose_name), lang)


build_localized_verbose_name = lazy(_build_localized_verbose_name, str)


def _join_css_class(bits, offset):
    if '-'.join(bits[-offset:]) in settings.AVAILABLE_LANGUAGES + ['en-us']:
        return '%s-%s' % ('_'.join(bits[: len(bits) - offset]), '_'.join(bits[-offset:]))
    return ''


def build_css_class(localized_fieldname, prefix=''):
    """
    Returns a css class based on ``localized_fieldname`` which is easily
    splittable and capable of regionalized language codes.

    Takes an optional ``prefix`` which is prepended to the returned string.
    """
    bits = localized_fieldname.split('_')
    css_class = ''
    if len(bits) == 1:
        css_class = str(localized_fieldname)
    elif len(bits) == 2:
        # Fieldname without underscore and short language code
        # Examples:
        # 'foo_de' --> 'foo-de',
        # 'bar_en' --> 'bar-en'
        css_class = '-'.join(bits)
    elif len(bits) > 2:
        # Try regionalized language code
        # Examples:
        # 'foo_es_ar' --> 'foo-es_ar',
        # 'foo_bar_zh_tw' --> 'foo_bar-zh_tw'
        css_class = _join_css_class(bits, 2)
        if not css_class:
            # Try short language code
            # Examples:
            # 'foo_bar_de' --> 'foo_bar-de',
            # 'foo_bar_baz_de' --> 'foo_bar_baz-de'
            css_class = _join_css_class(bits, 1)
    return '%s-%s' % (prefix, css_class) if prefix else css_class


def unique(seq):
    """
    Returns a generator yielding unique sequence members in order

    A set by itself will return unique values without any regard for order.

    >>> list(unique([1, 2, 3, 2, 2, 4, 1]))
    [1, 2, 3, 4]
    """
    seen = set()
    return (x for x in seq if x not in seen and not seen.add(x))


def resolution_order(lang, override=None):
    """
    Return order of languages which should be checked for parameter language.
    First is always the parameter language, later are fallback languages.
    Override parameter has priority over FALLBACK_LANGUAGES.
    """
    if not fallbacks_enabled():
        return (lang,)

    if override is None:
        override = {}
    fallback_for_lang = override.get(lang, settings.FALLBACK_LANGUAGES.get(lang, ()))
    fallback_def = override.get('default', settings.FALLBACK_LANGUAGES['default'])
    order = (lang,) + fallback_for_lang + fallback_def
    return tuple(unique(order))


@contextmanager
def auto_populate(mode='all'):
    """
    Overrides translation fields population mode (population mode decides which
    unprovided translations will be filled during model construction / loading).

    Example:

        with auto_populate('all'):
            s = Slugged.objects.create(title='foo')
        s.title_en == 'foo' // True
        s.title_de == 'foo' // True

    This method may be used to ensure consistency loading untranslated fixtures,
    with non-default language active:

        with auto_populate('required'):
            call_command('loaddata', 'fixture.json')
    """
    set_auto_populate(mode)
    try:
        yield
    finally:
        set_auto_populate(None)


@contextmanager
def fallbacks(enable=True):
    """
    Temporarily switch all language fallbacks on or off.

    Example:

        with fallbacks(False):
            lang_has_slug = bool(self.slug)

    May be used to enable fallbacks just when they're needed saving on some
    processing or check if there is a value for the current language (not
    knowing the language)
    """
    set_enable_fallbacks(enable)
    try:
        yield
    finally:
        set_enable_fallbacks(None)


def parse_field(setting, field_name, default):
    """
    Extract result from single-value or dict-type setting like fallback_values.
    """
    if isinstance(setting, dict):
        return setting.get(field_name, default)
    else:
        return setting


def build_localized_intermediary_model(intermediary_model: models.Model, lang: str) -> models.Model:
    from modeltranslation.translator import translator

    meta = type(
        "Meta",
        (),
        {
            "db_table": build_localized_fieldname(intermediary_model._meta.db_table, lang),
            "auto_created": intermediary_model._meta.auto_created,
            "app_label": intermediary_model._meta.app_label,
            "db_tablespace": intermediary_model._meta.db_tablespace,
            "unique_together": intermediary_model._meta.unique_together,
            "verbose_name": build_localized_verbose_name(
                intermediary_model._meta.verbose_name, lang
            ),
            "verbose_name_plural": build_localized_verbose_name(
                intermediary_model._meta.verbose_name_plural, lang
            ),
            "apps": intermediary_model._meta.apps,
        },
    )
    klass = type(
        build_localized_fieldname(intermediary_model.__name__, lang),
        (models.Model,),
        {
            **{k: v for k, v in dict(intermediary_model.__dict__).items() if k != "_meta"},
            **{f.name: f.clone() for f in intermediary_model._meta.fields},
            "Meta": meta,
        },
    )

    def lazy_register_model(old_model, new_model, translator):
        cls_opts = translator._get_options_for_model(old_model)
        if cls_opts.registered and new_model not in translator._registry:
            name = "%sTranslationOptions" % new_model.__name__
            translator.register(new_model, type(name, (cls_opts.__class__,), {}))

    translator.lazy_operation(lazy_register_model, intermediary_model, klass)

    return klass
