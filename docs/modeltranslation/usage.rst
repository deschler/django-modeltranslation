.. _usage:

Accessing Translated and Translation Fields
===========================================

Modeltranslation changes the behaviour of the translated fields. To
explain this consider the news example from the :ref:`registration` chapter
again. The original ``News`` model looked like this::

    class News(models.Model):
        title = models.CharField(max_length=255)
        text = models.TextField()

Now that it is registered with modeltranslation the model looks
like this - note the additional fields automatically added by the app::

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
translated ``title`` field will return the value from the ``title_de`` field::

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

Every model registered for translation is patched so that all its managers become subclasses
of ``MultilingualManager`` (of course, if a custom manager was defined on the model, its
functions will be retained). ``MultilingualManager`` simplifies language-aware queries,
especially on third-party apps, by rewriting query field names.

Every model's manager is patched, not only ``objects`` (even managers inherited from abstract base
classes).

For example::

    # Assuming the current language is "de",
    # these queries returns the same objects
    news1 = News.objects.filter(title__contains='enigma')
    news2 = News.objects.filter(title_de__contains='enigma')

    assert news1 == news2

It works as follow: if the translation field name is used (``title``), it is changed into the
current language field name (``title_de`` or ``title_en``, depending on the current active
language).
Any language-suffixed names are left untouched (so ``title_en`` wouldn't change,
no matter what the current language is).

Rewriting of field names works with operators (like ``__in``, ``__ge``) as well as with
relationship spanning. Moreover, it is also handled on ``Q`` and ``F`` expressions.

These manager methods perform rewriting:

- ``filter()``, ``exclude()``, ``get()``
- ``order_by()``
- ``update()``
- ``only()``, ``defer()``
- ``values()``, ``values_list()``, with :ref:`fallback <fallback>` mechanism
- ``dates()``
- ``select_related()``
- ``create()``, with optional auto-population_ feature

In order not to introduce differences between ``X.objects.create(...)`` and ``X(...)``, model
constructor is also patched and performs rewriting of field names prior to regular initialization.

If one wants to turn rewriting of field names off, this can be easily achieved with
``rewrite(mode)`` method. ``mode`` is a boolean specifying whether rewriting should be applied.
It can be changed several times inside a query. So ``X.objects.rewrite(False)`` turns rewriting off.

``MultilingualManager`` offers one additional method: ``raw_values``. It returns actual values from
the database, without field names rewriting. Useful for checking translated field database value.

Auto-population
***************

.. versionchanged:: 0.6

There is special manager method ``populate(mode)`` which can trigger ``create()`` or
``get_or_create()`` to populate all translation (language) fields with values from translated
(original) ones. It can be very convenient when working with many languages. So::

    x = News.objects.populate(True).create(title='bar')

is equivalent of::

    x = News.objects.create(title_en='bar', title_de='bar') ## title_?? for every language


Moreover, some fields can be explicitly assigned different values::

    x = News.objects.populate(True).create(title='-- no translation yet --', title_de='enigma')

It will result in ``title_de == 'enigma'`` and other ``title_?? == '-- no translation yet --'``.

There is another way of altering the current population status, an ``auto_populate`` context
manager::

    from modeltranslation.utils import auto_populate

    with auto_populate(True):
        x = News.objects.create(title='bar')

Auto-population takes place also in model constructor, what is extremely useful when loading
non-translated fixtures. Just remember to use the context manager::

     with auto_populate():  # True can be ommited
        call_command('loaddata', 'fixture.json')  # Some fixture loading

        z = News(title='bar')
        print(z.title_en, z.title_de)  # prints 'bar bar'

There is a more convenient way than calling ``populate`` manager method or entering
``auto_populate`` manager context all the time:
:ref:`settings-modeltranslation_auto_populate` setting.
It controls the default population behaviour.

.. _auto-population-modes:

Auto-population modes
^^^^^^^^^^^^^^^^^^^^^

There are four different population modes:

``False``
    [set by default]

    Auto-population turned off

``True`` or ``'all'``
    [default argument to population altering methods]

    Auto-population turned on, copying translated field value to all other languages
    (unless a translation field value is provided)

``'default'``
    Auto-population turned on, copying translated field value to default language field
    (unless its value is provided)

``'required'``
    Acts like ``'default'``, but copy value only if the original field is non-nullable


.. _fallback:

Falling back
------------

Modeltranslation provides a mechanism to control behaviour of data access in case of empty
translation values. This mechanism affects field access, as well as ``values()``
and ``values_list()`` manager methods.

Consider the ``News`` example: a creator of some news hasn't specified its German title and
content, but only English ones. Then if a German visitor is viewing the site, we would rather show
him English title/content of the news than display empty strings. This is called *fallback*. ::

    news.title_en = 'English title'
    news.title_de = ''
    print(news.title)
    # If current active language is German, it should display the title_de field value ('').
    # But if fallback is enabled, it would display 'English title' instead.

    # Similarly for manager
    news.save()
    print(News.objects.filter(pk=news.pk).values_list('title', flat=True)[0])
    # As above: if current active language is German and fallback to English is enabled,
    # it would display 'English title'.

There are several ways of controlling fallback, described below.

.. _fallback_lang:

Fallback languages
******************

.. versionadded:: 0.5

:ref:`settings-modeltranslation_fallback_languages` setting allows to set the order of *fallback
languages*. By default that's the ``DEFAULT_LANGUAGE``.

For example, setting ::

    MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'de', 'fr')

means: if current active language field value is unset, try English value. If it is also unset,
try German, and so on - until some language yields a non-empty value of the field.

There is also an option to define a fallback by language, using dict syntax::

    MODELTRANSLATION_FALLBACK_LANGUAGES = {
        'default': ('en', 'de', 'fr'),
        'fr': ('de',),
        'uk': ('ru',)
    }

The ``default`` key is required and its value denote languages which are always tried at the end.
With such a setting:

- for `uk` the order of fallback languages is: ``('ru', 'en', 'de', 'fr')``
- for `fr` the order of fallback languages is: ``('de', 'en')`` - Note, that `fr` obviously is not
  a fallback, since its active language and `de` would be tried before `en`
- for `en` and `de` the fallback order is ``('de', 'fr')`` and ``('en', 'fr')``, respectively
- for any other language the order of fallback languages is just ``('en', 'de', 'fr')``

What is more, fallback languages order can be overridden per model, using ``TranslationOptions``::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        fallback_languages = {'default': ('fa', 'km')}  # use Persian and Khmer as fallback for News

Dict syntax is only allowed there.

.. versionadded:: 0.6

Even more, all fallbacks may be switched on or off for just some exceptional block of code using::

    from modeltranslation.utils import fallbacks

    with fallbacks(False):
        # Work with values for the active language only

.. _fallback_val:

Fallback values
***************

.. versionadded:: 0.4

But what if current language and all fallback languages yield no field value? Then modeltranslation
will use the field's *fallback value*, if one was defined.

Fallback values are defined in ``TranslationOptions``, for example::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        fallback_values = _('-- sorry, no translation provided --')

In this case, if title is missing in active language and any of fallback languages, news title
will be ``'-- sorry, no translation provided --'`` (maybe translated, since gettext is used).
Empty text will be handled in same way.

Fallback values can be also customized per model field::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        fallback_values = {
            'title': _('-- sorry, this news was not translated --'),
            'text': _('-- please contact our translator (translator@example.com) --')
        }

If current language and all fallback languages yield no field value, and no fallback values are
defined, then modeltranslation will use the field's default value.

.. _fallback_undef:

Fallback undefined
******************

.. versionadded:: 0.7

Another question is what do we consider "no value", on what value should we fall back to other
translations? For text fields the empty string can usually be considered as the undefined value,
but other fields may have different concepts of empty or missing values.

Modeltranslation defaults to using the field's default value as the undefined value (the empty
string for non-nullable ``CharFields``). This requires calling ``get_default`` for every field
access, which in some cases may be expensive.

If you'd like to fall back on a different value or your default is expensive to calculate, provide
a custom undefined value (for a field or model)::

    class NewsTranslationOptions(TranslationOptions):
        fields = ('title', 'text',)
        fallback_undefined = {
            'title': 'no title',
            'text': None
        }

The State of the Original Field
-------------------------------

.. versionchanged:: 0.5
.. versionchanged:: 0.12

As defined by the :ref:`rules`, accessing the original field is guaranteed to
work on the associated translation field of the current language. This applies
to both, read and write operations.

The actual field value (which *can* still be accessed through
``instance.__dict__['original_field_name']``) however has to be considered
**undetermined** once the field has been registered for translation.
Attempts to keep the value in sync with either the default or current
language's field value has raised a boatload of unpredictable side effects in
older versions of modeltranslation.

Since version 0.12 the original field is expected to have even more undetermined value.
It's because Django 1.10 changed the way deferred fields work.

.. warning::
    Do not rely on the underlying value of the *original field* in any way!

.. todo::
    Perhaps outline effects this might have on the ``update_translation_field``
    management command.


.. _set_language: https://docs.djangoproject.com/en/dev/topics/i18n/translation/#set-language-redirect-view
