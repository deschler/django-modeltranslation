#!/usr/bin/env python
import os
import shutil
import sys

import django
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
            })
            if django.VERSION < (1, 6):
                DATABASES['default']['OPTIONS'] = {'autocommit': True}

        # Configure test environment
        settings.configure(
            DATABASES=DATABASES,
            INSTALLED_APPS=(
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'modeltranslation',
            ),
            MIGRATION_MODULES={
                'auth': 'modeltranslation.tests.auth_migrations',
            },
            ROOT_URLCONF=None,  # tests override urlconf, but it still needs to be defined
            LANGUAGES=(
                ('en', 'English'),
            ),
            MIDDLEWARE_CLASSES=(),
        )

    # Copy django.contrib.auth.migrations to a writable path
    dj_auth_migrations_dir = os.path.join(os.path.dirname(django.__file__),
                                          'contrib', 'auth', 'migrations')
    auth_migrations_dir = os.path.join('modeltranslation', 'tests',
                                       'auth_migrations')
    if os.path.exists(dj_auth_migrations_dir):
        if os.path.isdir(auth_migrations_dir):
            shutil.rmtree(auth_migrations_dir)
        shutil.copytree(dj_auth_migrations_dir, auth_migrations_dir)

    if django.VERSION >= (1, 7):
        django.setup()
    failures = call_command(
        'test', 'modeltranslation', interactive=False, failfast=False, verbosity=2)

    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
