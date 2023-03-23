.. _caveats:

Caveats
=======

Accessing Translated Fields Outside Views
-----------------------------------------

Since the modeltranslation mechanism relies on the current language as it
is returned by the ``get_language`` function care must be taken when accessing
translated fields outside a view function.

Within a view function the language is set by Django based on a flexible model
described at `How Django discovers language preference`_ which is normally used
only by Django's static translation system.

.. _How Django discovers language preference: https://docs.djangoproject.com/en/dev/topics/i18n/translation/#how-django-discovers-language-preference

When a translated field is accessed in a view function or in a template, it
uses the ``django.utils.translation.get_language`` function to determine the
current language and return the appropriate value.

Outside a view (or a template), i.e. in normal Python code, a call to the
``get_language`` function still returns a value, but it might not what you
expect. Since no request is involved, Django's machinery for discovering the
user's preferred language is not activated. For this reason modeltranslation
adds a thin wrapper (``modeltranslation.utils.get_language``) around the function
which guarantees that the returned language is listed in the ``LANGUAGES`` setting.

The unittests use the ``django.utils.translation.trans_real`` functions to
activate and deactive a specific language outside a view function.

Using in combination with ``django-audit-log``
----------------------------------------------

``django-audit-log`` is a package that allows you to track changes to your
model instances (`documentation`_). As ``django-audit-log`` behind the scenes
automatically creates "shadow" models for your tracked models, you have to
remember to register these shadow models for translation as well as your
regular models. Here's an example:

.. code:: python

    from modeltranslation.translator import register, TranslationOptions

    from my_app import models


    @register(models.MyModel)
    @register(models.MyModel.audit_log.model)
    class MyModelTranslationOptions(TranslationOptions):
        """Translation options for MyModel."""

        fields = (
            'text',
            'title',
        )

If you forget to register the shadow models, you will get an error like:

.. code::

    TypeError: 'text_es' is an invalid keyword argument for this function
    
Using in combination with ``django-rest-framework``
-------------------------------------------------
When creating a new viewset , make sure to override ``get_queryset`` method, using ``queryset`` as a property won't work because it is being evaluated once, before any language was set.

Translating ``ManyToManyField`` fields
-------------------------------------------------
Translated ``ManyToManyField`` fields do not support fallbacks. This is because the field descriptor returns a ``Manager`` when accessed. If falbacks were enabled we could find ourselves using the manager of a different language than the current one without realizing it. This can lead to using the ``.set()`` method on the wrong language.
Due to this behavior the fallbacks on M2M fields have been disabled.

.. _documentation: https://django-audit-log.readthedocs.io/
