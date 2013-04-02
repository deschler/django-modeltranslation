.. _installation:

Installation
============

Requirements
------------

+------------------+------------+-----------+
| Modeltranslation | Python     | Django    |
+==================+============+===========+
| >=0.5            | 2.6 - 2.7  |       1.5 |
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

Get a source tarball from `pypi`_, unpack, then install with:

.. code-block:: console

    $ python setup.py install

.. note:: As an alternative, if you don't want to mess with any packaging tool,
          unpack the tarball and copy/move the modeltranslation directory
          to a path listed in your ``PYTHONPATH`` environment variable.

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
   if the models registered in the ``translation.py`` did not have been
   synced to the database before. If they did - read further down what to do
   in that case.


Configuration
=============

Required Settings
-----------------

The following variables have to be added to or edited in the project's
``settings.py``:


``INSTALLED_APPS``
^^^^^^^^^^^^^^^^^^

Make sure that the ``modeltranslation`` app is listed in your
``INSTALLED_APPS`` variable::

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
``de`` is the default language)::

    gettext = lambda s: s
    LANGUAGES = (
        ('de', gettext('German')),
        ('en', gettext('English')),
    )

.. note::
    The ``gettext`` lambda function is not a feature of modeltranslation, but
    rather required for Django to be able to (statically) translate the verbose
    names of the languages using the standard ``i18n`` solution.

.. warning::
    Modeltranslation does not enforce the ``LANGUAGES`` setting to be defined
    in your project. When it isn't present, it defaults to Django's
    `global LANGUAGES setting <https://github.com/django/django/blob/master/django/conf/global_settings.py>`_
    instead, and that are quite a number of languages!


Advanced Settings
-----------------

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

Example::

    MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'


.. _settings-modeltranslation_fallback_languages:

``MODELTRANSLATION_FALLBACK_LANGUAGES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.5

Default: ``(DEFAULT_LANGUAGE,)``

By default modeltranslation will :ref:`fallback <fallback>` to the computed value of the
``DEFAULT_LANGUAGE``. This is either the first language found in the
``LANGUAGES`` setting or the value defined through
``MODELTRANSLATION_DEFAULT_LANGUAGE`` which acts as an override.

This setting allows for a more fine grained tuning of the fallback behaviour
by taking additional languages into account. The language order is defined as
a tuple or list of language codes.

Example::

    MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'de')

Using a dict syntax it is also possible to define fallbacks by language.
A ``default`` key is required in this case to define the default behaviour
of unlisted languages.

Example::

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

Syntax::

    MODELTRANSLATION_TRANSLATION_FILES = (
        '<APP1_MODULE>.translation',
        '<APP2_MODULE>.translation',
    )

Example::

    MODELTRANSLATION_TRANSLATION_FILES = (
        'news.translation',
        'projects.translation',
    )

.. note::
    Modeltranslation up to version 0.3 used a single project wide registration
    file which was defined through
    ``MODELTRANSLATION_TRANSLATION_REGISTRY = '<PROJECT_MODULE>.translation'``.

    In version 0.4 and 0.5, for backwards compatibiliy, the module defined through this setting was
    automatically added to ``MODELTRANSLATION_TRANSLATION_FILES``. A
    ``DeprecationWarning`` was issued in this case.

    In version 0.6 ``MODELTRANSLATION_TRANSLATION_REGISTRY`` is handled no more.


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

Example::

    MODELTRANSLATION_CUSTOM_FIELDS = ('MyField', 'MyOtherField',)

.. warning::
    This just prevents modeltranslation from throwing an
    ``ImproperlyConfigured`` exception. Any unsupported field will most
    likely fail in one way or another. The feature is considered experimental
    and might be replaced by a more sophisticated mechanism in future versions.


.. _settings-modeltranslation_auto_populate:

``MODELTRANSLATION_AUTO_POPULATE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``False``

.. versionadded:: 0.5

This setting controls if the :ref:`multilingual_manager` should automatically
populate language field values in its ``create`` and ``get_or_create`` method, and in model
constructors, so that these two blocks of statements can be considered equivalent::

    News.objects.populate(True).create(title='-- no translation yet --')
    with auto_populate(True):
        q = News(title='-- no translation yet --')

    # same effect with MODELTRANSLATION_AUTO_POPULATE == True:

    News.objects.create(title='-- no translation yet --')
    q = News(title='-- no translation yet --')

Possible modes are listed :ref:`here <auto-population-modes>`.


``MODELTRANSLATION_DEBUG``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``False``

.. versionadded:: 0.4
.. versionchanged:: 0.7

Used for modeltranslation related debug output. Currently setting it to
``False`` will just prevent Django's development server from printing the
``Registered xx models for translation`` message to stdout.


``MODELTRANSLATION_ENABLE_FALLBACKS``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default: ``True``

.. versionadded:: 0.6

Control if :ref:`fallback <fallback>` (both language and value) will occur.
