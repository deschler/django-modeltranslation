.. _installation:

Installation
============

Requirements
------------

Which Modeltranslation version is required for given Django-Python combination to work?

======= ==== ==== ==== ==== ==== ==== ==== ==== ====
Python  Django
------- --------------------------------------- ----
version 1.8  1.9  1.10 1.11 2.0  2.1  2.2  3.0  3.2
======= ==== ==== ==== ==== ==== ==== ==== ==== ====
2.7     |9|  |11| |12| |13|
3.2     |9|
3.3     |9|
3.4     |9|  |11| |12| |13| |13|
3.5     |9|  |11| |12| |13| |13| |13|
3.6                    |13| |13| |13| |15| |15| |17|
3.7                         |13| |13| |15| |15| |17|
3.8                         |13| |13| |15| |15| |17|
3.9                         |13| |13| |15| |15| |17|
======= ==== ==== ==== ==== ==== ==== ==== ==== ====

(``-X`` denotes "up to version X", whereas ``X+`` means "from version X upwards")

.. |9|  replace:: 0.9+
.. |11| replace:: 0.11+
.. |12| replace:: 0.12+
.. |13| replace:: 0.13+
.. |15| replace:: 0.15+
.. |17| replace:: 0.17+

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

1. Add ``modeltranslation`` to the ``INSTALLED_APPS`` variable of your
   project's ``settings.py``.

2. Set ``USE_I18N = True`` in ``settings.py``.

3. Configure your ``LANGUAGES`` in ``settings.py``.

4. Create a ``translation.py`` in your app directory and register
   ``TranslationOptions`` for every model you want to translate.

5. Sync the database using ``python manage.py makemigrations`` and ``python manage.py migrate``.

   .. note:: This only applies if the models registered in ``translation.py`` haven't been
             synced to the database before. If they have, please read :ref:`db-fields`.

   .. note:: If you are using Django 1.7 and its internal migration system, run
             ``python manage.py makemigrations``, followed by
             ``python manage.py migrate`` instead. See :ref:`migrations` for details.


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
        'django.contrib.admin',  # optional
        ....
    )

.. important::
    If you want to use the admin integration, ``modeltranslation`` must be put
    before ``django.contrib.admin`` (only applies when using Django 1.7 or
    above).

.. important::
    If you want to use the ``django-debug-toolbar`` together with modeltranslation, use `explicit setup
    <http://django-debug-toolbar.readthedocs.org/en/latest/installation.html#explicit-setup>`_.
    Otherwise tweak the order of ``INSTALLED_APPS``: try to put ``debug_toolbar`` as first entry in
    ``INSTALLED_APPS`` (in Django < 1.7) or after ``modeltranslation`` (in Django >= 1.7). However,
    only `explicit setup` is guaranteed to succeed.

.. _settings-languages:

``LANGUAGES``
^^^^^^^^^^^^^

The ``LANGUAGES`` variable must contain all languages used for translation. The
first language is treated as the *default language*.

Modeltranslation uses the list of languages to add localized fields to the
models registered for translation. To use the languages ``de`` and ``en`` in
your project, set the ``LANGUAGES`` variable like this (where ``de`` is the
default language)::

    gettext = lambda s: s
    LANGUAGES = (
        ('de', gettext('German')),
        ('en', gettext('English')),
    )

.. note::
    The ``gettext`` lambda function is not a feature of modeltranslation, but
    rather required for Django to be able to (statically) translate the verbose
    names of the languages using the standard ``i18n`` solution.

.. note::
    If, for some reason, you don't want to translate objects to exactly the same languages as
    the site would be displayed into, you can set ``MODELTRANSLATION_LANGUAGES`` (see below).
    For any language in ``LANGUAGES`` not present in ``MODELTRANSLATION_LANGUAGES``, the *default
    language* will be used when accessing translated content. For any language in
    ``MODELTRANSLATION_LANGUAGES`` not present in ``LANGUAGES``, probably nobody will see translated
    content, since the site wouldn't be accessible in that language.

.. warning::
    Modeltranslation does not enforce the ``LANGUAGES`` setting to be defined
    in your project. When it isn't present (and neither is ``MODELTRANSLATION_LANGUAGES``), it
    defaults to Django's
    `global LANGUAGES setting <https://github.com/django/django/blob/master/django/conf/global_settings.py>`_
    instead, and that are quite a few languages!


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


``MODELTRANSLATION_LANGUAGES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.8

Default: same as ``LANGUAGES``

Allow to set languages the content will be translated into. If not set, by default all
languages listed in ``LANGUAGES`` will be used.

Example::

    LANGUAGES = (
        ('en', 'English'),
        ('de', 'German'),
        ('pl', 'Polish'),
    )
    MODELTRANSLATION_LANGUAGES = ('en', 'de')

.. note::
    This setting may become useful if your users shall produce content for a restricted
    set of languages, while your application is translated into a greater number of locales.


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


.. _settings-modeltranslation_prepopulate_language:

``MODELTRANSLATION_PREPOPULATE_LANGUAGE``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.7

Default: ``current active language``

By default modeltranslation will use the current request language for prepopulating
admin fields specified in the ``prepopulated_fields`` admin property. This is often
used to automatically fill slug fields.

This setting allows you to pin this functionality to a specific language.

Example::

    MODELTRANSLATION_PREPOPULATE_LANGUAGE = 'en'

.. note::
    The language has to be in the ``LANGUAGES`` setting, otherwise an
    ``ImproperlyConfigured`` exception is raised.


``MODELTRANSLATION_TRANSLATION_FILES``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 0.4

Default: ``()`` (empty tuple)

Modeltranslation uses an autoregister feature similar to the one in Django's
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

    In version 0.4 and 0.5, for backwards compatibility, the module defined through this setting was
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
