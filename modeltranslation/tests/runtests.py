# -*- coding: utf-8 -*-
import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

#from django.test.simple import DjangoTestSuiteRunner
#from django.test.utils import get_runner
#from django.conf import settings
from django.core.management import call_command


def runtests():
#    #TestRunner = get_runner(settings)
#    #test_runner = TestRunner(verbosity=2, failfast=False)
#    #failures = test_runner.run_tests(['modeltranslation'])
#    failures = DjangoTestSuiteRunner(
#        verbosity=2, failfast=False).run_tests(['modeltranslation'])
#    sys.exit(bool(failures))
    # FIXME: Debugging drop tables when running on travis-ci
    from django.db import connection
    cursor = connection.cursor()
    tables = ['tests_testmodelwithfallback', 'tests_testmodelwithfallback2',
              'tests_testmodelwithfilefields', 'tests_testmodelmultitablea',
              'tests_testmodelmultitableb', 'tests_testmodelmultitablec',
              'tests_testmodelmultitabled', 'tests_testmodelabstractb',
              'tests_datamodel']
    for table in tables:
        try:
            cursor.execute("DROP TABLE %s" % table)
        except Exception, e:
            print "DROP TABLE %s: %s" % (table, e)

    failures = call_command(
        'test', 'modeltranslation', interactive=False, failfast=False,
        verbosity=2)
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
