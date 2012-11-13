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
adds a thin wrapper around the function which guarantees that the returned
language is listed in the ``LANGUAGES`` setting.

The unittests use the ``django.utils.translation.trans_real`` functions to
activate and deactive a specific language outside a view function.
