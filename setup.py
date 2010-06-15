#!/usr/bin/env python

from distutils.core import setup

setup(name='django-modeltranslation',
      version='0.2',
      description='Translates Django models using a registration approach.',
      author='Peter Eschler, Dirk Eschler',
      author_email='peschler@googlemail.com, eschler@gmail.com',
      url='http://code.google.com/p/django-modeltranslation/',
      packages=['modeltranslation', 'modeltranslation.management',
                'modeltranslation.management.commands'],
      license='New BSD')
