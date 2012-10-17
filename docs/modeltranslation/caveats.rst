.. _caveats:

Caveats
=======

Consider the following example (assuming the default language is ``de``):

.. code-block:: python

    >>> n = News.objects.create(title="foo")
    >>> n.title
    'foo'
    >>> n.title_de
    >>>

Because the original field ``title`` was specified in the constructor it is
directly passed into the instance's ``__dict__`` and the descriptor which
normally updates the associated default translation field (``title_de``) is not
called. Therefor the call to ``n.title_de`` returns an empty value.

Now assign the title, which triggers the descriptor and the default translation
field is updated:

.. code-block:: python

    >>> n.title = 'foo'
    >>> n.title_de
    'foo'
    >>>


Accessing translated fields outside views
-----------------------------------------
Since the ``modeltranslation`` mechanism relies on the current language as it
is returned by the ``get_language`` function care must be taken when accessing
translated fields outside a view function.

Within a view function the language is set by Django based on a flexible model
described at `How Django discovers language preference`_ which is normally used
only by Django's static translation system.

.. _How Django discovers language preference: http://docs.djangoproject.com/en/dev/topics/i18n/#id2

When a translated field is accessed in a view function or in a template, it
uses the ``django.utils.translation.get_language`` function to determine the
current language and return the appropriate value.

Outside a view (or a template), i.e. in normal Python code, a call to the
``get_language`` function still returns a value, but it might not what you
expect. Since no request is involved, Django's machinery for discovering the
user's preferred language is not activated.

.. todo:: Explain more

The unittests in ``tests.py`` use the ``django.utils.translation.trans_real``
functions to activate and deactive a specific language outside a view function.
