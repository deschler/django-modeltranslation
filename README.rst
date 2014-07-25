================
Modeltranslation
================

The modeltranslation application is used to translate dynamic content of
existing Django models to an arbitrary number of languages without having to
change the original model classes. It uses a registration approach (comparable
to Django's admin app) to be able to add translations to existing or new
projects and is fully integrated into the Django admin backend.

The advantage of a registration approach is the ability to add translations to
models on a per-app basis. You can use the same app in different projects,
may they use translations or not, and you never have to touch the original
model class.


.. image:: http://img.shields.io/travis/deschler/django-modeltranslation/master.png?style=flat
    :target: https://travis-ci.org/deschler/django-modeltranslation

.. image:: http://img.shields.io/coveralls/deschler/django-modeltranslation.png?style=flat
    :target: https://coveralls.io/r/deschler/django-modeltranslation

.. image:: https://pypip.in/v/django-modeltranslation/badge.png?style=flat
    :target: https://pypi.python.org/pypi/django-modeltranslation/
    :alt: Latest PyPI version

.. image:: https://pypip.in/py_versions/django-modeltranslation/badge.png?style=flat
    :target: https://pypi.python.org/pypi/django-modeltranslation/
    :alt: Supported Python versions

.. image:: https://pypip.in/d/django-modeltranslation/badge.png?style=flat
    :target: https://pypi.python.org/pypi/django-modeltranslation/
    :alt: Number of PyPI downloads


Features
========

- Add translations without changing existing models or views
- Translation fields are stored in the same table (no expensive joins)
- Supports inherited models (abstract and multi-table inheritance)
- Handle more than just text fields
- Django admin integration
- Flexible fallbacks, auto-population and more!


Project Home
------------
https://github.com/deschler/django-modeltranslation

Documentation
-------------
https://django-modeltranslation.readthedocs.org/en/latest

Mailing List
------------
http://groups.google.com/group/django-modeltranslation
