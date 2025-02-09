import os
import warnings

import django_stubs_ext
from modeltranslation._typing import monkeypatch

warnings.simplefilter("always", DeprecationWarning)
django_stubs_ext.monkeypatch()
monkeypatch()


def _get_database_config():
    db = os.getenv("DB", "sqlite")
    host = os.getenv("DB_HOST", "localhost")
    conf = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
    if db == "mysql":
        conf.update(
            {
                "ENGINE": "django.db.backends.mysql",
                "NAME": os.getenv("MYSQL_DATABASE", "modeltranslation"),
                "USER": os.getenv("MYSQL_USER", "root"),
                "PASSWORD": os.getenv("MYSQL_PASSWORD", "password"),
                "HOST": host,
            }
        )
    elif db == "postgres":
        conf.update(
            {
                "ENGINE": "django.db.backends.postgresql",
                "USER": os.getenv("POSTGRES_USER", "postgres"),
                "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
                "NAME": os.getenv("POSTGRES_DB", "modeltranslation"),
                "HOST": host,
            }
        )
    return conf


DATABASES = {"default": _get_database_config()}
SECRET_KEY = "0" * 64

INSTALLED_APPS = (
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.messages",
    "django.contrib.sessions",
    "modeltranslation",
    "modeltranslation.tests",
    "django.contrib.admin",
)

LANGUAGES = (("de", "Deutsch"), ("en", "English"))
LANGUAGE_CODE = "en"

USE_I18N = True
USE_TZ = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "builtins": [
                "django.templatetags.i18n",
                "django.templatetags.static",
            ],
        },
    },
]

MODELTRANSLATION_DEFAULT_LANGUAGE = "de"
MODELTRANSLATION_AUTO_POPULATE = False
MODELTRANSLATION_FALLBACK_LANGUAGES = ()

ROOT_URLCONF = "modeltranslation.tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

TEST_NON_SERIALIZED_APPS = ("django.contrib.auth",)
