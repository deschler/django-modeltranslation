.. _forms:

ModelForms
==========

``ModelForms`` for multilanguage models are defined and handled as typical ``ModelForms``.
Please note, however, that they shouldn't be defined next to models
(see :ref:`a note <register-precautions>`).

Editing multilanguage models with all translation fields in the admin backend is quite sensible.
However, presenting all model fields to the user on the frontend may be not the right way.
Here comes the ``TranslationModelForm`` which strip out all translation fields::

    from news.models import News
    from modeltranslation.forms import TranslationModelForm

    class MyForm(TranslationModelForm):
        class Meta:
            model = News

Such a form will contain only original fields (title, text - see :ref:`example <registration>`).
Of course, upon saving, provided values would be set on proper attributes, depending on the user
current language.


.. _formfield_nullability:

Formfields and nullability
--------------------------

.. versionadded:: 0.7.1

.. note::
    Please remember that all translation fields added to model definition are nullable
    (``null=True``), regardless of the original field nullability.

In most cases formfields for translation fields behave as expected. However, there is one annoying
problem with ``models.CharField`` - probably the most commonly translated field type.

The problem is that default formfield for ``CharField`` stores empty values as empty strings
(``''``), even if the field is nullable
(see django `ticket #9590 <http://code.djangoproject.com/ticket/9590>`_).

Thus formfields for translation fields are patched by modeltranslation. The following rules apply:

.. _formfield_rules:

- If the original field is not nullable, an empty value is saved as ``''``;
- If the original field is nullable, an empty value is saved as ``None``.

To deal with complex cases, these rules can be overridden per model or even per field
using ``TranslationOptions``::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        empty_values = None

    class ProjectTranslationOptions(TranslationOptions):
        fields = ('name', 'slug', 'description',)
        empty_values = {'name': '', 'slug': None}

If a field is not mentioned while using dict syntax, the :ref:`default rules <formfield_rules>`
apply.

This configuration is especially useful for fields with unique constraints::

    class Category(models.Model):
        name = models.CharField(max_length=40)
        slug = models.SlugField(max_length=30, unique=True)

Because the ``slug`` field is not nullable, its translation fields would store empty values as
``''`` and that would result in an error when two or more ``Categories`` are saved with
``slug_en`` empty - unique constraints wouldn't be satisfied. Instead, ``None`` should be stored,
as several ``None`` values in the database don't violate uniqueness::

    class CategoryTranslationOptions(TranslationOptions):
        fields = ('name', 'slug')
        empty_values = {'slug': None}


.. _forms-formfield-both:

None-checkbox widget
********************

Maybe there is a situation where you want to store both - empty strings and ``None``
values - in a field. For such a scenario there is a third configuration value: ``'both'``::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        empty_values = {'title': None, 'text': 'both'}

It results in a special widget with a None-checkbox to null a field. It's not recommended in
frontend as users may be confused what this `None` is. The only useful place for this widget might
be the admin backend; see :ref:`admin-formfield`.

To sum it up, the valid values for ``empty_values`` are: ``None``, ``''`` and ``'both'``.
