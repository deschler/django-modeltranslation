.. _registration:

Registering Models for Translation
==================================

Modeltranslation can translate model fields of any model class. For each model
to translate a translation option class containing the fields to translate is
registered with a special object called the ``translator``.

Registering models and their fields for translation requires the following
steps:

1. Create a ``translation.py`` in your app directory.
2. Create a translation option class for every model to translate.
3. Register the model and the translation option class at the
   ``modeltranslation.translator.translator``.

The modeltranslation application reads the ``translation.py`` file in your
app directory thereby triggering the registration of the translation
options found in the file.

A translation option is a class that declares which fields of a model to
translate. The class must derive from
``modeltranslation.translator.TranslationOptions`` and it must provide a
``fields`` attribute storing the list of fieldnames. The option class must be
registered with the ``modeltranslation.translator.translator`` instance.

To illustrate this let's have a look at a simple example using a ``News``
model. The news in this example only contains a ``title`` and a ``text`` field.
Instead of a news, this could be any Django model class::

    class News(models.Model):
        title = models.CharField(max_length=255)
        text = models.TextField()

In order to tell the modeltranslation app to translate the ``title`` and
``text`` field, create a ``translation.py`` file in your news app directory and
add the following::

    from modeltranslation.translator import translator, TranslationOptions
    from news.models import News

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)

    translator.register(News, NewsTranslationOptions)

Note that this does not require to change the ``News`` model in any way, it's
only imported. The ``NewsTranslationOptions`` derives from
``TranslationOptions`` and provides the ``fields`` attribute. Finally the model
and its translation options are registered at the ``translator`` object.

At this point you are mostly done and the model classes registered for
translation will have been added some auto-magical fields. The next section
explains how things are working under the hood.


.. _TO_field_inheritance:

``TranslationOptions`` fields inheritance
-----------------------------------------

.. versionadded:: 0.5

A subclass of any ``TranslationOptions`` will inherit fields from its bases
(similar to the way Django models inherit fields, but with a different syntax). ::

    from modeltranslation.translator import translator, TranslationOptions
    from news.models import News, NewsWithImage

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)

    class NewsWithImageTranslationOptions(NewsTranslationOptions):
        fields = ('image',)

    translator.register(News, NewsTranslationOptions)
    translator.register(NewsWithImage, NewsWithImageTranslationOptions)

The above example adds the fields ``title`` and ``text`` from the
``NewsTranslationOptions`` class to ``NewsWithImageTranslationOptions``, or to
say it in code::

    assert NewsWithImageTranslationOptions.fields == ('title', 'text', 'image')

Of course multiple inheritance and inheritance chains (A > B > C) also work as
expected.

.. note:: When upgrading from a previous modeltranslation version, please
    review your ``TranslationOptions`` classes and see if introducing `fields
    inheritance` broke the project (if you had always subclassed
    ``TranslationOptions`` only, there is no risk).


Changes Automatically Applied to the Model Class
------------------------------------------------

After registering the ``News`` model for translation a SQL dump of the news
app will look like this:

.. code-block:: console

    $ ./manage.py sqlall news
    BEGIN;
    CREATE TABLE `news_news` (
        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `title` varchar(255) NOT NULL,
        `title_de` varchar(255) NULL,
        `title_en` varchar(255) NULL,
        `text` longtext NULL,
        `text_de` longtext NULL,
        `text_en` longtext NULL,
    )
    ;
    CREATE INDEX `news_news_page_id` ON `news_news` (`page_id`);
    COMMIT;

Note the ``title_de``, ``title_en``, ``text_de`` and ``text_en`` fields which
are not declared in the original ``News`` model class but rather have been
added by the modeltranslation app. These are called *translation fields*. There
will be one for every language in your project's ``settings.py``.

The name of these additional fields is build using the original name of the
translated field and appending one of the language identifiers found in the
``settings.LANGUAGES``.

As these fields are added to the registered model class as fully valid Django
model fields, they will appear in the db schema for the model although it has
not been specified on the model explicitly.

.. _register-precautions:

Precautions regarding registration approach
*******************************************

Be aware that registration approach (as opposed to base-class approach) to
models translation has a few caveats, though (despite many pros).

First important thing to note is the fact that translatable models are being patched - that means
their fields list is not final until the `MT` code executes. In normal circumstances it shouldn't
affect anything - as long as ``models.py`` contain only models' related code.

For example: consider a project when a ``ModelForm`` is declared in ``models.py`` just after
its model. When the file is executed, the form gets prepared - but it will be frozen with
old fields list (without translation fields). That's because ``ModelForm`` will be created before
`MT` would add new fields to the model (``ModelForm`` gather fields info at class creation time, not
instantiation time). Proper solution is to define the form in ``forms.py``, which wouldn't be
imported alongside with ``models.py`` (and rather imported from views file or urlconf).

Generally, for seamless integration with `MT` (and as sensible design, anyway),
the ``models.py`` should contain only bare models and model related logic.

.. _db-fields:

Committing fields to database
*****************************

If you are starting a fresh project and have considered your translation needs
in the beginning then simply sync your database (``./manage.py syncdb`` or
``./manage.py schemamigration myapp --initial`` if using South)
and you are ready to use the translated models.

In case you are translating an existing project and your models have already
been synced to the database you will need to alter the tables in your database
and add these additional translation fields. If you are using South, you're
done: simply create a new migration (South will detect newly added translation
fields) and apply it. If not, you can use a little helper:
:ref:`commands-sync_translation_fields` which can execute schema-ALTERing SQL
to add new fields. Use either of these two solutions, not both.

If you are adding translation fields to third-party app that is using South,
things get more complicated. In order to be able to update the app in future,
and to feel comfortable, you should use the ``sync_translation_fields`` command.
Although it's possible to introduce new fields in a migration, it's nasty and
involves copying migration files, using ``SOUTH_MIGRATION_MODULES`` setting,
and passing ``--delete-ghost-migrations`` flag, so we don't recommend it.
Invoking ``sync_translation_fields`` is plain easier.

Note that all added fields are by default
declared ``blank=True`` and ``null=True`` no matter if the original field is
required or not. In other words - all translations are optional, unless an explicit option
is provided - see below.

To populate the default translation fields added by the modeltranslation application
with values from existing database fields, you
can use the ``update_translation_fields`` command below. See
:ref:`commands-update_translation_fields` for more info on this.


.. _required_langs:

Required fields
---------------

By default, all translation fields are optional (not required). It can be changed using special
attribute on ``TranslationOptions``, though::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        required_languages = ('en', 'de')

It quite self-explanatory: for German and English, all translation fields are required. For other
languages - optional.

A more fine-grained control is available::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        required_languages = {'de': ('title', 'text'), 'default': ('title',)}

For German, all fields (both ``title`` and ``text``) are required; for all other languages - only
``title`` is required. The ``'default'`` is optional.

.. note::
    Requirement is enforced by ``blank=False``. Please remember that it will trigger validation only
    in modelforms and admin (as always in Django). Manual model validation can be performed via
    ``full_clean()`` model method.

    The required fields are still ``null=True``, though.


``TranslationOptions`` attributes reference
-------------------------------------------

Quick cheatsheet with links to proper docs sections and examples showing expected syntax.

Classes inheriting from ``TranslationOptions`` can have following attributes defined:

.. attribute:: TranslationOptions.fields (required)

    List of translatable model fields. See :ref:`registration`.

    Some fields can be implicitly added through inheritance, see :ref:`TO_field_inheritance`.

.. attribute:: TranslationOptions.fallback_languages

    Control order of languages for fallback purposes. See :ref:`fallback_lang`. ::

        fallback_languages = {'default': ('en', 'de', 'fr'), 'uk': ('ru',)}

.. attribute:: TranslationOptions.fallback_values

    Set the value that should be used if no fallback language yielded a value.
    See :ref:`fallback_val`. ::

        fallback_values = _('-- sorry, no translation provided --')
        fallback_values = {'title': _('Object not translated'), 'text': '---'}

.. attribute:: TranslationOptions.fallback_undefined

    Set what value should be considered "no value". See :ref:`fallback_undef`. ::

        fallback_undefined = None
        fallback_undefined = {'title': 'no title', 'text': None}

.. attribute:: TranslationOptions.empty_values

    Override the value that should be saved in forms on empty fields.
    See :ref:`formfield_nullability`. ::

        empty_values = ''
        empty_values = {'title': '', 'slug': None, 'desc': 'both'}

.. attribute:: TranslationOptions.required_languages

    Control which translation fields are required. See :ref:`required_langs`. ::

        required_languages = ('en', 'de')
        required_languages = {'de': ('title','text'), 'default': ('title',)}


.. _supported_field_matrix:

Supported Fields Matrix
-----------------------

While the main purpose of modeltranslation is to translate text-like fields,
translating other fields can be useful in several situations. The table lists
all model fields available in Django and gives an overview about their current
support status:

=============================== === === ===
Model Field                     0.4 0.5 0.7
=============================== === === ===
``AutoField``                   |n| |n| |n|
``BigIntegerField``             |n| |i| |i|
``BooleanField``                |n| |y| |y|
``CharField``                   |y| |y| |y|
``CommaSeparatedIntegerField``  |n| |y| |y|
``DateField``                   |n| |y| |y|
``DateTimeField``               |n| |y| |y|
``DecimalField``                |n| |y| |y|
``EmailField``                  |i| |i| |i|
``FileField``                   |y| |y| |y|
``FilePathField``               |i| |i| |i|
``FloatField``                  |n| |y| |y|
``ImageField``                  |y| |y| |y|
``IntegerField``                |n| |y| |y|
``IPAddressField``              |n| |y| |y|
``GenericIPAddressField``       |n| |y| |y|
``NullBooleanField``            |n| |y| |y|
``PositiveIntegerField``        |n| |i| |i|
``PositiveSmallIntegerField``   |n| |i| |i|
``SlugField``                   |i| |i| |i|
``SmallIntegerField``           |n| |i| |i|
``TextField``                   |y| |y| |y|
``TimeField``                   |n| |y| |y|
``URLField``                    |i| |i| |i|
``ForeignKey``                  |n| |n| |y|
``OneToOneField``               |n| |n| |y|
``ManyToManyField``             |n| |n| |n|
=============================== === === ===

.. |y| replace:: Yes
.. |i| replace:: Yes\*
.. |n| replace:: No
.. |u| replace:: ?

\* Implicitly supported (as subclass of a supported field)
