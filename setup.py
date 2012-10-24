#!/usr/bin/env python
from distutils.core import setup


setup(
    name='django-modeltranslation',
    version='0.4.0-beta2',
    description='Translates Django models using a registration approach.',
    long_description=(
        'The modeltranslation application can be used to translate dynamic '
        'content of existing models to an arbitrary number of languages '
        'without having to change the original model classes. It uses a '
        'registration approach (comparable to Django\'s admin app) to be able '
        'to add translations to existing or new projects and is fully '
        'integrated into the Django admin backend.'),
    author='Peter Eschler',
    author_email='peschler@gmail.com',
    maintainer='Dirk Eschler',
    maintainer_email='eschler@gmail.com',
    url='https://github.com/deschler/django-modeltranslation',
    packages=['modeltranslation', 'modeltranslation.management',
              'modeltranslation.management.commands'],
    package_data={'modeltranslation': ['static/modeltranslation/css/*.css',
                                       'static/modeltranslation/js/*.js']},
    requires=['django(>=1.2)'],
    download_url='https://github.com/downloads/deschler/django-modeltranslation/django-modeltranslation-0.4.0-beta2.tar.gz',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License'],
    license='New BSD')
