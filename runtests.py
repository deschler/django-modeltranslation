#!/usr/bin/env python
import os
import sys
import warnings
from optparse import OptionParser

import django
from django.conf import settings
from django.core.management import call_command


def runtests(test_path='modeltranslation'):
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
                'ENGINE': 'django.db.backends.postgresql',
                'USER': 'postgres',
                'NAME': 'modeltranslation',
            })

        # Configure test environment
        settings.configure(
            DATABASES=DATABASES,
            INSTALLED_APPS=(
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'modeltranslation',
            ),
            ROOT_URLCONF=None,  # tests override urlconf, but it still needs to be defined
            LANGUAGES=(
                ('en', 'English'),
            ),
            MIDDLEWARE_CLASSES=(),
        )

    django.setup()
    warnings.simplefilter('always', DeprecationWarning)
    failures = call_command(
        'test', test_path, interactive=False, failfast=False, verbosity=2)

    sys.exit(bool(failures))


if __name__ == '__main__':
    parser = OptionParser()

    (options, args) = parser.parse_args()
    runtests(*args)
