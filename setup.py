#!/usr/bin/env python

from distutils.core import setup

setup(name='django-modeltranslation',
      version='0.1',
      description='Translates Django models using a registration approach.',
      author='Peter Eschler',
      author_email='peschler@googlemail.com',
      url='http://code.google.com/p/django-modeltranslation/',
      packages=['modeltranslation', 'modeltranslation.management', 'modeltranslation.management.commands'],
      liicense='New BSD' 
     )
