#!/usr/bin/env python
from distutils.core import setup

# Dynamically calculate the version based on modeltranslation.VERSION.
version = __import__('modeltranslation').get_version()


setup(
    name='django-modeltranslation',
    version=version,
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
    requires=['Django(>=1.11)'],
    download_url='https://github.com/deschler/django-modeltranslation/archive/%s.tar.gz' % version,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License'],
    license='New BSD')
