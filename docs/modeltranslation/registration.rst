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
Instead of a news, this could be any Django model class:

.. code-block:: python

    class News(models.Model):
        title = models.CharField(max_length=255)
        text = models.TextField()

In order to tell the modeltranslation app to translate the ``title`` and
``text`` field, create a ``translation.py`` file in your news app directory and
add the following:

.. code-block:: python

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


``TranslationOptions`` fields inheritance
-----------------------------------------

.. versionadded:: 0.5

A subclass of any ``TranslationOptions`` will inherit fields from its bases
(similar to the way Django models inherit fields, but with a different syntax).

.. code-block:: python

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
say it in code:

.. code-block:: python

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

If you are starting a fresh project and have considered your translation needs
in the beginning then simply sync your database and you are ready to use
the translated models.

In case you are translating an existing project and your models have already
been synced to the database you will need to alter the tables in your database
and add these additional translation fields. Note that all added fields are
declared ``blank=True`` and ``null=True`` no matter if the original field is
required or not. In other words - all translations are optional. To populate
the default translation fields added by the modeltranslation application you
can use the ``update_translation_fields`` command below. See
:ref:`commands-update_translation_fields` for more infos on this.


.. _supported_field_matrix:

Supported Fields Matrix
-----------------------

While the main purpose of modeltranslation is to translate text-like fields,
translating other fields can be useful in several situations. The table lists
all model fields available in Django and gives an overview about their current
support status:

=============================== === ===
Model Field                     0.4 0.5
=============================== === ===
``AutoField``                   |n| |n|
``BigIntegerField``             |n| |i|
``BooleanField``                |n| |y|
``CharField``                   |y| |y|
``CommaSeparatedIntegerField``  |n| |y|
``DateField``                   |n| |y|
``DateTimeField``               |n| |y|
``DecimalField``                |n| |y|
``EmailField``                  |i| |i|
``FileField``                   |y| |y|
``FilePathField``               |i| |i|
``FloatField``                  |n| |y|
``ImageField``                  |y| |y|
``IntegerField``                |n| |y|
``IPAddressField``              |n| |y|
``GenericIPAddressField``       |n| |y|
``NullBooleanField``            |n| |y|
``PositiveIntegerField``        |n| |i|
``PositiveSmallIntegerField``   |n| |i|
``SlugField``                   |i| |i|
``SmallIntegerField``           |n| |i|
``TextField``                   |y| |y|
``TimeField``                   |n| |y|
``URLField``                    |i| |i|
``ForeignKey``                  |n| |n|
``OneToOneField``               |n| |n|
``ManyToManyField``             |n| |n|
=============================== === ===

.. |y| replace:: Yes
.. |i| replace:: Yes\*
.. |n| replace:: No
.. |u| replace:: ?

\* Implicitly supported (as subclass of a supported field)
