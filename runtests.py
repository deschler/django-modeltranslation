#!/usr/bin/env python
import os
import sys

from django.core.management import call_command

os.environ['DJANGO_SETTINGS_MODULE'] = 'modeltranslation.tests.settings'

def runtests():
    failures = call_command(
        'test', 'modeltranslation', interactive=False, failfast=False,
        verbosity=2)
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
