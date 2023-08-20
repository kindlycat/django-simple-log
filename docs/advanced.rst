Advanced usage
==============

Manual logging
--------------

If you need to log something manually:

.. code-block:: python

    from simple_log.models import SimpleLog

    SimpleLog.log(
        instance=obj,
        action_flag=SimpleLog.CHANGE,
        change_message='Some message'
    )


Pass params to log
------------------

Add ``simple_log_params`` to instance:

.. code-block:: python

    class SomeView(FormView):
        ...

        def form_valid(self, form):
            form.instance.simple_log_params = {
                'user': None,
                'user_repr': 'GLaDOS',
                'change_message': 'Cake is a lie'
            }
            return super().form_valid(form)


Custom serializer
-----------------

.. code-block:: python

    # Serializer for concrete model
    class MyModel:
        ...
        simple_log_model_serializer = 'app_label.ModelName'

    # Default serializer in settings
    SIMPLE_LOG_MODEL_SERIALIZER = 'app_label.ModelName'


Custom log model
----------------

.. code-block:: python

    from simple_log.models import SimpleLogAbstractBase

    from django.db import models
    from django.utils.translation import gettext_lazy as _


    class ChangeLog(SimpleLogAbstractBase):
        # custom action_flag
        ERROR = 4
        ACTION_CHOICES = SimpleLogAbstractBase.ACTION_CHOICES + (
            (ERROR, 'error'),
        )

        action_flag = models.PositiveSmallIntegerField(
            _('action flag'),
            choices=ACTION_CHOICES,
            default=SimpleLogAbstractBase.CHANGE
        )

        # custom field
        user_is_staff = models.BooleanField(default=False)

        @classmethod
        def get_log_params(cls, instance, **kwargs):
            params = super(ChangeLog, cls).get_log_params(instance, **kwargs)
            user = params['user']
            if user:
                params['user_is_staff'] = user.is_staff
            return params

    # in settings
    SIMPLE_LOG_MODEL = 'app_label.ChangeLog'

