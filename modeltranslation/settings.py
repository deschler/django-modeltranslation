from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ._typing import AutoPopulate, _ListOrTuple

TRANSLATION_FILES: tuple[str, ...] = tuple(
    getattr(settings, "MODELTRANSLATION_TRANSLATION_FILES", ())
)

AVAILABLE_LANGUAGES: list[str] = list(
    getattr(
        settings,
        "MODELTRANSLATION_LANGUAGES",
        (val for val, label in settings.LANGUAGES),
    )
)
_default_language: str | None = getattr(settings, "MODELTRANSLATION_DEFAULT_LANGUAGE", None)
if _default_language and _default_language not in AVAILABLE_LANGUAGES:
    raise ImproperlyConfigured("MODELTRANSLATION_DEFAULT_LANGUAGE not in LANGUAGES setting.")
DEFAULT_LANGUAGE = _default_language or AVAILABLE_LANGUAGES[0]

REQUIRED_LANGUAGES: _ListOrTuple[str] = getattr(settings, "MODELTRANSLATION_REQUIRED_LANGUAGES", ())

# Fixed base language for prepopulated fields (slugs)
# (If not set, the current request language will be used)
PREPOPULATE_LANGUAGE: str | None = getattr(settings, "MODELTRANSLATION_PREPOPULATE_LANGUAGE", None)
if PREPOPULATE_LANGUAGE and PREPOPULATE_LANGUAGE not in AVAILABLE_LANGUAGES:
    raise ImproperlyConfigured("MODELTRANSLATION_PREPOPULATE_LANGUAGE not in LANGUAGES setting.")

# Load allowed CUSTOM_FIELDS from django settings
CUSTOM_FIELDS: tuple[str, ...] = getattr(settings, "MODELTRANSLATION_CUSTOM_FIELDS", ())

# Don't change this setting unless you really know what you are doing
ENABLE_REGISTRATIONS: bool = getattr(
    settings, "MODELTRANSLATION_ENABLE_REGISTRATIONS", settings.USE_I18N
)

# Modeltranslation specific debug setting
DEBUG: bool = getattr(settings, "MODELTRANSLATION_DEBUG", False)

AUTO_POPULATE: AutoPopulate = getattr(settings, "MODELTRANSLATION_AUTO_POPULATE", False)

# FALLBACK_LANGUAGES should be in either format:
# MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'de')
# MODELTRANSLATION_FALLBACK_LANGUAGES = {'default': ('en', 'de'), 'fr': ('de',)}
# By default we fallback to the default language
_fallback_languages = getattr(settings, "MODELTRANSLATION_FALLBACK_LANGUAGES", (DEFAULT_LANGUAGE,))
if isinstance(_fallback_languages, (tuple, list)):
    _fallback_languages = {"default": tuple(_fallback_languages)}

# To please mypy, explicitly annotate:
FALLBACK_LANGUAGES: dict[str, tuple[str, ...]] = _fallback_languages


if "default" not in FALLBACK_LANGUAGES:
    raise ImproperlyConfigured(
        'MODELTRANSLATION_FALLBACK_LANGUAGES does not contain "default" key.'
    )
for key, value in FALLBACK_LANGUAGES.items():
    if key != "default" and key not in AVAILABLE_LANGUAGES:
        raise ImproperlyConfigured(
            'MODELTRANSLATION_FALLBACK_LANGUAGES: "%s" not in LANGUAGES setting.' % key
        )
    if not isinstance(value, (tuple, list)):
        raise ImproperlyConfigured(
            'MODELTRANSLATION_FALLBACK_LANGUAGES: value for key "%s" is not list nor tuple.' % key
        )
    for lang in value:
        if lang not in AVAILABLE_LANGUAGES:
            raise ImproperlyConfigured(
                'MODELTRANSLATION_FALLBACK_LANGUAGES: "%s" not in LANGUAGES setting.' % lang
            )
ENABLE_FALLBACKS: bool = getattr(settings, "MODELTRANSLATION_ENABLE_FALLBACKS", True)

LOADDATA_RETAIN_LOCALE: bool = getattr(settings, "MODELTRANSLATION_LOADDATA_RETAIN_LOCALE", True)

JQUERY_URL: str = getattr(
    settings,
    "JQUERY_URL",
    "//ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js",
)
JQUERY_UI_URL: str = getattr(
    settings,
    "JQUERY_UI_URL",
    "//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js",
)
