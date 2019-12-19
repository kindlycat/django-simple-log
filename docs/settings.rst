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


SIMPLE_LOG_SAVE_RELATED
-----------------------
Default: ``False``

Link related logs.


SIMPLE_LOG_SAVE_ONE_TO_MANY
---------------------------
Default: ``False``

Track one to many fields.


SIMPLE_LOG_PROXY_CONCRETE
-------------------------
Default: ``False``

Save content type of proxy model, instead of base.


SIMPLE_LOG_SAVE_ONLY_CHANGED
----------------------------
Default: ``False``

Save only changed fields.


SIMPLE_LOG_DATETIME_FORMAT
--------------------------
Default: ``None``

Format for datetime fields.


SIMPLE_LOG_DATE_FORMAT
----------------------
Default: ``None``

Format for date fields.


SIMPLE_LOG_TIME_FORMAT
----------------------
Default: ``None``

Format for time fields.


SIMPLE_LOG_FILE_NAME_ONLY
-------------------------
Default: ``True``

Save file name only instead of path to file.


SIMPLE_LOG_EXCLUDE_RAW
-------------------------
Default: ``False``

Don't create log entry if signal is raw (e. g. load data from fixtures).
