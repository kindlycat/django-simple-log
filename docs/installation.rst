Installation
============
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
