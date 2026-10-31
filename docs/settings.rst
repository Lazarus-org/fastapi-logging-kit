Settings
========

By default, `fastapi_logging_kit` uses a built-in configuration that requires no additional setup. However, you can customize the logging settings by passing a configuration mapping to ``setup_logging``, or by setting ``FASTAPI_LOGGING_``-prefixed environment variables.

An explicit mapping passed to ``setup_logging`` takes priority over the environment, which in turn takes priority over the packaged defaults.

.. code-block:: python

    from fastapi import FastAPI

    from fastapi_logging_kit import setup_logging

    app = FastAPI()

    setup_logging(app, {"LOG_DIR": "logs"})

Environment variables are parsed as JSON, falling back to a plain string:

.. code-block:: shell

    export FASTAPI_LOGGING_LOG_DIR=/var/log/myapp
    export FASTAPI_LOGGING_LOG_FILE_LEVELS='["INFO", "ERROR"]'
    export FASTAPI_LOGGING_LOG_CONSOLE_COLORIZE=false

.. note::

   Configuration check failures are logged as warnings — they do **not** abort startup the way Django system checks do. Your application still boots.

Default configuration
---------------------

.. code-block:: python

    {
        "AUTO_INITIALIZATION_ENABLE": True,
        "INITIALIZATION_MESSAGE_ENABLE": True,
        "LOG_SQL_QUERIES_ENABLE": False,
        "LOG_FILE_LEVELS": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "LOG_DIR": "logs",
        "LOG_DIR_SIZE_LIMIT": 1024,  # MB
        "LOG_FILE_FORMATS": {
            "DEBUG": 1,
            "INFO": 1,
            "WARNING": 1,
            "ERROR": 1,
            "CRITICAL": 1,
        },
        "LOG_FILE_FORMAT_TYPES": {
            "DEBUG": "normal",
            "INFO": "normal",
            "WARNING": "normal",
            "ERROR": "normal",
            "CRITICAL": "normal",
        },
        "EXTRA_LOG_FILES": {  # for extra formats (JSON, XML)
            "DEBUG": False,
            "INFO": False,
            "WARNING": False,
            "ERROR": False,
            "CRITICAL": False,
        },
        "LOG_CONSOLE_LEVEL": "DEBUG",
        "LOG_CONSOLE_FORMAT": 1,
        "LOG_CONSOLE_COLORIZE": True,
        "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_EMAIL_NOTIFIER": {
            "ENABLE": False,
            "NOTIFY_ERROR": False,
            "NOTIFY_CRITICAL": False,
            "LOG_FORMAT": 1,
            "USE_TEMPLATE": True,
        },
        "INCLUDE_LOG_iBOARD": False,
        "DEBUG": False,
        "EMAIL": {},
        # Rotation — all keys are optional; defaults shown below
        "LOG_ROTATION": {
            "TYPE": "none",  # "none" | "size" | "time"
            "MAX_BYTES": 10485760,  # 10 MB, used when TYPE="size"
            "BACKUP_COUNT": 5,
            "WHEN": "midnight",  # used when TYPE="time"
            "INTERVAL": 1,
            "COMPRESS": False,
        },
        "LOG_ROTATION_OVERRIDES": {},
    }

Configuration Options
---------------------
Here's a breakdown of the available configuration options:

``AUTO_INITIALIZATION_ENABLE``
------------------------------

- **Type**: ``bool``
- **Description**: Enables automatic initialization of logging configurations. Defaults to ``True``.

``INITIALIZATION_MESSAGE_ENABLE``
---------------------------------

- **Type**: ``bool``
- **Description**: Enables logging of the initialization message when logging starts. Defaults to ``True``.

``INCLUDE_LOG_iBOARD``
----------------------

- **Type**: ``bool``
- **Description**: Registers the LogiBoard route and static files on your application. Defaults to ``False``. For setting up the LogiBoard, please refer to the :doc:`LogiBoard Integration <log_iboard>`.

``LOG_SQL_QUERIES_ENABLE``
--------------------------

- **Type**: ``bool``
- **Description**: Enables logging of SQL queries within ``RequestLogMiddleware`` logs. Defaults to ``False``. When enabled, queries recorded during each request will be included in the log output. See the ``Tracking queries`` section of the :doc:`Usage <usage>` documentation for how queries are collected.

``DEBUG``
---------

- **Type**: ``bool``
- **Description**: Replaces Django's ``settings.DEBUG``. Gates query counting in the ``execution_tracker`` decorator. Defaults to ``False``.

``LOG_FILE_LEVELS``
-------------------

- **Type**: ``list[str]``
- **Description**: Specifies which log levels should be captured in log files. Defaults to ``["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]``.

``LOG_DIR``
-----------

- **Type**: ``str``
- **Description**: Specifies the directory where log files will be stored. Defaults to ``"logs"``.

``LOG_DIR_SIZE_LIMIT``
----------------------

- **Type**: ``int``
- **Description**: Specifies the maximum allowed size of the log directory in megabytes (MB). If the directory exceeds this limit and ``MonitorLogSizeMiddleware`` is enabled, a warning email will be sent to the admin weekly. Defaults to ``1024 MB`` (1 GB).

``LOG_FILE_FORMATS``
--------------------

- **Type**: ``dict[str, int | str]``
- **Description**: Maps each log level to its corresponding log format. The format can be an ``int`` referencing a predefined format or a custom ``str`` format.
- **Default**: Format ``1`` for all levels.
- **Note**: See :ref:`available_format_options` below for the available formats.

``LOG_FILE_FORMAT_TYPES``
-------------------------

- **Type**: ``dict[str, str]``
- **Description**: Defines the format type (e.g., ``normal``, ``JSON``, ``XML``, ``FLAT``) for each log level. The keys are log levels, and the values are the format types.

    - **Format Types**:

      - ``normal``: Standard text log.
      - ``JSON``: Structured logs in JSON format.
      - ``XML``: Structured logs in XML format.
      - ``FLAT``: Logs with flat format.

- **Default**: Type ``normal`` for all levels.

``EXTRA_LOG_FILES``
-------------------

- **Type**: ``dict[str, bool]``
- **Description**: Determines whether separate log files for ``JSON`` or ``XML`` formats should be created for each log level. When set to ``True`` for a specific level, a dedicated directory (e.g., ``logs/json`` or ``logs/xml``) will be created with files like ``info.json`` or ``info.xml``. If ``False``, JSON and XML logs will be written to ``.log`` files.
- **Default**: ``False`` for all levels.

``LOG_CONSOLE_LEVEL``
---------------------

- **Type**: ``str``
- **Description**: Specifies the log level for console output. Defaults to ``"DEBUG"``.

``LOG_CONSOLE_FORMAT``
----------------------

- **Type**: ``int | str``
- **Description**: Specifies the format for console logs, similar to ``LOG_FILE_FORMATS``. Defaults to format ``1``.

``LOG_CONSOLE_COLORIZE``
------------------------

- **Type**: ``bool``
- **Description**: Determines whether console output should be colorized. Defaults to ``True``.

``LOG_DATE_FORMAT``
-------------------

- **Type**: ``str``
- **Description**: Specifies the date format for log messages. Defaults to ``"%Y-%m-%d %H:%M:%S"``.

``LOG_EMAIL_NOTIFIER``
----------------------

- **Type**: ``dict``
- **Description**: Configures the email notifier for sending log-related alerts.

    - ``ENABLE``:
      - **Type**: ``bool``
      - **Description**: Enables or disables the email notifier. Defaults to ``False``.

    - ``NOTIFY_ERROR``:
      - **Type**: ``bool``
      - **Description**: Sends an email when an ``ERROR`` record is logged. Defaults to ``False``.

    - ``NOTIFY_CRITICAL``:
      - **Type**: ``bool``
      - **Description**: Sends an email when a ``CRITICAL`` record is logged. Defaults to ``False``.

    - ``LOG_FORMAT``:
      - **Type**: ``int | str``
      - **Description**: The format used for the log message in the email. Defaults to format ``1``.

    - ``USE_TEMPLATE``:
      - **Type**: ``bool``
      - **Description**: Whether the email body is rendered with the packaged HTML template. Defaults to ``True``.

``EMAIL``
---------

- **Type**: ``dict``
- **Description**: The SMTP settings used to deliver notifications. In `django_logging` these were top-level Django settings; here they are namespaced under this key. See :ref:`required_email_settings`.
- **Default**: ``{}``

``LOG_ROTATION``
----------------

- **Type**: ``dict``
- **Description**: Controls how log files are rotated. By default no rotation is applied and a plain ``FileHandler`` is used. Setting ``TYPE`` to ``"size"`` or ``"time"`` switches the underlying handler automatically for every log level, with no other code changes required.

    - ``TYPE``:
      - **Type**: ``str``
      - **Choices**: ``"none"``, ``"size"``, ``"time"``
      - **Description**:

        - ``"none"`` — No rotation. Plain ``logging.FileHandler`` (default).
        - ``"size"`` — Rotate when a file reaches ``MAX_BYTES``. Uses ``RotatingFileHandler``.
        - ``"time"`` — Rotate on a time schedule. Uses ``TimedRotatingFileHandler``.

      - **Default**: ``"none"``

    - ``MAX_BYTES``:
      - **Type**: ``int``
      - **Description**: Maximum file size in bytes before rotation. Only used when ``TYPE="size"``.
      - **Default**: ``10485760`` (10 MB)

    - ``BACKUP_COUNT``:
      - **Type**: ``int``
      - **Description**: Number of rotated backup files to keep. ``0`` means keep all rotated files indefinitely.
      - **Default**: ``5``

    - ``WHEN``:
      - **Type**: ``str``
      - **Description**: Time unit for timed rotation. Only used when ``TYPE="time"``. Accepted values: ``"s"``, ``"m"``, ``"h"``, ``"d"``, ``"midnight"``, ``"w0"``–``"w6"`` (Monday–Sunday).
      - **Default**: ``"midnight"``

    - ``INTERVAL``:
      - **Type**: ``int``
      - **Description**: Number of ``WHEN`` units between rotations. Only used when ``TYPE="time"``.
      - **Default**: ``1``

    - ``COMPRESS``:
      - **Type**: ``bool``
      - **Description**: When ``True``, each rotated file is gzip-compressed automatically (e.g., ``debug.log.1.gz``). Works with both ``"size"`` and ``"time"`` rotation types.
      - **Default**: ``False``

  **Example — size-based rotation with compression:**

  .. code-block:: python

    setup_logging(
        app,
        {
            "LOG_ROTATION": {
                "TYPE": "size",
                "MAX_BYTES": 5_000_000,
                "BACKUP_COUNT": 10,
                "COMPRESS": True,
            }
        },
    )

  **Example — daily time-based rotation:**

  .. code-block:: python

    setup_logging(
        app,
        {
            "LOG_ROTATION": {
                "TYPE": "time",
                "WHEN": "midnight",
                "INTERVAL": 1,
                "BACKUP_COUNT": 30,
            }
        },
    )

``LOG_ROTATION_OVERRIDES``
--------------------------

- **Type**: ``dict[str, dict]``
- **Description**: Per-level rotation overrides. Each key must be a valid log level (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``, ``"CRITICAL"``). The value is a partial ``LOG_ROTATION`` dict, shallow-merged over ``LOG_ROTATION`` — only the keys you supply are changed; all other keys are inherited.
- **Default**: ``{}`` (no overrides)

  **Example — ERROR and CRITICAL rotate daily while all other levels rotate by size:**

  .. code-block:: python

    setup_logging(
        app,
        {
            "LOG_ROTATION": {
                "TYPE": "size",
                "MAX_BYTES": 5_000_000,
                "BACKUP_COUNT": 5,
            },
            "LOG_ROTATION_OVERRIDES": {
                "ERROR": {"TYPE": "time", "WHEN": "midnight", "BACKUP_COUNT": 30},
                "CRITICAL": {"TYPE": "time", "WHEN": "midnight", "BACKUP_COUNT": 90},
            },
        },
    )

.. _available_format_options:

Available Format Options
------------------------

The `fastapi_logging_kit` package provides predefined log format options that you can use in configuration. Below are the available format options:

.. code-block:: python

    FORMAT_OPTIONS = {
        1: "%(levelname)s | %(asctime)s | %(module)s | %(message)s | %(context)s",
        2: "%(levelname)s | %(asctime)s | %(context)s | %(message)s | %(exc_text)s",
        3: "%(levelname)s | %(context)s | %(message)s | %(stack_info)s",
        4: "%(context)s | %(asctime)s - %(name)s - %(levelname)s - %(message)s",
        5: "%(levelname)s | %(message)s | %(context)s | [in %(pathname)s:%(lineno)d]",
        6: "%(asctime)s | %(context)s | %(levelname)s | %(message)s | %(exc_info)s",
        7: "%(levelname)s | %(asctime)s | %(context)s | in %(module)s: %(message)s",
        8: "%(levelname)s | %(context)s | %(message)s | [%(filename)s:%(lineno)d]",
        9: "[%(asctime)s] | %(levelname)s | %(context)s | in %(module)s: %(message)s",
        10: "%(asctime)s | %(processName)s | %(context)s | %(name)s | %(levelname)s | %(message)s",
        11: "%(asctime)s | %(context)s | %(threadName)s | %(name)s | %(levelname)s | %(message)s",
        12: "%(levelname)s | [%(asctime)s] | %(context)s | (%(filename)s:%(lineno)d) | %(message)s",
        13: "%(levelname)s | [%(asctime)s] | %(context)s | {%(name)s} | (%(filename)s:%(lineno)d): %(message)s",
        14: "[%(asctime)s] | %(levelname)s | %(context)s | %(name)s | %(module)s | %(message)s",
        15: "%(levelname)s | %(context)s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s",
        16: "%(levelname)s | %(context)s | %(message)s | [%(asctime)s] | %(module)s",
        17: "%(levelname)s | %(context)s | [%(asctime)s] | %(process)d | %(message)s",
        18: "%(levelname)s | %(context)s | %(asctime)s | %(name)s | %(message)s",
        19: "%(levelname)s | %(asctime)s | %(context)s | %(module)s:%(lineno)d | %(message)s",
        20: "[%(asctime)s] | %(levelname)s | %(context)s | %(thread)d | %(message)s",
    }

You can reference these formats by their corresponding **integer keys** in your logging configuration. You can also pass a custom format string instead of an integer.

.. _required_email_settings:

Required Email Settings
-----------------------

To use the email notifier, the following settings must be configured under the ``EMAIL`` configuration key:

- ``EMAIL_HOST``: The host to use for sending emails.
- ``EMAIL_PORT``: The port to use for the email server.
- ``EMAIL_HOST_USER``: The username to use for the email server.
- ``EMAIL_HOST_PASSWORD``: The password to use for the email server.
- ``EMAIL_USE_TLS``: Whether to use a TLS (secure) connection when talking to the email server.
- ``DEFAULT_FROM_EMAIL``: The default email address to use for sending emails.
- ``ADMIN_EMAIL``: The email address where log notifications will be sent. This is the recipient address used by the email notifier to deliver the logs.

Example Email Settings
----------------------

Below is an example configuration for the email settings:

.. code-block:: python

   setup_logging(
       app,
       {
           "LOG_EMAIL_NOTIFIER": {"ENABLE": True, "NOTIFY_ERROR": True},
           "EMAIL": {
               "EMAIL_HOST": "smtp.example.com",
               "EMAIL_PORT": 587,
               "EMAIL_HOST_USER": "your-email@example.com",
               "EMAIL_HOST_PASSWORD": "your-email-password",
               "EMAIL_USE_TLS": True,
               "DEFAULT_FROM_EMAIL": "your-email@example.com",
               "ADMIN_EMAIL": "admin@example.com",
           },
       },
   )

These settings ensure that the email notifier is correctly configured to send log notifications to the specified ``ADMIN_EMAIL`` address.

Keep credentials out of your source tree by supplying them through the environment instead:

.. code-block:: shell

   export FASTAPI_LOGGING_EMAIL='{"EMAIL_HOST":"smtp.example.com","EMAIL_PORT":587,"ADMIN_EMAIL":"admin@example.com"}'
