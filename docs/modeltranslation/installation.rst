.. _installation:

Installation
============

Requirements
------------

+------------------+------------+-----------+
| Modeltranslation | Python     | Django    |
+==================+============+===========+
| ==0.5            | 2.6 - 2.7  |       1.5 |
|                  +------------+-----------+
|                  | 2.5 - 2.7  | 1.3 - 1.4 |
+------------------+------------+-----------+
| ==0.4            | 2.5 - 2.7  | 1.3 - 1.4 |
+------------------+------------+-----------+
| <=0.3            | 2.4 - 2.7  | 1.0 - 1.4 |
+------------------+------------+-----------+


Using Pip
---------

.. code-block:: console

    $ pip install django-modeltranslation


Using the Source
----------------

Get a source tarball from `github`_ or `pypi`_, unpack, then install with:

.. code-block:: console

    $ python setup.py install

.. note:: As an alternative, if you don't want to mess with any packaging tool,
          unpack the tarball and copy/move the modeltranslation directory
          to a path listed in your ``PYTHONPATH`` environment variable.

.. _github: https://github.com/deschler/django-modeltranslation/downloads
.. _pypi: http://pypi.python.org/pypi/django-modeltranslation/


Setup
=====

To setup the application please follow these steps. Each step is described
in detail in the following sections:

1. Add the ``modeltranslation`` app to the ``INSTALLED_APPS`` variable of your
   project's ``settings.py``.

2. Configure your ``LANGUAGES`` in ``settings.py``.

3. Create a ``translation.py`` in your app directory and register
   ``TranslationOptions`` for every model you want to translate.

4. Sync the database using ``manage.py syncdb`` (note that this only applies
   if the models registered in the ``translations.py`` did not have been
   synced to the database before. If they did - read further down what to do
   in that case.


Configure the Project's ``settings.py``
---------------------------------------

Required Settings
*****************

The following variables have to be added to or edited in the project's
``settings.py``:


``INSTALLED_APPS``
^^^^^^^^^^^^^^^^^^

Make sure that the ``modeltranslation`` app is listed in your
``INSTALLED_APPS`` variable:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'modeltranslation',
        ....
    )


.. _settings-languages:

``LANGUAGES``
^^^^^^^^^^^^^

The ``LANGUAGES`` variable must contain all languages used for translation. The
first language is treated as the *default language*.

The modeltranslation application uses the list of languages to add localized
fields to the models registered for translation. To use the languages ``de``
and ``en`` in your project, set the ``LANGUAGES`` variable like this (where
``de`` is the default language):

.. code-block:: python

    gettext = lambda s: s
    LANGUAGES = (
        ('de', gettext('German')),
        ('en', gettext('English')),
    )

.. note::
    The ``gettext`` lambda function is not a feature of modeltranslation, but
    rather required for Django to be able to (statically) translate the verbose
    names of the languages using the standard ``i18n`` solution.


Advanced Settings
*****************

Modeltranslation also has some advanced settings to customize its behaviour.

.. _settings-modeltranslation_default_language:

``MODELTRANSLATION_DEFAULT_LANGUAGE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.3

Default: ``None``

To override the default language as described in :ref:`settings-languages`,
you can define a language in ``MODELTRANSLATION_DEFAULT_LANGUAGE``. Note that
the value has to be in ``settings.LANGUAGES``, otherwise an
``ImproperlyConfigured`` exception will be raised.

Example:

.. code-block:: python

    MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'


``MODELTRANSLATION_FALLBACK_LANGUAGES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.5

Default: ``(DEFAULT_LANGUAGE,)``

By default modeltranslation will fallback to the computed value of the
``DEFAULT_LANGUAGE``. This is either the first language found in the
``LANGUAGES`` setting or the value defined through
``MODELTRANSLATION_DEFAULT_LANGUAGE`` which acts as an override.

This setting allows for a more fine grained tuning of the fallback behaviour
by taking additional languages into account. The language order is defined as
a tuple or list of language codes.

Example:

.. code-block:: python

    MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'de')

Using a dict syntax it is also possible to define fallbacks by language.
A ``default`` key is required in this case to define the default behaviour
of unlisted languages.

Example:

.. code-block:: python

    MODELTRANSLATION_FALLBACK_LANGUAGES = {'default': ('en', 'de'), 'fr': ('de',)}

.. note::
    Each language has to be in the ``LANGUAGES`` setting, otherwise an
    ``ImproperlyConfigured`` exception is raised.


``MODELTRANSLATION_TRANSLATION_FILES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.4

Default: ``()`` (empty tuple)

Modeltranslation uses an autoregister feature similiar to the one in Django's
admin. The autoregistration process will look for a ``translation.py``
file in the root directory of each application that is in ``INSTALLED_APPS``.

The setting ``MODELTRANSLATION_TRANSLATION_FILES`` is provided to extend the
modules that are taken into account.

Syntax:

.. code-block:: python

    MODELTRANSLATION_TRANSLATION_FILES = (
        '<APP1_MODULE>.translation',
        '<APP2_MODULE>.translation',
    )

Example:

.. code-block:: python

    MODELTRANSLATION_TRANSLATION_FILES = (
        'news.translation',
        'projects.translation',
    )

.. note::
    Modeltranslation up to version 0.3 used a single project wide registration
    file which was defined through
    ``MODELTRANSLATION_TRANSLATION_REGISTRY = '<PROJECT_MODULE>.translation'``.
    For backwards compatibiliy the module defined through this setting is
    automatically added to ``MODELTRANSLATION_TRANSLATION_FILES``. A
    ``DeprecationWarning`` is issued in this case.


``MODELTRANSLATION_CUSTOM_FIELDS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``()`` (empty tuple)

.. versionadded:: 0.3

Modeltranslation supports the fields listed in the
:ref:`supported_field_matrix`. In most cases subclasses of the supported
fields will work fine, too. Unsupported fields will throw an
``ImproperlyConfigured`` exception.

The list of supported fields can be extended by defining a tuple of field
names in your ``settings.py``.

Example:

.. code-block:: python

    MODELTRANSLATION_CUSTOM_FIELDS = ('MyField', 'MyOtherField',)

.. warning::
    This just prevents modeltranslation from throwing an
    ``ImproperlyConfigured`` exception. Any unsupported field will most
    likely fail in one way or another. The feature is considered experimental
    and might be replaced by a more sophisticated mechanism in future versions.


``MODELTRANSLATION_AUTO_POPULATE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``False``

.. versionadded:: 0.5

This setting controls if the :ref:`multilingual_manager` should automatically
populate language field values in its ``create`` method, so that these two
statements can be considered equivalent:

.. code-block:: python

    News.objects.create(title='-- no translation yet --', _populate=True)

.. code-block:: python

    News.objects.create(title='-- no translation yet --')


``MODELTRANSLATION_DEBUG``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``settings.DEBUG``

.. versionadded:: 0.4

Used for modeltranslation related debug output. Currently setting it to
``False`` will just prevent Django's development server from printing the
``Registered xx models for translation`` message to stdout.
