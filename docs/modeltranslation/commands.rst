.. _commands:

Management Commands
===================

.. _commands-update_translation_fields:

The ``update_translation_fields`` Command
-----------------------------------------

In case the modeltranslation app was installed on an existing project and you
have specified to translate fields of models which are already synced to the
database, you have to update your database schema manually.

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

All translated models (as specified in the project's ``translation.py`` will be
populated with initial data.


The ``sync_translation_fields`` Command
---------------------------------------

.. versionadded:: 0.4

.. code-block:: console

    $ ./manage.py sync_translation_fields

.. todo:: Explain
