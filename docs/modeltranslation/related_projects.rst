.. _related_projects:

Related Projects
================

.. note:: This list is horribly outdated and only covers apps that where
          available when modeltranslation was initially developed. A more
          complete list can be found at `djangopackages.com`_.


`django-multilingual`_
----------------------

    A library providing support for multilingual content in Django models.

It is not possible to reuse existing models without modifying them.


`django-multilingual-model`_
----------------------------

    A much simpler version of the above `django-multilingual`.

It works very similar to the `django-multilingual` approach.


`transdb`_
----------

    Django's field that stores labels in more than one language in database.

This approach uses a specialized ``Field`` class, which means one has to change
existing models.


`i18ndynamic`_
--------------

This approach is not developed any more.


`django-pluggable-model-i18n`_
------------------------------

    This app utilizes a new approach to multilingual models based on the same
    concept the new admin interface uses. A translation for an existing model
    can be added by registering a translation class for that model.

This is more or less what modeltranslation does, unfortunately it is far
from being finished.


.. _djangopackages.com: http://www.djangopackages.com/grids/g/model-translation/
.. _django-multilingual: http://code.google.com/p/django-multilingual/
.. _django-multilingual-model: http://code.google.com/p/django-multilingual-model/
.. _django-transdb: http://code.google.com/p/transdb/
.. _i18ndynamic: http://code.google.com/p/i18ndynamic/
.. _django-pluggable-model-i18n: http://code.google.com/p/django-pluggable-model-i18n/
