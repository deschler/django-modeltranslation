# -*- coding: utf-8 -*-
from django.conf import global_settings, settings as django_settings
from django.utils.encoding import force_unicode
from django.utils.translation import get_language as _get_language
from django.utils.functional import lazy

from modeltranslation import settings


def get_language():
    """
    Return an active language code that is guaranteed to be in
    settings.LANGUAGES (Django does not seem to guarantee this for us).
    """
    lang = _get_language()
    if lang not in settings.AVAILABLE_LANGUAGES and '-' in lang:
        lang = lang.split('-')[0]
    if lang in settings.AVAILABLE_LANGUAGES:
        return lang
    return settings.DEFAULT_LANGUAGE


def get_supported_languages():
    supported_languages = ['en-us']
    supported_languages.extend([l[0] for l in django_settings.LANGUAGES])
    supported_languages.extend([l[0] for l in global_settings.LANGUAGES])
    return set(supported_languages)
supported_languages = get_supported_languages()


def get_translation_fields(field):
    """
    Returns a list of localized fieldnames for a given field.
    """
    return [build_localized_fieldname(field, l) for l in settings.AVAILABLE_LANGUAGES]


def build_localized_fieldname(field_name, lang):
    return str('%s_%s' % (field_name, lang.replace('-', '_')))


def _build_localized_verbose_name(verbose_name, lang):
    return u'%s [%s]' % (force_unicode(verbose_name), lang)
build_localized_verbose_name = lazy(_build_localized_verbose_name, unicode)


def _join_css_class(bits, offset):
    if '-'.join(bits[-offset:]) in supported_languages:
        return '%s-%s' % ('_'.join(bits[:len(bits) - offset]), '_'.join(bits[-offset:]))
    return ''


def build_css_class(localized_fieldname, prefix=''):
    """
    Returns a css class based on ``localized_fieldname`` which is easily
    splitable and capable of regionalized language codes.

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
    if override is None:
        override = {}
    fallback_for_lang = override.get(lang, settings.FALLBACK_LANGUAGES.get(lang, ()))
    fallback_def = override.get('default', settings.FALLBACK_LANGUAGES['default'])
    order = (lang,) + fallback_for_lang + fallback_def
    return tuple(unique(order))
