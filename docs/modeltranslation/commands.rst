.. _commands:

Management Commands
===================

.. _commands-update_translation_fields:

The ``update_translation_fields`` Command
-----------------------------------------

In case the modeltranslation app was installed on an existing project and you
have specified to translate fields of models which are already synced to the
database, you have to update your database schema (see :ref:`db-fields`).

Unfortunately the newly added translation fields on the model will be empty
then, and your templates will show the translated value of the fields (see
Rule 1) which will be empty in this case. To correctly initialize the
default translation field you can use the ``update_translation_fields``
command:

.. code-block:: console

    $ ./manage.py update_translation_fields

Taken the news example used throughout the documentation this command will copy
the value from the news object's ``title`` field to the default translation
field ``title_de``. It only does so if the default translation field is empty
otherwise nothing is copied.

.. note::

    Unless you configured modeltranslation to
    :ref:`override the default language <settings-modeltranslation_default_language>`
    the command will examine your ``settings.LANGUAGES`` variable and the first
    language declared there will be used as the default language.

All translated models (as specified in the translation files) from all apps will be
populated with initial data.


.. _commands-sync_translation_fields:

The ``sync_translation_fields`` Command
---------------------------------------

.. versionadded:: 0.4

.. code-block:: console

    $ ./manage.py sync_translation_fields

This command compares the database and translated models definitions (finding new translation
fields) and provides SQL statements to alter tables. You should run this command after adding
new language or deciding to translate new field in a ``TranslationOptions``.

However, if you are using South in your project, in most cases it's recommended to use migration
instead of ``sync_translation_fields``. See :ref:`db-fields` for detailed info and use cases.


The ``loaddata`` Command
------------------------

.. versionadded:: 0.7

It is just extension to original ``loaddata`` command which adds an optional ``populate`` keyword.
If specified, then normal loading command will be run under selected auto-population modes.

By default no auto-population is performed.

.. code-block:: console

    $ ./manage.py loaddata --populate=all fixtures.json

Allowed modes are listed :ref:`here <auto-population-modes>`. To choose ``False``
(turn off auto-population) specify ``'0'`` or ``'false'``:

.. code-block:: console

    $ ./manage.py loaddata --populate=false fixtures.json
    $ ./manage.py loaddata --populate=0 fixtures.json

.. note::

    If ``populate`` is not specified, then current auto-population mode is used. *Current* means
    the one set by :ref:`settings <settings-modeltranslation_auto_populate>`.

Moreover, this ``loaddata`` command version can override the nasty habit of changing locale to
`en-us`. By default, it will retain proper locale. To get back to old behaviour, set
:ref:`settings-modeltranslation_loaddata_retain_locale` to ``False``.
