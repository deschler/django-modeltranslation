import os
import warnings

warnings.simplefilter('always', DeprecationWarning)


def _get_database_config():
    db = os.getenv('DB', 'sqlite')
    host = os.getenv('DB_HOST', 'localhost')
    conf = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'SERIALIZE': False,
        },
    }
    if db == 'mysql':
        conf.update(
            {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': os.getenv('MYSQL_DATABASE', 'modeltranslation'),
                'USER': os.getenv('MYSQL_USER', 'root'),
                'PASSWORD': os.getenv('MYSQL_PASSWORD', 'password'),
                'HOST': host,
            }
        )
    elif db == 'postgres':
        conf.update(
            {
                'ENGINE': 'django.db.backends.postgresql',
                'USER': os.getenv('POSTGRES_USER', 'postgres'),
                'PASSWORD': os.getenv('POSTGRES_DB', 'postgres'),
                'NAME': os.getenv('POSTGRES_DB', 'modeltranslation'),
                'HOST': host,
            }
        )
    return conf


DATABASES = {"default": _get_database_config()}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'modeltranslation',
    'modeltranslation.tests',
)

LANGUAGES = (('de', 'Deutsch'), ('en', 'English'))
LANGUAGE_CODE = 'de'

USE_I18N = True
USE_TZ = False
MIDDLEWARE_CLASSES = ()

MODELTRANSLATION_DEFAULT_LANGUAGE = 'de'
MODELTRANSLATION_AUTO_POPULATE = False
MODELTRANSLATION_FALLBACK_LANGUAGES = ()

ROOT_URLCONF = 'modeltranslation.tests.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
