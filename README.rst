==============
War in Ukraine
==============

On February 24th, 2022, Russia invaded Ukraine. I'm sole maintainer of this project
staying in safe place, but i don't know how long it would be safe.

Russian military shelling our cities, targeting civilian population.

Help Ukraine:

- https://supportukrainenow.org/

Talk to your politics, talk to your friends. Send heavy weapons to Ukraine. Close the sky.

----------------

================
Modeltranslation
================


.. image:: http://img.shields.io/coveralls/deschler/django-modeltranslation.svg?style=flat-square
    :target: https://coveralls.io/r/deschler/django-modeltranslation

.. image:: https://img.shields.io/pypi/v/django-modeltranslation.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-modeltranslation/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/pyversions/django-modeltranslation.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-modeltranslation/
    :alt: Supported Python versions

.. image:: https://img.shields.io/gitter/room/django-modeltranslation/community?color=4DB798&style=flat-square
    :alt: Join the chat at https://gitter.im/django-modeltranslation/community
    :target: https://gitter.im/django-modeltranslation/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge



The modeltranslation application is used to translate dynamic content of
existing Django models to an arbitrary number of languages without having to
change the original model classes. It uses a registration approach (comparable
to Django's admin app) to be able to add translations to existing or new
projects and is fully integrated into the Django admin backend.

The advantage of a registration approach is the ability to add translations to
models on a per-app basis. You can use the same app in different projects,
may they use translations or not, and you never have to touch the original
model class.

Features
========

- Add translations without changing existing models or views
- Translation fields are stored in the same table (no expensive joins)
- Supports inherited models (abstract and multi-table inheritance)
- Handle more than just text fields
- Django admin integration
- Flexible fallbacks, auto-population and more!

For the latest documentation, visit https://django-modeltranslation.readthedocs.io/en/latest/.
