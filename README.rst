Django simple log
=================
.. image:: https://travis-ci.org/kindlycat/django-simple-log.svg?branch=master
    :target: https://travis-ci.org/kindlycat/django-simple-log
.. image:: https://coveralls.io/repos/github/kindlycat/django-simple-log/badge.svg?branch=master
    :target: https://coveralls.io/github/kindlycat/django-simple-log?branch=master
.. image:: https://img.shields.io/pypi/v/django-simple-log.svg
    :target: https://pypi.python.org/pypi/django-simple-log
.. image:: https://img.shields.io/pypi/status/django-simple-log.svg
    :target: https://pypi.python.org/pypi/django-simple-log
.. image:: https://img.shields.io/pypi/pyversions/django-simple-log.svg
    :target: https://pypi.python.org/pypi/django-simple-log
.. image:: https://img.shields.io/badge/django-%3E%3D1.8-green.svg
    :target: https://pypi.python.org/pypi/django-simple-log
.. image:: https://img.shields.io/gitter/room/nwjs/nw.js.svg
    :target: https://gitter.im/django-simple-log/django-simple-log

Logging model changes on every create/update/delete.

TL;DR
-----
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
        'simple_log.middleware.ThreadLocalMiddleware',
        ...
    ]

For django 1.8:

.. code-block:: sh

    $ pip install django-jsonfield django-transaction-hooks

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'transaction_hooks.backends.postgresql_psycopg2',
            ...
        }
    }

Migrate:

.. code-block:: sh

    $ python manage.py migrate


Disable logging
===============
For temporary disable logging:

.. code-block:: python

    from simple_log.utils import disable_logging

    with disable_logging():
        # create/update/delete objects


Commands
========
To view which models is tracking:

.. code-block:: sh

    $ python manage.py view_tracking_models

With option ``-f`` you can view which fields is tracking for every model.

Settings
========

SIMPLE_LOG_MODEL_LIST
---------------------

Default: ``()``

List of models for logging by label: 'app.Model'.

SIMPLE_LOG_EXCLUDE_MODEL_LIST
-----------------------------

Default: ``('admin.LogEntry', 'migrations.Migration', 'sessions.Session',
'contenttypes.ContentType', 'captcha.CaptchaStore')``

List of models for exclude from logging by label: 'app.Model'.

SIMPLE_LOG_EXCLUDE_FIELD_LIST
-----------------------------
Default:
``('id', 'last_login', 'password', 'created_at', 'updated_at')``

List of field names which not track.

If you need to define which fields to track for concrete model, you can add
one of the properties to model: ``simple_log_fields = ('id',)`` or
``simple_log_exclude_fields = ('password',)``.

SIMPLE_LOG_ANONYMOUS_REPR
-------------------------
Default: ``'Anonymous'``

User representation that write to log, if anonymous user changes model.


SIMPLE_LOG_NONE_USER_REPR
-------------------------
Default: ``'System'``

User representation that write to log, if user not detected (If middleware not
working or if model changes from task or console).

SIMPLE_LOG_MODEL
----------------
Default: ``'simple_log.SimpleLog'``

Model for writing logs. If you want to define your own model, you should
inheritance from ``simple_log.SimpleLogAbstract`` and change this setting.

If you need to define log model for concrete model, you can property to model:
``simple_log_model = 'simple_log.SimpleLog'``.

SIMPLE_LOG_MODEL_SERIALIZER
---------------------------
Default: ``'simple_log.models.ModelSerializer'``

Class for serializing model fields to json.

SIMPLE_LOG_GET_CURRENT_REQUEST
------------------------------
Default: ``'simple_log.utils.get_current_request_default'``

Function that return current request. Rewrite this setting if you already
have middleware for storing current request.

SIMPLE_LOG_OLD_INSTANCE_ATTR_NAME
---------------------------------
Default: ``'_old_instance'``

Name of attribute for storing old instance of logging object.
