#!/usr/bin/env python
from distutils.core import setup

setup(name='django-modeltranslation',
      version='0.2',
      description='Translates Django models using a registration approach.',
      long_description='The modeltranslation application can be used to '
                       'translate dynamic content of existing models to an '
                       'arbitrary number of languages without having to '
                       'change the original model classes. It uses a '
                       'registration approach (comparable to Django\'s admin '
                       'app) to be able to add translations to existing or '
                       'new projects and is fully integrated into the Django '
                       'admin backend.',
      author='Peter Eschler',
      author_email='p.eschler@nmy.de',
      maintainer='Dirk Eschler',
      maintainer_email='d.eschler@nmy.de',
      url='http://code.google.com/p/django-modeltranslation/',
      packages=['modeltranslation', 'modeltranslation.management',
                'modeltranslation.management.commands'],
      requires=['django(>=1.0)'],
      download_url='http://django-modeltranslation.googlecode.com/files/django-modeltranslation-0.2.tar.gz',
      classifiers=['Framework :: Django',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License'],
      license='New BSD')
