Django simple log
=================
.. image:: https://travis-ci.org/kindlycat/django-simple-log.svg?branch=master
    :target: https://travis-ci.org/kindlycat/django-simple-log
.. image:: https://coveralls.io/repos/github/kindlycat/django-simple-log/badge.svg?branch=master
    :target: https://coveralls.io/github/kindlycat/django-simple-log?branch=master
.. image:: https://img.shields.io/pypi/v/django-simple-log.svg
    :target: https://pypi.python.org/pypi/django-simple-log

Logging model changes on every create/update/delete (except queryset update).

Full documentation on `read the docs`_.


Installation
------------
Install using pip:

.. code-block:: sh

    $ pip install django-simple-log

Add to installed apps:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'simple_log',
        ...
    )

Add middleware for detecting user:

.. code-block:: python

    MIDDLEWARE = [
        ...
        'request_vars.middleware.RequestVarsMiddleware',
        ...
    ]

Migrate:

.. code-block:: sh

    $ python manage.py migrate


.. _`read the docs`: https://django-simple-log.readthedocs.io/en/latest/
