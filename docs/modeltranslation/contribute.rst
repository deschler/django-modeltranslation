.. _contribute:

How to Contribute
=================

There are various ways how you can contribute to the project.


Contributing Code
-----------------

The preferred way for code contributions are pull requests at `Github`_, usually
created against master.

.. note::

    In order to be properly blamed for a contribution, please verify that the
    email you commit with is connected to your Github account (see
    `help.github.com`_ for details).


Coding Style
************

Please make sure that your code follows the `PEP 8`_ style guide. The only
exception we make is to allow a maximum line length of 100. Furthermore
your code has to validate against `pyflakes`_. It is recommended to use
`flake8`_ which combines all the checks:

.. code-block:: console

    $ flake8 --max-line-length=100 modeltranslation

The ``#NOQA`` mark added by `flake8`_ should be used sparsely.


Django and Python Versions
**************************

We always try to support **at least** the two latest major versions of Django,
as well as Django's development version. While we can not guarantee the latter
to be supported in early development stages of a new Django version, we aim
to achieve support once it has seen its first release candidate.

The supported Python versions can be derived from the supported Django versions.
Example (from the past) where we support Python 2.5, 2.6 and 2.7:

 * Django 1.3 (old stable) supports Python 2.5, 2.6, 2.7
 * Django 1.4 (current stable) supports Python 2.5, 2.6, 2.7
 * Django 1.5 (dev) supports Python 2.6, 2.7

Python 3 is supported since 0.7 release. Although 0.6 release supported Django 1.5
(which started Python 3 compliance), it was not Python 3 ready yet.


Unittests
*********

Modeltranslation has a comprehensive test suite. A test runner is provided which
allows to run the tests outside of a Django project:

.. code-block:: console

    $ python runtests.py

Non trivial changes and new features should always be accompanied by a unittest.
Pull requests which add unittests for uncovered code or rare edge cases are also
appreciated.


Continuous Integration
**********************

The project uses `Travis CI`_ for continuous integration tests. Hooks provided
by Github are active, so that each push and pull request is automatically run
against our `Travis CI config`_, checking code against different databases,
Python and Django versions. This includes automatic tracking of test coverage
through `Coveralls`_.

.. image:: http://img.shields.io/coveralls/deschler/django-modeltranslation.png?style=flat
    :target: https://coveralls.io/r/deschler/django-modeltranslation


Contributing Documentation
--------------------------

Documentation is a crucial part of any open source project. We try to make
it as useful as possible for both, new and experienced developers. If you
feel that something is unclear or lacking, your help to improve it is highly
appreciated.

Even if you don't feel comfortable enough to document modeltranslation's usage
or internals, you still have a chance to contribute. None of the core
committers is a native english speaker and bad grammar or misspellings happen.
If you find any of these kind or just simple typos, nobody will feel offended
for getting an English lesson.

The documentation is written using `reStructuredText`_ and `Sphinx`_. You
should try to keep a maximum line length of 80 characters. Unlike for code
contribution this isn't a forced rule and easily exceeded by something like a
long url.


Using the Issue Tracker
-----------------------

When you have found a bug or want to request a new feature for modeltranslation,
please create a ticket using the project's `issue tracker`_. Your report should
include as many details as possible, like a traceback in case you get one.

Please do not use the issue tracker for general questions, we run a dedicated
`mailing list`_ for this.


.. _help.github.com: https://help.github.com/articles/why-are-my-commits-linked-to-the-wrong-user
.. _PEP 8: http://www.python.org/dev/peps/pep-0008/
.. _pyflakes: https://pypi.python.org/pypi/pyflakes
.. _flake8: https://pypi.python.org/pypi/flake8
.. _Github: https://github.com/deschler/django-modeltranslation
.. _Travis CI: https://travis-ci.org/deschler/django-modeltranslation
.. _Travis CI config: https://github.com/deschler/django-modeltranslation/blob/master/.travis.yml
.. _Coveralls: https://coveralls.io/r/deschler/django-modeltranslation
.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/
.. _issue tracker: https://github.com/deschler/django-modeltranslation/issues
.. _mailing list: http://groups.google.com/group/django-modeltranslation
