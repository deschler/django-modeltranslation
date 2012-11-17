.. _admin:

Django Admin Integration
========================

In order to be able to edit the translations via the ``django.contrib.admin``
application you need to register a special admin class for the translated
models. The admin class must derive from
``modeltranslation.admin.TranslationAdmin`` which does some funky
patching on all your models registered for translation. Taken the
:ref:`news example <registration>` the most simple case would look like:

.. code-block:: python

    from django.contrib import admin
    from news.models import News
    from modeltranslation.admin import TranslationAdmin

    class NewsAdmin(TranslationAdmin):
        pass

    admin.site.register(News, NewsAdmin)


Tweaks Applied to the Admin
---------------------------

formfield_for_dbfield
*********************

The ``TranslationBaseModelAdmin`` class, which ``TranslationAdmin`` and all
inline related classes in modeltranslation derive from, implements a special
method which is ``def formfield_for_dbfield(self, db_field, **kwargs)``. This
method does the following:

1. Copies the widget of the original field to each of its translation fields.
2. Checks if the original field was required and if so makes the default
   translation field required instead.


get_form/get_fieldsets/_declared_fieldsets
******************************************

In addition the ``TranslationBaseModelAdmin`` class overrides ``get_form``,
``get_fieldsets`` and ``_declared_fieldsets`` to make the options ``fields``,
``exclude`` and ``fieldsets`` work in a transparent way. It basically does:

1. Removes the original field from every admin form by adding it to
   ``exclude`` under the hood.
2. Replaces the - now removed - orginal fields with their corresponding
   translation fields.

Taken the ``fieldsets`` option as an example, where the ``title`` field is
registered for translation but not the ``news`` field:

.. code-block:: python

    class NewsAdmin(TranslationAdmin):
        fieldsets = [
            (u'News', {'fields': ('title', 'news',)})
        ]

In this case ``get_fieldsets`` will return a patched fieldset which contains
the translation fields of ``title``, but not the original field:

.. code-block:: python

    >>> a = NewsAdmin(NewsModel, site)
    >>> a.get_fieldsets(request)
    [(u'News', {'fields': ('title_de', 'title_en', 'news',)})]


.. _translationadmin_in_combination_with_other_admin_classes:

TranslationAdmin in Combination with Other Admin Classes
--------------------------------------------------------

If there already exists a custom admin class for a translated model and you
don't want or can't edit that class directly there is another solution.

Taken a (fictional) reusable blog app which defines a model ``Entry`` and a
corresponding admin class called ``EntryAdmin``. This app is not yours and you
don't want to touch it at all.

In the most common case you simply make use of Python's support for multiple
inheritance like this:

.. code-block:: python

    class MyTranslatedEntryAdmin(EntryAdmin, TranslationAdmin):
        pass

The class is then registered for the ``admin.site`` (not to be confused with
modeltranslation's ``translator``). If ``EntryAdmin`` is already registered
through the blog app, it has to be unregistered first:

.. code-block:: python

    admin.site.unregister(Entry)
    admin.site.register(Entry, MyTranslatedEntryAdmin)


Admin Classes that Override ``formfield_for_dbfield``
*****************************************************

In a more complex setup the original ``EntryAdmin`` might override
``formfield_for_dbfield`` itself:

.. code-block:: python

    class EntryAdmin(model.Admin):
        def formfield_for_dbfield(self, db_field, **kwargs):
            # does some funky stuff with the formfield here

Unfortunately the first example won't work anymore because Python can only
execute one of the ``formfield_for_dbfield`` methods. Since both admin classes
implement this method Python must make a decision and it chooses the first
class ``EntryAdmin``. The functionality from ``TranslationAdmin`` will not be
executed and translation in the admin will not work for this class.

But don't panic, here's a solution:

.. code-block:: python

    class MyTranslatedEntryAdmin(EntryAdmin, TranslationAdmin):
        def formfield_for_dbfield(self, db_field, **kwargs):
            field = super(MyTranslatedEntryAdmin, self).formfield_for_dbfield(db_field, **kwargs)
            self.patch_translation_field(db_field, field, **kwargs)
            return field

This implements the ``formfield_for_dbfield`` such that both functionalities
will be executed. The first line calls the superclass method which in this case
will be the one of ``EntryAdmin`` because it is the first class inherited from.
The ``TranslationAdmin`` capsulates its functionality in the
``patch_translation_field`` method and the ``formfield_for_dbfield``
implementation of the ``TranslationAdmin`` class simply calls it. You can copy
this behaviour by calling it from a custom admin class and that's done in the
example above. After that the ``field`` is fully patched for translation and
finally returned.


Admin Inlines
-------------

.. versionadded:: 0.2

Support for tabular and stacked inlines, common and generic ones.

A translated inline must derive from one of the following classes:

 * ``modeltranslation.admin.TranslationTabularInline``
 * ``modeltranslation.admin.TranslationStackedInline``
 * ``modeltranslation.admin.TranslationGenericTabularInline``
 * ``modeltranslation.admin.TranslationGenericStackedInline``

Just like ``TranslationAdmin`` these classes implement a special method
``formfield_for_dbfield`` which does all the patching.

For our example we assume that there is a new model called ``Image``. The
definition is left out for simplicity. Our ``News`` model inlines the new
model:

.. code-block:: python

    from django.contrib import admin
    from news.models import Image, News
    from modeltranslation.admin import TranslationTabularInline

    class ImageInline(TranslationTabularInline):
        model = Image

    class NewsAdmin(admin.ModelAdmin):
        list_display = ('title',)
        inlines = [ImageInline,]

    admin.site.register(News, NewsAdmin)

.. note::
    In this example only the ``Image`` model is registered in
    ``translation.py``. It's not a requirement that ``NewsAdmin`` derives from
    ``TranslationAdmin`` in order to inline a model which is registered for
    translation.


Complex Example with Admin Inlines
**********************************

In this more complex example we assume that the ``News`` and ``Image`` models
are registered in ``translation.py``. The ``News`` model has an own custom
admin class called ``NewsAdmin`` and the ``Image`` model an own generic stacked
inline class called ``ImageInline``. Furthermore we assume that ``NewsAdmin``
overrides ``formfield_for_dbfield`` itself and the admin class is already
registered through the news app.

.. note::
    The example uses the technique described in
    `TranslationAdmin in combination with other admin classes`__.

__ translationadmin_in_combination_with_other_admin_classes_

Bringing it all together our code might look like this:

.. code-block:: python

    from django.contrib import admin
    from news.admin import ImageInline
    from news.models import Image, News
    from modeltranslation.admin import TranslationAdmin, TranslationGenericStackedInline

    class TranslatedImageInline(ImageInline, TranslationGenericStackedInline):
        model = Image

    class TranslatedNewsAdmin(NewsAdmin, TranslationAdmin):
        inlines = [TranslatedImageInline,]

        def formfield_for_dbfield(self, db_field, **kwargs):
            field = super(TranslatedNewsAdmin, self).formfield_for_dbfield(db_field, **kwargs)
            self.patch_translation_field(db_field, field, **kwargs)
            return field

    admin.site.unregister(News)
    admin.site.register(News, NewsAdmin)


Using Tabbed Translation Fields
-------------------------------

.. versionadded:: 0.3

Modeltranslation supports separation of translation fields via jquery-ui tabs.
The proposed way to include it is through the inner ``Media`` class of a
``TranslationAdmin`` class like this:

.. code-block:: python

    class NewsAdmin(TranslationAdmin):
        class Media:
            js = (
                'modeltranslation/js/force_jquery.js',
                'http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.24/jquery-ui.min.js',
                'modeltranslation/js/tabbed_translation_fields.js',
            )
            css = {
                'screen': ('modeltranslation/css/tabbed_translation_fields.css',),
            }

The ``force_jquery.js`` script is necessary when using Django's built-in
``django.jQuery`` object. Otherwise the *normal* ``jQuery`` object won't be
available to the included (non-namespaced) jquery-ui library.

Standard jquery-ui theming can be used to customize the look of tabs, the
provided css file is supposed to work well with a default Django admin.

.. note:: This is just an example and might have to be adopted to your setup.


Using a Custom jQuery Library
-----------------------------

If you don't want to use the jquery library shipped with Django, you can also
include a standard one. While this adds some redundancy it could be useful in
situations where you need certain features from a newer version of jquery
that is not yet included in Django or you rely on a non-namespaced version of
jquery somewhere in your custom admin frontend code or included plugins.

In this case you don't need the ``force_jquery.js`` static provided by
modeltranslation but include the standard jquery library before jquery-ui like
this:

.. code-block:: python

    class NewsAdmin(TranslationAdmin):
        class Media:
            js = (
                'http://code.jquery.com/jquery-1.8.2.min.js',
                'http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.24/jquery-ui.min.js',
                'modeltranslation/js/tabbed_translation_fields.js',
            )
            css = {
                'screen': ('modeltranslation/css/tabbed_translation_fields.css',),
            }

