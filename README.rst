================
Modeltranslation
================

The modeltranslation application can be used to translate dynamic content of
existing Django models to an arbitrary number of languages without having to
change the original model classes. It uses a registration approach (comparable
to Django's admin app) to be able to add translations to existing or new
projects and is fully integrated into the Django admin backend.

The advantage of a registration approach is the ability to add translations to
models on a per-app basis. You can use the same app in different projects,
may they use translations or not, and you never have to touch the original
model class.


.. image:: https://travis-ci.org/deschler/django-modeltranslation.png?branch=master
    :target: https://travis-ci.org/deschler/django-modeltranslation


Features
========

- Add translations without changing existing models
- Fast, because translation fields are stored in the same table
- Supports inherited models
- Django admin support
- Unlimited number of target languages


Project Home
------------
https://github.com/deschler/django-modeltranslation

Documentation
-------------
https://django-modeltranslation.readthedocs.org/en/latest/

Mailing List
------------
http://groups.google.com/group/django-modeltranslation
