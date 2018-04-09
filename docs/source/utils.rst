Utils
=====

For temporary disable logging:

.. code-block:: python

    from simple_log.utils import disable_logging

    with disable_logging():
        # create/update/delete objects


To view which models is tracking:

.. code-block:: sh

    $ python manage.py view_tracking_models

With option ``-f`` you can view which fields is tracking for every model.
