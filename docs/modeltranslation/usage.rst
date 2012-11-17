.. _usage:

Accessing Translated and Translation Fields
===========================================

The modeltranslation app changes the behaviour of the translated fields. To
explain this consider the news example from the :ref:`registration` chapter
again. The original ``News`` model looked like this:

.. code-block:: python

    class News(models.Model):
        title = models.CharField(max_length=255)
        text = models.TextField()

Now that it is registered with the modeltranslation app the model looks
like this - note the additional fields automatically added by the app:

.. code-block:: python

    class News(models.Model):
        title = models.CharField(max_length=255)  # original/translated field
        title_de = models.CharField(null=True, blank=True, max_length=255)  # default translation field
        title_en = models.CharField(null=True, blank=True, max_length=255)  # translation field
        text = models.TextField()  # original/translated field
        text_de = models.TextField(null=True, blank=True)  # default translation field
        text_en = models.TextField(null=True, blank=True)  # translation field

The example above assumes that the default language is ``de``, therefore the
``title_de`` and ``text_de`` fields are marked as the *default translation
fields*. If the default language is ``en``, the ``title_en`` and ``text_en``
fields would be the *default translation fields*.

.. _rules:

Rules for Translated Field Access
---------------------------------

.. versionchanged:: 0.5

So now when it comes to setting and getting the value of the original and the
translation fields the following rules apply:

**Rule 1**

    Reading the value from the original field returns the value translated to
    the current language.

**Rule 2**

    Assigning a value to the original field updates the value in the associated
    current language translation field.

**Rule 3**

    If both fields - the original and the current language translation field -
    are updated at the same time, the current language translation field wins.

    .. note:: This can only happen in the model's constructor or
        ``objects.create``. There is no other situation which can be considered
        *changing several fields at the same time*.


Examples for Translated Field Access
------------------------------------

Because the whole point of using the modeltranslation app is translating
dynamic content, the fields marked for translation are somehow special when it
comes to accessing them. The value returned by a translated field is depending
on the current language setting. "Language setting" is referring to the Django
`set_language`_ view and the corresponding ``get_lang`` function.

Assuming the current language is ``de`` in the news example from above, the
translated ``title`` field will return the value from the ``title_de`` field:

.. code-block:: python

    # Assuming the current language is "de"
    n = News.objects.all()[0]
    t = n.title  # returns german translation

    # Assuming the current language is "en"
    t = n.title  # returns english translation

This feature is implemented using Python descriptors making it happen without
the need to touch the original model classes in any way. The descriptor uses
the ``django.utils.i18n.get_language`` function to determine the current
language.

.. todo:: Add more examples.


.. _multilingual_manager:

Multilingual Manager
--------------------

.. versionadded:: 0.5

.. todo:: Write something smart.


The State of the Original Field
-------------------------------

.. versionchanged:: 0.5

As defined by the :ref:`rules`, accessing the original field is guaranteed to
work on the associated translation field of the current language. This applies
to both, read and write operations.

The actual field value (which *can* still be accessed through
``instance.__dict__['original_field_name']``) however has to be considered
**undetermined** once the field has been registered for translation.
Attempts to keep the value in sync with either the default or current
language's field value has raised a boatload of unpredictable side effects in
older versions of modeltranslation.

.. warning::
    Do not rely on the underlying value of the *original field* in any way!

.. todo::
    Perhaps outline effects this might have on the ``update_translation_field``
    management command.


.. _set_language: https://docs.djangoproject.com/en/dev/topics/i18n/translation/#set-language-redirect-view
