.. _usage:

Accessing translated and translation fields
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


Rules for translated field access
---------------------------------
So now when it comes to setting and getting the value of the original and the
translation fields the following rules apply:

**Rule 1**

    Reading the value from the original field returns the value translated to
    the *current language*.

**Rule 2**

    Assigning a value to the original field also updates the value in the
    associated default translation field.

**Rule 3**

    Assigning a value to the default translation field also updates the
    original field - note that the value of the original field will not be
    updated until the model instance is saved.

**Rule 4**

    If both fields - the original and the default translation field - are
    updated at the same time, the default translation field wins.


Examples for translated field access
------------------------------------
Because the whole point of using the modeltranslation app is translating
dynamic content, the fields marked for translation are somehow special when it
comes to accessing them. The value returned by a translated field is depending
on the current language setting. "Language setting" is referring to the Django
`set_language`_ view and the corresponding ``get_lang`` function.

Assuming the current language is ``de`` in the News example from above, the
translated ``title`` field will return the value from the ``title_de`` field:

.. code-block:: python

    # Assuming the current language is "de"
    n = News.objects.all()[0]
    t = n.title # returns german translation

    # Assuming the current language is "en"
    t = n.title # returns english translation

This feature is implemented using Python descriptors making it happen without
the need to touch the original model classes in any way. The descriptor uses
the ``django.utils.i18n.get_language`` function to determine the current
language.


.. _set_language: https://docs.djangoproject.com/en/dev/topics/i18n/translation/#set-language-redirect-view
