Usage
=====

Once ``fastapi_logging_kit`` is installed and ``setup_logging`` has been called, you can start using it right away. The package provides several features to customize and enhance logging in your FastAPI project. Below is a guide on how to use the various features provided by `fastapi_logging_kit`.

Basic Logging Usage
-------------------

   At its core, `fastapi_logging_kit` is built on top of Python's built-in logging module. This means you can use the standard logging module to log messages across your project. Here's a basic example of logging usage:

   .. code-block:: python

      import logging

      logger = logging.getLogger(__name__)

      logger.debug("This is a debug message")
      logger.info("This is an info message")
      logger.warning("This is a warning message")
      logger.error("This is an error message")
      logger.critical("This is a critical message")

   These logs will be handled according to the configurations set up by `fastapi_logging_kit`, using either the default settings or any custom settings you've provided.


Configuring
-----------

``setup_logging`` accepts the configuration as its second argument:

.. code-block:: python

   from fastapi import FastAPI

   from fastapi_logging_kit import setup_logging

   app = FastAPI()

   setup_logging(
       app,
       {
           "LOG_DIR": "logs",
           "LOG_FILE_LEVELS": ["INFO", "ERROR", "CRITICAL"],
           "LOG_FILE_FORMAT_TYPES": {"ERROR": "JSON"},
       },
   )

Every option can also be supplied through the environment, using the ``FASTAPI_LOGGING_`` prefix. Values are parsed as JSON, falling back to a plain string:

.. code-block:: shell

   export FASTAPI_LOGGING_LOG_DIR=/var/log/myapp
   export FASTAPI_LOGGING_LOG_FILE_LEVELS='["INFO", "ERROR"]'
   export FASTAPI_LOGGING_LOG_CONSOLE_COLORIZE=false

An explicit mapping passed to ``setup_logging`` takes priority over the environment, which in turn takes priority over the packaged defaults. This means the CLI commands pick up the same ``FASTAPI_LOGGING_LOG_DIR`` your application uses, with no extra wiring.

``setup_logging`` can also be called without an application when you only want the logging configured — for example in a worker process or a maintenance script:

.. code-block:: python

   from fastapi_logging_kit import setup_logging

   setup_logging(config={"LOG_DIR": "logs"})

.. note::

   Configuration check failures are logged as warnings; unlike Django's system checks they never abort startup. Your application still boots, falling back to the packaged defaults for the invalid options.

For a full breakdown of every option, refer to the :doc:`Settings <settings>`.

Context Manager
---------------
   You can use the ``config_setup`` context manager to temporarily apply `fastapi_logging_kit` configurations within a specific block of code.

   Example usage:

   .. code-block:: python

      import logging

      from fastapi_logging_kit.utils.context_manager import config_setup

      logger = logging.getLogger(__name__)


      def foo():
          logger.info("This log will use the configuration set in the context manager!")


      with config_setup():
          """Your logging configuration changes here"""
          foo()

      # the logging configuration will restore to what it was before,
      # in here outside of the with block

   Note: ``AUTO_INITIALIZATION_ENABLE`` must be set to ``False`` in the configuration to use the context manager. If it is ``True``, attempting to use the context manager will raise a ``ValueError``.

Log and Notify Utility
----------------------

   To send specific logs as email, use the ``log_and_notify_admin`` function. Ensure that the ``ENABLE`` option in ``LOG_EMAIL_NOTIFIER`` is set to ``True`` in your configuration:

   .. code-block:: python

      import logging

      from fastapi_logging_kit.utils.log_email_notifier.log_and_notify import log_and_notify_admin

      logger = logging.getLogger(__name__)

      log_and_notify_admin(logger, logging.INFO, "This is a log message")

   You can also include request details in the email by passing the request through ``extra``:

   .. code-block:: python

      log_and_notify_admin(
          logger,
          logging.INFO,
          "This is a log message",
          extra={"request": request},
      )

   Note: To use the email notifier, ``LOG_EMAIL_NOTIFIER["ENABLE"]`` must be set to ``True``. If it is not, calling ``log_and_notify_admin`` will raise a ``ValueError``.

   Additionally, the ``EMAIL`` settings must be configured.

    - **Note**: For more detailed configuration options, refer to the :doc:`Settings <settings>`.

Execution Tracker
-----------------

The ``execution_tracker`` decorator is used to log the performance metrics of any function. It tracks execution time and, optionally, the number of database queries for the decorated function.

Example Usage:

.. code-block:: python

    import logging

    from fastapi_logging_kit.decorators import execution_tracker

    logger = logging.getLogger(__name__)


    @execution_tracker(
        logging_level=logging.INFO,
        log_queries=True,
        query_threshold=10,
        query_exceed_warning=True,
    )
    def some_function():
        # function code
        pass

**Arguments:**

- ``logging_level`` (``int``): The logging level at which performance details will be logged. Defaults to ``logging.INFO``.

- ``log_queries`` (``bool``): Whether to include the number of database queries. Requires ``DEBUG`` to be ``True`` in your configuration. Defaults to ``False``.

- ``query_threshold`` (``int | None``): If provided, the number of database queries will be checked. If the number of queries exceeds the given threshold, a warning will be logged. Defaults to ``None``.

- ``query_exceed_warning`` (``bool``): Whether to log a ``WARNING`` message if the number of queries exceeds the threshold. Defaults to ``False``.

**Example Log Output:**

.. code-block:: text

    INFO | 'datetime' | execution_tracking | Performance Metrics for Function: 'some_function'
      Module: some_module
      File: /path/to/file.py, Line: 123
      Execution Time: 0.21 second(s)
      Database Queries: 15 queries (exceeds threshold of 10)

Tracking queries
^^^^^^^^^^^^^^^^

Django counted queries automatically through ``connection.queries``. FastAPI ships no ORM, so ``fastapi_logging_kit`` keeps its own per-context query log. If you use SQLAlchemy, instrument your engine once at startup:

.. code-block:: python

   from sqlalchemy import create_engine

   from fastapi_logging_kit import instrument_sqlalchemy

   engine = create_engine("postgresql://...")
   instrument_sqlalchemy(engine)

Using a different database library? Report queries yourself from your own instrumentation:

.. code-block:: python

   from fastapi_logging_kit import record_query

   record_query("SELECT * FROM users", duration=0.014)

Request Logging Middleware
--------------------------

``RequestLogMiddleware`` logs detailed information about each incoming request to the server. It is installed for you by ``setup_logging``.

To install it yourself — for example to control the middleware ordering — add it directly:

.. code-block:: python

   from fastapi import FastAPI

   from fastapi_logging_kit import RequestLogMiddleware, setup_logging

   app = FastAPI()
   setup_logging(app, add_middleware=False)
   app.add_middleware(RequestLogMiddleware)

Key Features
^^^^^^^^^^^^

1. **Request/response logging**:
   - Logs the following details at the start of each request:

     - Request method
     - Request path
     - Query parameters
     - Referrer (if available)

   - And the following details once the request has been processed:

     - User (or ``Anonymous`` if not authenticated)
     - HTTP status code
     - Content type
     - Time taken to process the request
     - Optionally the SQL queries recorded during the request

2. **Request IDs**:
   - Reuses an incoming ``X-Request-ID`` header when present, otherwise generates a UUID. The request ID is included in logs and can help with tracing specific requests.

3. **Context propagation**:
   - Binds ``request_id``, ``ip_address`` and ``user_agent`` to the context variables, so every log record emitted while handling the request carries them automatically.

4. **Streaming support**:
   - Emits ``Streaming started`` and ``Streaming finished`` records around streaming responses.

5. **Cancellation handling**:
   - Logs a warning and releases the bound context when a client disconnects mid-request.

6. **SQL query logging**:
   - Includes the queries a request issued when ``LOG_SQL_QUERIES_ENABLE`` is on. For how queries are collected, see `Tracking queries`_.

The middleware is pure ASGI, so it forwards websocket and lifespan traffic untouched.

Example log output:

.. code-block:: text

   INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST STARTED:
        method=GET
        path=/api/items
        query_params={'page': '2'}
        referrer=None
    | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}

   INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST FINISHED:
        user=Anonymous
        status_code=200
        content_type=[application/json]
        response_time=[0.02 second(s)]
    | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}

Identifying the user
^^^^^^^^^^^^^^^^^^^^

FastAPI has no built-in authentication, so the middleware reads the user from ``scope["user"]`` — the convention used by Starlette's ``AuthenticationMiddleware`` and most FastAPI auth extensions. When no user is present, requests are logged as ``Anonymous``.

Context Variables Usage
^^^^^^^^^^^^^^^^^^^^^^^

We use context variables in ``RequestLogMiddleware`` to store the following information for each request:

- **request_id**: A unique identifier for the request.
- **ip_address**: The client's IP address.
- **user_agent**: The client's user agent string.

Because the request context is bound to context variables, your own log calls inherit it without you passing anything:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)


   @app.get("/items")
   async def list_items():
       # automatically carries request_id, ip_address, user_agent
       logger.info("Listing items")
       return []

MonitorLogSizeMiddleware
------------------------

``MonitorLogSizeMiddleware`` runs the log size audit at most once a week, warning the admin by email when the log directory exceeds ``LOG_DIR_SIZE_LIMIT``. It is installed by ``setup_logging`` alongside the request middleware.

The "last run" timestamp is kept in a small in-process cache. If you run several workers and want them to share it, install your own backend:

.. code-block:: python

   from fastapi_logging_kit import set_cache

   # any object with .get(key, default) and .set(key, value, timeout)
   set_cache(my_redis_backed_cache)

- **Note**: this feature requires the ``EMAIL`` settings to be configured. See :ref:`required_email_settings`.

Context Variable Management
---------------------------

``fastapi_logging_kit`` includes a powerful ``ContextVarManager`` class, allowing you to manage context variables dynamically within your logging system. These variables are bound to the current context and automatically included in your log entries via the ``%(context)s`` placeholder in the log format.

Binding and Unbinding Context Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ContextVarManager`` provides several methods to manage context variables efficiently:

``bind(**kwargs)``
~~~~~~~~~~~~~~~~~~

The ``bind`` method allows you to bind key-value pairs as context variables that will be available during the current context.

**Example**:

.. code-block:: python

   import logging

   from fastapi_logging_kit import manager

   logger = logging.getLogger(__name__)

   # Binding context variables
   manager.bind(user_id=42, tenant="acme")

   logger.info("Processing")

**Log Output**:

.. code-block:: text

   INFO | 2026-01-05 12:00:00 | Processing | {'user_id': 42, 'tenant': 'acme'}

``unbind(key: str)``
~~~~~~~~~~~~~~~~~~~~

The ``unbind`` method removes a specific context variable by its key.

**Example**:

.. code-block:: python

   manager.unbind("tenant")

   logger.info("Still processing")

**Log Output**:

.. code-block:: text

   INFO | 2026-01-05 12:05:00 | Still processing | {'user_id': 42}

Batch Binding and Resetting Context Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``batch_bind(**kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~

The ``batch_bind`` method binds multiple context variables at once and returns tokens that can be used later to reset the variables to their previous state.

**Example**:

.. code-block:: python

   from fastapi_logging_kit import manager

   tokens = manager.batch_bind(request_id="abc", stage="validate")
   try:
       ...
   finally:
       manager.reset(tokens)

``reset(tokens)``
~~~~~~~~~~~~~~~~~

The ``reset`` method restores context variables to their previous state using the tokens returned by ``batch_bind``.

``clear()``
~~~~~~~~~~~

The ``clear`` method clears all bound context variables at once, effectively removing all contextual data from the log entry.

**Example**:

.. code-block:: python

   manager.clear()

   logger.info("All context variables cleared")

Retrieving and Merging Context Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``get_contextvars()``
~~~~~~~~~~~~~~~~~~~~~

The ``get_contextvars`` method retrieves the current context variables available in the context. This method is useful for inspecting or debugging the context.

**Example**:

.. code-block:: python

   from fastapi_logging_kit import manager

   manager.get_contextvars()  # {'request_id': 'abc'}

``get_merged_context(bound_logger_context)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``get_merged_context`` method combines the bound logger context with the current context variables, allowing you to retrieve a single dictionary with all the context data. The bound logger context wins over the ambient one.

**Example**:

.. code-block:: python

   from fastapi_logging_kit import manager

   manager.get_merged_context({"extra": "value"})

Scoped Context Management
^^^^^^^^^^^^^^^^^^^^^^^^^

``scoped_context(**kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The cleanest option is ``scoped_context``, which binds context variables for the duration of a block and restores them afterwards — even if the block raises.

**Example**:

.. code-block:: python

   from fastapi_logging_kit import manager

   with manager.scoped_context(job_id="import-42"):
       run_import()  # every log record inside carries job_id

CLI Commands
------------

FastAPI projects have no ``manage.py``, so the commands ship as a ``fastapi-logging-kit`` console script. Every command reads the same configuration your application does, so ``FASTAPI_LOGGING_LOG_DIR`` applies here too:

.. code-block:: shell

   $ fastapi-logging-kit --help

send-logs Command
^^^^^^^^^^^^^^^^^

Zips the log directory and emails it to the given address. The command is useful for retrieving logs remotely and securely, allowing administrators to receive log files via email.

**Key Features:**

- **Zips Log Directory**: Compresses the entire log directory into a single zip archive.
- **Email Log Files**: Attaches the archive to an email and delivers it over SMTP.
- **Cleanup**: Removes the temporary archive afterwards, whether or not the send succeeded.

**Command Execution:**

.. code-block:: shell

   $ fastapi-logging-kit send-logs <email>

**Example:**

.. code-block:: shell

   $ fastapi-logging-kit send-logs ops@example.com

- **Note**: requires the ``EMAIL`` settings. See :ref:`required_email_settings`.

logs-size-audit Command
^^^^^^^^^^^^^^^^^^^^^^^

Reports the size of the log directory, broken down by category, and emails the admin when it exceeds ``LOG_DIR_SIZE_LIMIT``.

**Key Features:**

- **Log Directory Size Check**: Calculates the total size of the log directory.
- **Per-Category Breakdown**: Separates file sizes into four buckets: active log files, rotated backups, gzip-compressed files, and archived bundles.
- **Configurable Size Limit**: Compares the total size against ``LOG_DIR_SIZE_LIMIT``.
- **Email Notification**: Sends a warning email to ``ADMIN_EMAIL`` when the limit is exceeded, including the full breakdown in the email body.

**Command Execution:**

.. code-block:: shell

   $ fastapi-logging-kit logs-size-audit

**Example:**

.. code-block:: text

   Log directory size breakdown:
     active            5 file(s)      12.40 MB
     rotated          14 file(s)     201.88 MB
     archived          3 file(s)      44.10 MB
     compressed        7 file(s)      18.02 MB
     TOTAL                           276.40 MB

   Log directory size is under the limit: 276.4 MB

rotate-logs Command
^^^^^^^^^^^^^^^^^^^

Immediately rotates every active rotating handler. Useful in a deploy script, so a new process starts on fresh files while safely preserving old log content in numbered backup files.

**Key Features:**

- **Immediate rollover**: calls ``doRollover()`` on every live ``RotatingFileHandler`` or ``TimedRotatingFileHandler`` found across all active loggers.
- **Graceful skip**: plain ``FileHandler`` instances (when ``LOG_ROTATION`` ``TYPE`` is ``"none"``) cannot be rotated programmatically; they are reported as skipped rather than failing.
- **Multi-handler support**: rotates all qualifying handlers in a single pass, regardless of which logger they are attached to.

**Command Execution:**

.. code-block:: shell

   $ fastapi-logging-kit rotate-logs

**Example Output:**

.. code-block:: text

   Rotated 5 handler(s):
     /var/log/myapp/debug.log
     /var/log/myapp/info.log
     ...

archive-logs Command
^^^^^^^^^^^^^^^^^^^^

Moves rotated (non-active) log files into a timestamped ``archive/`` subdirectory, optionally compressing them. Active ``<level>.log`` files are never touched.

**Key Features:**

- **Safe archiving**: only rotated files (``debug.log.1``, ``info.log.2024-01-15``, etc.) are moved.
- **Compression**: gzip-compresses each uncompressed rotated file before archiving.
- **Bundling**: bundles the entire timestamped directory into a single ``tar.gz`` or ``zip`` file and removes the directory.
- **Dry run**: prints exactly what would happen without touching any files.

**Command Execution:**

.. code-block:: shell

   # Basic — move rotated files into archive/
   $ fastapi-logging-kit archive-logs

   # Gzip each file before moving
   $ fastapi-logging-kit archive-logs --compress

   # Bundle the archive directory into a tar.gz and remove it
   $ fastapi-logging-kit archive-logs --bundle tar.gz

   # Bundle into a zip file
   $ fastapi-logging-kit archive-logs --bundle zip

   # Compress individual files and then bundle into tar.gz
   $ fastapi-logging-kit archive-logs --compress --bundle tar.gz

   # Preview everything without touching any files
   $ fastapi-logging-kit archive-logs --dry-run

**Arguments:**

``--compress``
  Gzip each uncompressed rotated file before archiving. Files that are already ``.gz`` are moved as-is.

``--bundle <FORMAT>``
  Bundle the archive directory into a single compressed file and remove the directory. Supported formats: ``tar.gz``, ``zip``.

``--dry-run``
  Print what would happen without touching any files.

**Example Output:**

.. code-block:: text

   Archived 3 file(s) to /var/log/myapp/archive/2026-03-15_143022:
     /var/log/myapp/archive/2026-03-15_143022/debug.log.1.gz
     /var/log/myapp/archive/2026-03-15_143022/info.log.2026-03-14.gz
     /var/log/myapp/archive/2026-03-15_143022/error.log.1.gz
   Bundled archive directory into /var/log/myapp/archive/2026-03-15_143022.tar.gz (0.04 MB) and removed the source directory.

generate-pretty-json Command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finds the ``.json`` files in ``logs/json/`` and rewrites them as valid, pretty-printed JSON arrays under ``logs/json/pretty/``, preserving the original files.

**Command Execution:**

.. code-block:: shell

   $ fastapi-logging-kit generate-pretty-json

**Example:**

Running the command will process the following files:

- ``logs/json/error.json`` ➡ ``logs/json/pretty/formatted_error.json``
- ``logs/json/info.json`` ➡ ``logs/json/pretty/formatted_info.json``

generate-pretty-xml Command
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finds the ``.xml`` files in ``logs/xml/`` and wraps their contents in a single ``<logs>`` element under ``logs/xml/pretty/``, preserving the original files.

**Command Execution:**

.. code-block:: shell

   $ fastapi-logging-kit generate-pretty-xml

**Example:**

Running the command will process the following files:

- ``logs/xml/error.xml`` ➡ ``logs/xml/pretty/formatted_error.xml``
- ``logs/xml/info.xml`` ➡ ``logs/xml/pretty/formatted_info.xml``

Log Rotation
------------

``fastapi_logging_kit`` supports dynamic log file rotation through the ``LOG_ROTATION`` configuration key. By default no rotation is applied and files grow forever. Setting ``TYPE`` to ``"size"`` or ``"time"`` switches the underlying handler automatically — no other code changes are needed.

For full configuration details refer to the :doc:`Settings <settings>` documentation.

Size-based rotation example
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   setup_logging(
       app,
       {
           "LOG_ROTATION": {
               "TYPE": "size",
               "MAX_BYTES": 5_000_000,  # 5 MB
               "BACKUP_COUNT": 10,
               "COMPRESS": True,  # produces debug.log.1.gz, info.log.1.gz …
           },
       },
   )

Time-based rotation example
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   setup_logging(
       app,
       {
           "LOG_ROTATION": {
               "TYPE": "time",
               "WHEN": "midnight",
               "INTERVAL": 1,
               "BACKUP_COUNT": 30,
           },
       },
   )

Per-level rotation overrides
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``LOG_ROTATION_OVERRIDES`` to give individual log levels a different strategy. Only the keys you specify are changed; everything else inherits from ``LOG_ROTATION``.

.. code-block:: python

   setup_logging(
       app,
       {
           "LOG_ROTATION": {
               "TYPE": "time",
               "WHEN": "midnight",
               "BACKUP_COUNT": 14,
           },
           "LOG_ROTATION_OVERRIDES": {
               "DEBUG": {
                   "TYPE": "size",
                   "MAX_BYTES": 5242880,  # 5 MB
                   "BACKUP_COUNT": 3,
                   "COMPRESS": True,
               },
           },
       },
   )

.. _migrating_from_django_logging:

Migrating from django_logging
-----------------------------

``fastapi_logging_kit`` keeps the same configuration keys, formats and behaviour as `django_logging`. What changes is how the package attaches to your application:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - django_logging
     - fastapi_logging_kit
   * - Add ``"django_logging"`` to ``INSTALLED_APPS``
     - Call ``setup_logging(app)``
   * - ``DJANGO_LOGGING = {...}`` in settings
     - A mapping passed to ``setup_logging``, or ``FASTAPI_LOGGING_*`` env vars
   * - Top-level ``EMAIL_HOST``, ``ADMIN_EMAIL``, … settings
     - The ``EMAIL`` configuration key
   * - ``settings.DEBUG``
     - The ``DEBUG`` configuration key
   * - ``MIDDLEWARE`` list entries
     - Installed by ``setup_logging``, or ``app.add_middleware(...)``
   * - ``python manage.py send_logs``
     - ``fastapi-logging-kit send-logs``
   * - Django system checks abort startup
     - Check failures are logged as warnings; the app still boots
   * - ``connection.queries``
     - ``instrument_sqlalchemy(engine)`` or ``record_query(...)``
   * - ``request.user``
     - ``scope["user"]``
   * - LogiBoard superuser check
     - A replaceable predicate via ``set_permission_check``
   * - ``django.core.cache``
     - An in-process cache, replaceable via ``set_cache``

The formatters, filters, context variable manager, rotation handling and format options are unchanged.
