Quickstart
==========

1. Install using pip:

.. code-block:: sh

    $ pip install django-simple-log

2. Add to installed apps:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'simple_log',
        ...
    )

3. Add middleware for detecting user:

.. code-block:: python

    MIDDLEWARE = [
        ...
        'simple_log.middleware.ThreadLocalMiddleware',
        ...
    ]

4. Migrate:

.. code-block:: sh

    $ python manage.py migrate
