Django admin integration
========================
In order to be able to edit the translations via the admin backend you need to
register a special admin class for the translated models. The admin class must
derive from ``modeltranslation.admin.TranslationAdmin`` which does some funky
patching on all your models registered for translation:

.. code-block:: python

    from django.contrib import admin
    from modeltranslation.admin import TranslationAdmin

    class NewsAdmin(TranslationAdmin):
        list_display = ('title',)

    admin.site.register(News, NewsAdmin)


Tweaks applied to the admin
---------------------------

formfield_for_dbfield
*********************
The ``TranslationBaseModelAdmin`` class, which ``TranslationAdmin`` and all
inline related classes in modeltranslation derive from, implements a special
method which is ``def formfield_for_dbfield(self, db_field, **kwargs)``. This
method does the following:

1. Copies the widget of the original field to each of it's translation fields.
2. Checks if the original field was required and if so makes
   the default translation field required instead.


get_form and get_fieldsets
**************************
The ``TranslationBaseModelAdmin`` class overrides ``get_form``,
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


TranslationAdmin in combination with other admin classes
--------------------------------------------------------
If there already exists a custom admin class for a translated model and you
don't want or can't edit that class directly there is another solution.

Taken the News example let's say there is a ``NewsAdmin`` class defined by the
News app itself. This app is not yours or you don't want to touch it at all.
In the most common case you simply make use of Python's support for multiple
inheritance like this:

.. code-block:: python

    class MyTranslatedNewsAdmin(NewsAdmin, TranslationAdmin):
        pass

In a more complex setup the NewsAdmin itself might override
formfield_for_dbfield:

.. code-block:: python

    class NewsAdmin(model.Admin):
        def formfield_for_dbfield(self, db_field, **kwargs):
            # does some funky stuff with the formfield here

Unfortunately the first example won't work anymore because Python can only
execute one of the ``formfield_for_dbfield`` methods. Since both admin class
implement this method Python must make a decision and it chooses the first
class ``NewsAdmin``. The functionality from ``TranslationAdmin`` will not be
executed and translation in the admin will not work for this class.

But don't panic, here's a solution:

.. code-block:: python

    class MyTranslatedNewsAdmin(NewsAdmin, TranslationAdmin):
        def formfield_for_dbfield(self, db_field, **kwargs):
            field = super(MyTranslatedNewsAdmin, self).formfield_for_dbfield(db_field, **kwargs)
            self.patch_translation_field(db_field, field, **kwargs)
            return field

This implements the ``formfield_for_dbfield`` such that both functionalities
will be executed. The first line calls the superclass method which in this case
will be the one of ``NewsAdmin`` because it is the first class inherited from.
The ``TranslationAdmin`` capsulates all it's functionality in the
``patch_translation_field(db_field, field, **kwargs)`` method and the
``formfield_for_dbfield`` implementation of the ``TranslationAdmin`` class
simply calls it. You can copy this behaviour by calling it from a
custom admin class and that's done in the example above. After that the
``field`` is fully patched for translation and finally returned.


Inlines
-------
.. versionadded:: 0.2

Support for tabular and stacked inlines, common and generic ones.

A translated inline must derive from one of the following classes:

 * ``modeltranslation.admin.TranslationTabularInline``
 * ``modeltranslation.admin.TranslationStackedInline``
 * ``modeltranslation.admin.TranslationGenericTabularInline``
 * ``modeltranslation.admin.TranslationGenericStackedInline``

Just like ``TranslationAdmin`` these classes implement a special method
``formfield_for_dbfield`` which does all the patching.

For our example we assume that there is new model called ``Image``. It's
definition is left out for simplicity. Our ``News`` model inlines the new
model:

.. code-block:: python

    from django.contrib import admin
    from modeltranslation.admin import TranslationTabularInline

    class ImageInline(TranslationTabularInline):
        model = Image

    class NewsAdmin(admin.ModelAdmin):
        list_display = ('title',)
        inlines = [ImageInline,]

    admin.site.register(News, NewsAdmin)

.. note:: In this example only the ``Image`` model is registered in
          ``translation.py``. It's not a requirement that ``NewsAdmin`` derives
          from ``TranslationAdmin`` in order to inline a model which is
          registered for translation.

In this more complex example we assume that the ``News`` and ``Image`` models
are registered in ``translation.py``. The ``News`` model has an own custom
admin class and the Image model an own generic stacked inline class. It uses
the technique described in
`TranslationAdmin in combination with other admin classes`__.:

__ translationadmin_in_combination_with_other_admin_classes_

.. code-block:: python

    from django.contrib import admin
    from modeltranslation.admin import TranslationAdmin, TranslationGenericStackedInline

    class TranslatedImageInline(ImageInline, TranslationGenericStackedInline):
        model = Image

    class TranslatedNewsAdmin(NewsAdmin, TranslationAdmin):
        def formfield_for_dbfield(self, db_field, **kwargs):
            field = super(TranslatedNewsAdmin, self).formfield_for_dbfield(db_field, **kwargs)
            self.patch_translation_field(db_field, field, **kwargs)
            return field

        inlines = [TranslatedImageInline,]

    admin.site.register(News, NewsAdmin)


Using tabbed translation fields
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
                'http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.2/jquery-ui.min.js',
                'modeltranslation/js/tabbed_translation_fields.js',
            )
            css = {
                'screen': ('modeltranslation/css/tabbed_translation_fields.css',),
            }

The ``force_jquery.js`` script is necessary when using Django's built-in
``django.jQuery`` object. This and the static urls used are just an example and
might have to be adopted to your setup of serving static files. Standard
jquery-ui theming can be used to customize the look of tabs, the provided css
file is supposed to work well with a default Django admin.
