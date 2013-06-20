#!/usr/bin/env python
import os
import sys

from django.conf import settings
from django.core.management import call_command


def runtests():
    if not settings.configured:
        # Choose database for settings
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        }
        test_db = os.environ.get('DB', 'sqlite')
        if test_db == 'mysql':
            DATABASES['default'].update({
                'ENGINE': 'django.db.backends.mysql',
                'NAME': 'modeltranslation',
                'USER': 'root',
            })
        elif test_db == 'postgres':
            DATABASES['default'].update({
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'USER': 'postgres',
                'NAME': 'modeltranslation',
                'OPTIONS': {
                    'autocommit': True,
                }
            })

        # Configure test environment
        settings.configure(
            DATABASES=DATABASES,
            INSTALLED_APPS=(
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.messages',
                'django.contrib.sessions',
                'modeltranslation',
            ),
            ROOT_URLCONF=None,  # tests override urlconf, but it still needs to be defined
            LANGUAGES=(
                ('en', 'English'),
            ),
            TEMPLATE_CONTEXT_PROCESSORS=(
                'django.contrib.messages.context_processors.messages',
            ),
            MIDDLEWARE_CLASSES=(
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
            )
        )

    failures = call_command(
        'test', 'modeltranslation', interactive=False, failfast=False,
        verbosity=2)
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
