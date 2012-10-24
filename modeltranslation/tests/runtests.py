# -*- coding: utf-8 -*-
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
#test_dir = os.path.join(
#    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests')
#sys.path.insert(0, test_dir)

from django.test.utils import get_runner
from django.conf import settings


def runtests():
    # Potential workaround for 'duplicate column name' error when using
    # travis-ci and different django environments.
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS 'tests';")

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, failfast=False)
    failures = test_runner.run_tests(['modeltranslation'])
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
