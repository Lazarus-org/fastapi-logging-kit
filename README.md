# FastAPI Logging Kit

Structured, extensible logging for FastAPI and ASGI applications.

![PyPI - Version](https://img.shields.io/pypi/v/fastapi-logging-kit)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi-logging-kit)
![PyPI - Downloads](https://img.shields.io/pypi/dm/fastapi-logging-kit)

![License](https://img.shields.io/github/license/lazarus-org/fastapi-logging-kit)
![Documentation](https://img.shields.io/readthedocs/fastapi-logging-kit)
![CI Workflow](https://github.com/lazarus-org/fastapi-logging-kit/actions/workflows/ci.yml/badge.svg)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=yellow)](https://github.com/pre-commit/pre-commit)
![Last Commit](https://img.shields.io/github/last-commit/lazarus-org/fastapi-logging-kit)
![Languages](https://img.shields.io/github/languages/top/lazarus-org/fastapi-logging-kit)
![Open Issues](https://img.shields.io/github/issues/lazarus-org/fastapi-logging-kit)
[![codecov](https://codecov.io/gh/lazarus-org/fastapi-logging-kit/branch/main/graph/badge.svg)](https://codecov.io/gh/lazarus-org/fastapi-logging-kit)

`fastapi-logging-kit` integrates with Python's standard `logging` package and FastAPI.
A single `setup_logging(app)` call enables safe request-completion logging and a
console logger without altering existing root handlers. Applications can supply
an explicit `FASTAPI_LOGGING` mapping to configure standard `dictConfig`
components, ASGI request logging, and extensible handlers, filters, and
formatters. No Django or settings-package dependency is required.

The JSON, XML, and FLAT structured formatters preserve original messages,
redact named sensitive fields, and impose limits on serialization depth,
items, output bytes, string lengths, and exception traces.

For migration from `django_logging`, see [Migrating from django_logging](#migrating-from-django_logging).


## Project Detail

- Language: Python >= 3.11 (supported: 3.11–3.15)
- Framework: FastAPI >= 0.100


## Documentation

The documentation is organized into the following sections:

- [Quick Start](#quick-start)
- [Usage](#usage)
- [LogiBoard Integration](#logiboard-integration)
- [Settings](#settings)
- [Log Rotation](#log-rotation)
- [CLI Commands](#cli-commands)
- [Available Format Options](#available-format-options)
- [Required Email Settings](#required-email-settings)
- [Migrating from django_logging](#migrating-from-django_logging)


## Quick Start

Getting started with `fastapi_logging_kit` is simple. Follow these steps to get up and running quickly:

1. **Install the Package**

first, Install `fastapi_logging_kit` via pip:

```shell
$ pip install fastapi-logging-kit
```

2. **Call `setup_logging`**

FastAPI has no application registry, so there is no equivalent of Django's `INSTALLED_APPS`. Instead, call `setup_logging` once, passing your application:

```python
from fastapi import FastAPI

from fastapi_logging_kit import setup_logging

app = FastAPI()
setup_logging(app)
```

That single call configures the logging, installs the request logging middleware and — if you enable it — mounts the LogiBoard router.

3. **Run Your Server**

Start your server to verify the installation:

```shell
uvicorn main:app --reload
```

The default structured integration preserves the host application's existing
root handlers and installs request logging. It does **not** automatically
create per-level log files. Configure file handlers explicitly through
`LOGGING` or `COMPONENTS` if you need them.

### Structured JSON logging

To emit JSON logs using standard Python logging configuration:

```python
from fastapi import FastAPI
from fastapi_logging_kit import setup_logging

app = FastAPI()
setup_logging(app, config={
    "LOGGING": {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "fastapi_logging_kit.formatters.JSONFormatter",
                "fmt": "%(levelname)s %(message)s %(context)s",
                "structured_logging": {
                    "INCLUDE_EXTRA": True,
                    "REDACT_FIELDS": ["customer_reference"],
                    "MAX_EVENT_BYTES": 65536,
                    "EXCEPTION_MODE": "type",
                },
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {"level": "INFO", "handlers": ["stdout"]},
    },
    "REQUEST_LOGGING": {
        "QUERY_PARAMS_ENABLED": False,
        "REQUEST_BODY_ENABLED": False,
        "ERROR_RESPONSE_BODY_ENABLED": False,
        "LOG_STREAMING_EVENTS": False,
        "LOG_SQL_QUERIES": False,
        "MAX_SQL_BYTES": 4096,
        "MAX_SQL_QUERIES": 100,
        "MAX_REQUEST_ID_LENGTH": 80,
    },
})
```

By supplying `LOGGING`, you explicitly select Python's process-wide
`dictConfig` replacement semantics. This is different from the no-config
additive setup. To preserve existing handlers, leave `LOGGING` empty and use
`COMPONENTS` for additive extensions.

Structured formatters never parse free-form `key=value` strings into fields.
Pass structured values through `extra={...}` or the request-context filter
instead. Redaction applies to named structured fields, **not** arbitrary
secrets embedded in messages or exception text. The `exception` policy can be
set to `"omit"`, `"type"`, or `"traceback"`.


## Usage

Once `fastapi_logging_kit` is installed and `setup_logging` has been called, you can start using it right away. The package provides several features to customize and enhance logging in your FastAPI project. Below is a guide on how to use the various features provided by `fastapi_logging_kit`.

### Basic Logging Usage:

At its core, `fastapi_logging_kit` is built on top of Python's built-in logging module. This means you can use the standard logging module to log messages across your project. Here's a basic example of logging usage:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")
```

These logs will be handled according to the configurations set up by `fastapi_logging_kit`, using either the default settings or any custom settings you've provided.

### Legacy configuration

Existing flat-key configuration remains supported for migration. New applications should use the structured `FASTAPI_LOGGING` contract above.

`setup_logging` accepts the legacy configuration as its second argument:

```python
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
```

Every option can also be supplied through the environment, using the `FASTAPI_LOGGING_` prefix. Values are parsed as JSON, falling back to a plain string:

```shell
export FASTAPI_LOGGING_LOG_DIR=/var/log/myapp
export FASTAPI_LOGGING_LOG_FILE_LEVELS='["INFO", "ERROR"]'
export FASTAPI_LOGGING_LOG_CONSOLE_COLORIZE=false
```

An explicit mapping passed to `setup_logging` takes priority over the environment, which in turn takes priority over the packaged defaults. This means the CLI commands pick up the same `FASTAPI_LOGGING_LOG_DIR` your application uses, with no extra wiring.

`setup_logging` can also be called without an application when you only want the logging configured — for example in a worker process or a maintenance script:

```python
from fastapi_logging_kit import setup_logging

setup_logging(config={"LOG_DIR": "logs"})
```

### Context Manager:

You can use the `config_setup` context manager to temporarily apply `fastapi_logging_kit` configurations within a specific block of code.
Example usage:

```python
import logging

from fastapi_logging_kit.utils.context_manager import config_setup

logger = logging.getLogger(__name__)


def foo():
    logger.info("This log will use the configuration set in the context manager!")


with config_setup():
    """Your logging configuration changes here"""
    foo()

# the logging configuration will restore to what it was before, in here outside of with block
```

- Note: `AUTO_INITIALIZATION_ENABLE` must be set to `False` in the configuration to use the context manager. If it is `True`, attempting to use the context manager will raise a `ValueError`.

### Log and Notify Utility:

To send specific logs as email, use the `log_and_notify_admin` function. Ensure that the `ENABLE` option in `LOG_EMAIL_NOTIFIER` is set to `True` in your configuration:

```python
import logging

from fastapi_logging_kit.utils.log_email_notifier.log_and_notify import log_and_notify_admin

logger = logging.getLogger(__name__)

log_and_notify_admin(logger, logging.INFO, "This is a log message")
```

You can also include request details in the email by passing the request through `extra`:

```python
log_and_notify_admin(
    logger,
    logging.INFO,
    "This is a log message",
    extra={"request": request},
)
```

- **Note**: To use this feature, the `EMAIL` settings must be configured. see [Required Email Settings](#required-email-settings).

### Execution Tracker Decorator:

The `execution_tracker` decorator logs the execution time and, optionally, the number of database queries for a function:

```python
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
```

**Arguments**:

- `logging_level` (`int`): the level at which the metrics are logged. Defaults to `logging.INFO`.
- `log_queries` (`bool`): whether to include the number of database queries. Requires `DEBUG` to be `True` in your configuration. Defaults to `False`.
- `query_threshold` (`int | None`): logs a warning when the query count exceeds this number. Defaults to `None`.
- `query_exceed_warning` (`bool`): whether to emit that warning. Defaults to `False`.

**Tracking queries**

Django counted queries automatically through `connection.queries`. FastAPI ships no ORM, so `fastapi_logging_kit` keeps a bounded, context-local query log. SQLAlchemy support is optional; install it with:

```shell
pip install "fastapi-logging-kit[sqlalchemy]"
```

Then instrument your engine once at startup:

```python
from sqlalchemy import create_engine

from fastapi_logging_kit import instrument_sqlalchemy

engine = create_engine("postgresql://...")
instrument_sqlalchemy(engine)
```

Enable request-level SQL diagnostics explicitly in the structured configuration:

```python
FASTAPI_LOGGING = {
    "REQUEST_LOGGING": {
        "LOG_SQL_QUERIES": True,
        "MAX_SQL_BYTES": 4096,
        "MAX_SQL_QUERIES": 100,
    },
}
```

`MAX_SQL_BYTES` bounds the retained SQL text and final diagnostic message.
`MAX_SQL_QUERIES` caps the number of statements captured per request. The
public `record_query()` API also applies a bounded default history when it is
used outside a request scope. `query_capture()` provides an explicit isolated
scope for custom instrumentation. Captured SQL is not automatically redacted:
parameterized statements are strongly preferred, and enabling SQL diagnostics
should be treated as a deliberate data-exposure decision.

Using a different database library? Report queries yourself from your own instrumentation:

```python
from fastapi_logging_kit import record_query

record_query("SELECT * FROM users", duration=0.014)
```

### Request Logging Middleware:

`RequestLogMiddleware` is installed for you by `setup_logging`. To install it yourself — for example to control the middleware ordering — add it directly:

```python
from fastapi import FastAPI

from fastapi_logging_kit import RequestLogMiddleware, setup_logging

app = FastAPI()
setup_logging(app, add_middleware=False)
app.add_middleware(RequestLogMiddleware)
```

#### Key Features

- **Request/response logging**: logs the method, path and request ID when a request starts, and the user, status code, content type and elapsed time when it finishes.
- **Request IDs**: reuses an incoming `X-Request-ID` header when present, otherwise generates a UUID.
- **Context propagation**: binds `request_id`, `ip_address` and `user_agent` to the context variables, so every log record emitted while handling the request carries them automatically.
- **Streaming support**: tracks streaming lifecycle and emits `Streaming started` and `Streaming finished` records only when `REQUEST_LOGGING.LOG_STREAMING_EVENTS` is enabled.
- **Cancellation handling**: logs a warning and releases the bound context when a client disconnects mid-request.
- **SQL query logging**: includes queries recorded during the request when `REQUEST_LOGGING.LOG_SQL_QUERIES` is enabled. SQL diagnostics are disabled by default because SQL statements may contain sensitive literal values.

The middleware is pure ASGI, so it forwards websocket and lifespan traffic untouched. Query parameters, request bodies, error-response bodies, SQL diagnostics and additional streaming lifecycle events are independently opt-in.

Example output:

```
INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST STARTED: method=GET path=/api/items request_id=a3f1...
 | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}

INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST FINISHED:
	user=Anonymous
	status_code=200
	content_type=[application/json]
	response_time=[0.02 second(s)]
 | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}
```

#### Identifying the user

FastAPI has no built-in authentication, so the middleware reads the user from `scope["user"]` — the convention used by Starlette's `AuthenticationMiddleware` and most FastAPI auth extensions. When no user is present, requests are logged as `Anonymous`.

#### Context Variables Usage

Because the request context is bound to context variables, your own log calls inherit it without you passing anything:

```python
import logging

logger = logging.getLogger(__name__)


@app.get("/items")
async def list_items():
    logger.info("Listing items")  # automatically carries request_id, ip_address, user_agent
    return []
```

### MonitorLogSizeMiddleware

`MonitorLogSizeMiddleware` runs the log size audit at most once a week, warning the admin by email when the log directory exceeds `LOG_DIR_SIZE_LIMIT`. It is installed by `setup_logging` when you use the legacy flat-key configuration path. The structured `FASTAPI_LOGGING` contract installs `RequestLogMiddleware` only; it does not enable the legacy file-size audit.

The "last run" timestamp is kept in a small in-process cache. If you run several workers and want them to share it, install your own backend:

```python
from fastapi_logging_kit import set_cache

set_cache(my_redis_backed_cache)  # any object with .get(key, default) and .set(key, value, timeout)
```

- **Note**: this feature requires the `EMAIL` settings to be configured. see [Required Email Settings](#required-email-settings).

### Context Variable Management

`fastapi_logging_kit` exposes the context manager used internally, so you can attach your own fields to every log record in a block of code.

#### Binding and Unbinding Context Variables

```python
import logging

from fastapi_logging_kit import manager

logger = logging.getLogger(__name__)

# Binding context variables
manager.bind(user_id=42, tenant="acme")
logger.info("Processing")  # context: {'user_id': 42, 'tenant': 'acme'}

# Unbinding a single variable
manager.unbind("tenant")
logger.info("Still processing")  # context: {'user_id': 42}

# Clearing everything
manager.clear()
```

#### Batch Binding and Resetting Context Variables

`batch_bind` returns tokens you can use to restore the previous values:

```python
from fastapi_logging_kit import manager

tokens = manager.batch_bind(request_id="abc", stage="validate")
try:
    ...
finally:
    manager.reset(tokens)
```

#### Retrieving and Merging Context Variables

```python
from fastapi_logging_kit import manager

manager.get_contextvars()  # {'request_id': 'abc'}
manager.get_merged_context({"extra": "value"})  # bound logger context wins over ambient
```

#### Scoped Context Management

The cleanest option is `scoped_context`, which binds for the duration of a block and restores afterwards — even if the block raises:

```python
from fastapi_logging_kit import manager

with manager.scoped_context(job_id="import-42"):
    run_import()  # every log record inside carries job_id
```


## LogiBoard Integration

LogiBoard lets you upload and browse log files in the browser.

### Setup Instructions

1. Enable it in your configuration:

```python
setup_logging(app, {"INCLUDE_LOG_iBOARD": True})
```

That registers the page at `/log-iboard/` and mounts its assets at `/fastapi-logging-kit/static`.

2. Restrict access.

FastAPI has no built-in permission framework. The default predicate reads `is_superuser` from `scope["user"]` and **denies anonymous requests**. Install authentication middleware that populates `scope["user"]` before relying on the default policy.

Prefer an application-scoped predicate so that separate FastAPI applications in the same process cannot affect one another:

```python
from fastapi import FastAPI
from fastapi_logging_kit.routers import set_permission_check

app = FastAPI()


def only_admins(request) -> bool:
    user = request.scope.get("user")
    return bool(user and user.role == "admin")


set_permission_check(only_admins, app=app)
```

Calling `set_permission_check(check)` without `app` remains available as a process-wide default for backward compatibility. Permission callbacks must be synchronous and return a real `bool`; asynchronous callbacks and non-boolean results fail closed. Users failing the check are shown an "Access Denied" page with a `403` status.

### Using LogiBoard

Visit `/log-iboard/` and upload a `.zip` of your logs. LogiBoard renders the directory tree and previews `JSON`, `XML` and `txt` files in the browser.


## Settings

For new applications, `setup_logging(app)` uses the structured defaults described in Quick Start. The flat-key settings below are retained for migration and are used only when you select the legacy configuration path by passing legacy keys or loading legacy settings. Those legacy values can also be supplied through `FASTAPI_LOGGING_`-prefixed environment variables.

#### Legacy default configuration:

```python
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
    "EXTRA_LOG_FILES": {
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
    # Rotation (all optional — defaults to no rotation)
    "LOG_ROTATION": {
        "TYPE": "none",
        "MAX_BYTES": 10485760,  # 10 MB
        "BACKUP_COUNT": 5,
        "WHEN": "midnight",
        "INTERVAL": 1,
        "COMPRESS": False,
    },
    "LOG_ROTATION_OVERRIDES": {},
}
```

#### Configuration Options:

Here's a breakdown of the available configuration options:

`AUTO_INITIALIZATION_ENABLE`
----------------------------

- **Type**: `bool`
- **Description**: Enables automatic initialization of logging configurations.
- **Default**: `True`

`INITIALIZATION_MESSAGE_ENABLE`
-------------------------------

- **Type**: `bool`
- **Description**: Enables logging of the initialization message when logging starts.
- **Default**: `True`

`INCLUDE_LOG_iBOARD`
--------------------

- **Type**: `bool`
- **Description**: Registers the LogiBoard route and static files on your application. For setting up LogiBoard, please refer to [LogiBoard Integration](#logiboard-integration).
- **Default**: `False`

`LOG_SQL_QUERIES_ENABLE`
------------------------

- **Type**: `bool`
- **Description**: Enables logging of SQL queries within `RequestLogMiddleware` logs. When enabled, queries recorded during each request will be included in the log output. See [Tracking queries](#execution-tracker-decorator) for how queries are collected.
- **Default**: `False`

`DEBUG`
-------

- **Type**: `bool`
- **Description**: Replaces Django's `settings.DEBUG`. Gates query counting in the `execution_tracker` decorator.
- **Default**: `False`

`LOG_FILE_LEVELS`
-----------------

- **Type**: `list[str]`
- **Description**: Specifies which log levels should be captured in log files.
- **Default**: `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]`

`LOG_DIR`
---------

- **Type**: `str`
- **Description**: Specifies the directory where log files will be stored.
- **Default**: `"logs"`

`LOG_DIR_SIZE_LIMIT`
--------------------

- **Type**: `int`
- **Description**: Specifies the maximum allowed size of the log directory in megabytes (MB). If the directory exceeds this limit and `MonitorLogSizeMiddleware` is enabled, a warning email will be sent to the admin weekly.
- **Default**: `1024 MB` (1 GB)

`LOG_FILE_FORMATS`
------------------

- **Type**: `dict[str, int | str]`
- **Description**: Maps each log level to its corresponding log format. The format can be an `int` referencing a predefined format or a custom `str` format.
- **Default**: Format `1` for all levels.
- **Note**: See the [Available Format Options](#available-format-options) below for available formats.

`LOG_FILE_FORMAT_TYPES`
-----------------------

- **Type**: `dict[str, str]`
- **Description**: Defines the format type (e.g., `normal`, `JSON`, `XML`, `FLAT`) for each log level. The keys are log levels, and the values are the format types.
    - **Format Types**:

      - ``normal``: Standard text log.
      - ``JSON``: Structured logs in JSON format.
      - ``XML``: Structured logs in XML format.
      - ``FLAT``: logs with Flat format.

- **Default**: Type `normal` for all levels.

`EXTRA_LOG_FILES`
-----------------

- **Type**: `dict[str, bool]`
- **Description**: Determines whether separate log files for `JSON` or `XML` formats should be created for each log level. When set to `True` for a specific level, a dedicated directory (e.g., `logs/json` or `logs/xml`) will be created with files like `info.json` or `info.xml`. If `False`, json and xml logs will be written to `.log` files.
- **Default**: `False` for all levels.

`LOG_CONSOLE_LEVEL`
-------------------

- **Type**: `str`
- **Description**: Specifies the log level for console output.
- **Default**: `"DEBUG"`

`LOG_CONSOLE_FORMAT`
--------------------

- **Type**: `int | str`
- **Description**: Specifies the format for console logs, similar to `LOG_FILE_FORMATS`.
- **Default**: format option `1`

`LOG_CONSOLE_COLORIZE`
----------------------

- **Type**: `bool`
- **Description**: Determines whether console output should be colorized.
- **Default**: `True`

`LOG_DATE_FORMAT`
-----------------

- **Type**: `str`
- **Description**: Specifies the date format for log messages.
- **Default**: `"%Y-%m-%d %H:%M:%S"`

`LOG_EMAIL_NOTIFIER`
--------------------

- **Type**: `dict`
- **Description**: Configures the email notifier for sending log-related alerts.

    - `ENABLE`:
      - **Type**: `bool`
      - **Description**: Enables or disables the email notifier.
      - **Default**: `False`

    - `NOTIFY_ERROR`:
      - **Type**: `bool`
      - **Description**: Sends an email when an `ERROR` record is logged.
      - **Default**: `False`

    - `NOTIFY_CRITICAL`:
      - **Type**: `bool`
      - **Description**: Sends an email when a `CRITICAL` record is logged.
      - **Default**: `False`

    - `LOG_FORMAT`:
      - **Type**: `int | str`
      - **Description**: The format used for the log message in the email.
      - **Default**: `1`

    - `USE_TEMPLATE`:
      - **Type**: `bool`
      - **Description**: Whether the email body is rendered with the packaged HTML template.
      - **Default**: `True`

    - `MAX_CONCURRENT`:
      - **Type**: `int` (1–64)
      - **Description**: Maximum number of simultaneous background email deliveries per worker process. Excess notifications are dropped rather than queued.
      - **Default**: `4`

    - `SMTP_TIMEOUT`:
      - **Type**: `int` (1–120 seconds)
      - **Description**: Network timeout for SMTP operations.
      - **Default**: `10`

`EMAIL`
-------

- **Type**: `dict`
- **Description**: The SMTP settings used to deliver notifications. In `django_logging` these were top-level Django settings; here they are namespaced under this key. See [Required Email Settings](#required-email-settings).
- **Default**: `{}`


## Log Rotation

Under the legacy flat-key configuration, file logging may be enabled; rotation is opt-in through `LOG_ROTATION` and can be overridden per level with `LOG_ROTATION_OVERRIDES`. The standard rotating handlers are not multi-process safe: for Gunicorn/Uvicorn workers, prefer stdout aggregation or an external rotation mechanism.

`LOG_ROTATION`
--------------

- **Type**: `dict`

    - `TYPE`:
      - **Type**: `str`
      - **Description**: One of `"none"` (a plain `FileHandler`), `"size"` (a `RotatingFileHandler`) or `"time"` (a `TimedRotatingFileHandler`).
      - **Default**: `"none"`

    - `MAX_BYTES`:
      - **Type**: `int`
      - **Description**: The size at which a file is rotated. Used when `TYPE` is `"size"`.
      - **Default**: `10485760` (10 MB)

    - `BACKUP_COUNT`:
      - **Type**: `int`
      - **Description**: How many rotated files to keep. `0` keeps all of them.
      - **Default**: `5`

    - `WHEN`:
      - **Type**: `str`
      - **Description**: The rotation interval unit. Used when `TYPE` is `"time"`. One of `s`, `m`, `h`, `d`, `midnight`, or `w0`–`w6`.
      - **Default**: `"midnight"`

    - `INTERVAL`:
      - **Type**: `int`
      - **Description**: How many `WHEN` units between rotations.
      - **Default**: `1`

    - `COMPRESS`:
      - **Type**: `bool`
      - **Description**: Whether rotated files are gzipped.
      - **Default**: `False`

`LOG_ROTATION_OVERRIDES`
------------------------

- **Type**: `dict[str, dict]`
- **Description**: Per-level rotation settings, shallow-merged over `LOG_ROTATION`, so you only specify the keys that differ.
- **Default**: `{}`

Example — rotate everything nightly, but rotate the noisy debug log by size and compress it:

```python
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
```


## CLI Commands

FastAPI projects have no `manage.py`, so the commands ship as a `fastapi-logging-kit` console script. Every command reads the same configuration your application does, so `FASTAPI_LOGGING_LOG_DIR` applies here too:

```shell
$ fastapi-logging-kit --help
```

### send-logs

Zips the log directory and emails it to the given address.

```shell
$ fastapi-logging-kit send-logs ops@example.com
```

#### Key Features:

- Compresses the entire log directory into a single zip archive.
- Attaches the archive to an email and delivers it over SMTP.
- Cleans up the temporary archive afterwards, whether or not the send succeeded.

- **Note**: requires the `EMAIL` settings. see [Required Email Settings](#required-email-settings).

### logs-size-audit

Reports the size of the log directory, broken down by category, and emails the admin when it exceeds `LOG_DIR_SIZE_LIMIT`.

```shell
$ fastapi-logging-kit logs-size-audit
```

#### Example:

```
Log directory size breakdown:
  active            5 file(s)      12.40 MB
  rotated          14 file(s)     201.88 MB
  archived          3 file(s)      44.10 MB
  compressed        7 file(s)      18.02 MB
  TOTAL                           276.40 MB

Log directory size is under the limit: 276.4 MB
```

### rotate-logs

Immediately rotates every active rotating handler. Useful in a deploy script, so a new process starts on fresh files.

```shell
$ fastapi-logging-kit rotate-logs
```

Plain `FileHandler` instances cannot be rotated programmatically; they are reported as skipped rather than failing.

### archive-logs

Moves rotated (non-active) log files into a timestamped `archive/` subdirectory, optionally compressing them.

```shell
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
```

#### Arguments:

- `--compress`: gzip each uncompressed rotated file before archiving.
- `--bundle FORMAT`: bundle the archive directory into a single `tar.gz` or `zip` and remove the directory.
- `--dry-run`: print what would happen without touching any files.

Active `<level>.log` files are never touched.

### generate-pretty-json

Finds the `.json` files in `logs/json/` and rewrites them as valid, pretty-printed JSON arrays under `logs/json/pretty/`.

```shell
$ fastapi-logging-kit generate-pretty-json
```

### generate-pretty-xml

Finds the `.xml` files in `logs/xml/` and wraps their contents in a single `<logs>` element under `logs/xml/pretty/`.

```shell
$ fastapi-logging-kit generate-pretty-xml
```


## Available Format Options

The `fastapi_logging_kit` package provides predefined log format options that you can use in configuration. You can reference these formats by their corresponding **integer keys**.

```
1.  "%(levelname)s | %(asctime)s | %(module)s | %(message)s | %(context)s"
2.  "%(levelname)s | %(asctime)s | %(context)s | %(message)s | %(exc_text)s"
3.  "%(levelname)s | %(context)s | %(message)s | %(stack_info)s"
4.  "%(context)s | %(asctime)s - %(name)s - %(levelname)s - %(message)s"
5.  "%(levelname)s | %(message)s | %(context)s | [in %(pathname)s:%(lineno)d]"
6.  "%(asctime)s | %(context)s | %(levelname)s | %(message)s | %(exc_info)s"
7.  "%(levelname)s | %(asctime)s | %(context)s | in %(module)s: %(message)s"
8.  "%(levelname)s | %(context)s | %(message)s | [%(filename)s:%(lineno)d]"
9.  "[%(asctime)s] | %(levelname)s | %(context)s | in %(module)s: %(message)s"
10. "%(asctime)s | %(processName)s | %(context)s | %(name)s | %(levelname)s | %(message)s"
11. "%(asctime)s | %(context)s | %(threadName)s | %(name)s | %(levelname)s | %(message)s"
12. "%(levelname)s | [%(asctime)s] | %(context)s | (%(filename)s:%(lineno)d) | %(message)s"
13. "%(levelname)s | [%(asctime)s] | %(context)s | {%(name)s} | (%(filename)s:%(lineno)d): %(message)s"
14. "[%(asctime)s] | %(levelname)s | %(context)s | %(name)s | %(module)s | %(message)s"
15. "%(levelname)s | %(context)s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s"
16. "%(levelname)s | %(context)s | %(message)s | [%(asctime)s] | %(module)s"
17. "%(levelname)s | %(context)s | [%(asctime)s] | %(process)d | %(message)s"
18. "%(levelname)s | %(context)s | %(asctime)s | %(name)s | %(message)s"
19. "%(levelname)s | %(asctime)s | %(context)s | %(module)s:%(lineno)d | %(message)s"
20. "[%(asctime)s] | %(levelname)s | %(context)s | %(thread)d | %(message)s"
```

You can also pass a custom format string instead of an integer.


## Required Email Settings

To use the email notifier, the following settings must be configured under the `EMAIL` key:

```python
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
```

These settings ensure that the email notifier is correctly configured to send log notifications to the specified `ADMIN_EMAIL` address.

Keep credentials out of your source tree by supplying them through the environment instead:

```shell
export FASTAPI_LOGGING_EMAIL='{"EMAIL_HOST":"smtp.example.com","EMAIL_PORT":587,"ADMIN_EMAIL":"admin@example.com"}'
```


## Migrating from django_logging

`fastapi_logging_kit` keeps the same configuration keys, formats and behaviour. What changes is how the package attaches to your application:

| django_logging | fastapi_logging_kit |
| --- | --- |
| Add `"django_logging"` to `INSTALLED_APPS` | Call `setup_logging(app)` |
| `DJANGO_LOGGING = {...}` in settings | A mapping passed to `setup_logging`, or `FASTAPI_LOGGING_*` env vars |
| Top-level `EMAIL_HOST`, `ADMIN_EMAIL`, … settings | The `EMAIL` configuration key |
| `settings.DEBUG` | The `DEBUG` configuration key |
| `MIDDLEWARE` list entries | Installed by `setup_logging`, or `app.add_middleware(...)` |
| `python manage.py send_logs` | `fastapi-logging-kit send-logs` |
| Django system checks abort startup | Check failures are logged as warnings; the app still boots |
| `connection.queries` | `instrument_sqlalchemy(engine)` or `record_query(...)` |
| `request.user` | `scope["user"]` |
| LogiBoard superuser check | A replaceable predicate via `set_permission_check` |
| `django.core.cache` | An in-process cache, replaceable via `set_cache` |

The formatters, filters, context variable manager, rotation handling and format options are unchanged.

## Explicit `FASTAPI_LOGGING` configuration

For an application-controlled logging setup, pass the `FASTAPI_LOGGING`
configuration to `setup_logging`. The package does not require a particular
settings module, environment loader, or Pydantic Settings implementation.

```python
from fastapi import FastAPI
from fastapi_logging_kit import setup_logging

FASTAPI_LOGGING = {
    "ENABLED": True,
    "COMPONENTS": {},
    "REQUEST_LOGGING": {
        "ENABLED": True,
        "LOG_REQUEST_STARTED": False,
        "LOG_REQUEST_FINISHED": True,
        "EXCLUDED_PATHS": ["/health", "/metrics"],
        "EXCLUDED_PATH_PREFIXES": ["/internal"],
        "QUERY_PARAMS_ENABLED": False,
        "MAX_REQUEST_ID_LENGTH": 80,
        "REQUEST_BODY_ENABLED": False,
        "ERROR_RESPONSE_BODY_ENABLED": False,
        "MAX_BODY_BYTES": 2048,
        "MAX_ERROR_RESPONSE_BYTES": 2048,
        "TRUSTED_PROXIES": [],
    },
}

app = FastAPI()
setup_logging(app, config=FASTAPI_LOGGING)
```

If no `LOGGING` dictionary is supplied, the structured configuration uses
an additive component activator: it does not replace the host's root logger,
log level, or third-party handlers. Installed components are owned by the
package. A custom handler can be declared and explicitly attached to root:

```python
FASTAPI_LOGGING = {
    "COMPONENTS": {
        "handlers": {"audit": {"class": "logging.NullHandler"}},
        "root_handlers": ["audit"],
    }
}
```

The `COMPONENTS` contract supports `formatters`, `filters`, `handlers`,
`loggers`, `replace`, `disable`, `root_handlers`, and `package_handlers`.
Naming conflicts require explicit replacement; invalid references raise
`ComponentConfigurationError` before handlers are activated.

Developers who explicitly provide `LOGGING` opt into the process-wide
semantics of `logging.config.dictConfig`, including replacement of the root
configuration when it is present in that dictionary. `disable_existing_loggers`
defaults to `False`. Do not use that option expecting an additive merge.

Request logging operates through pure ASGI middleware. It does not buffer
successful responses. Request IDs are checked for safe characters and size,
then returned in the configured response header. Forwarded IP addresses are
only trusted when the immediate peer belongs to `TRUSTED_PROXIES` (CIDR
networks or individual IPs); otherwise the ASGI client address is used.
When deploying behind a reverse proxy, coordinate these settings with your
ASGI server's own forwarded-header trust configuration.

Query parameters are omitted by default. Set `QUERY_PARAMS_ENABLED=True` to
log bounded, JSON-escaped query values; common credential keys are redacted,
and additional exclusions can be configured through `EXCLUDED_FIELDS` and
`EXCLUDED_FIELDS_BY_PATH`.

SQL query capture is independently opt-in through `LOG_SQL_QUERIES`. Its
output is bounded by `MAX_SQL_BYTES` and `MAX_SQL_QUERIES`. Streaming lifecycle
records are independently opt-in through `LOG_STREAMING_EVENTS`; the
middleware still propagates request context through streams when those extra
events are disabled.

JSON request-body diagnostics and JSON error-response diagnostics are also
opt-in through `REQUEST_BODY_ENABLED` and `ERROR_RESPONSE_BODY_ENABLED`.
Request-body capture is limited to POST, PUT, and PATCH requests, observes
JSON media types only, and captures only chunks that the application itself
receives. Error-response capture is restricted to
HTTP status codes 400 and above and JSON media types. Both paths enforce byte
limits (maximum configurable value: 64 KiB), recursively redact sensitive
fields, and never log raw malformed JSON, multipart, or binary bodies. Values
that exceed the configured limit are discarded and represented by a marker;
request/response messages continue to the application unchanged. Keep both
options disabled unless the diagnostic value justifies logging potentially
sensitive application data.

The original flat-key API remains available for compatibility with existing
installations. New applications should use the structured configuration shown
above. Repeating the same setup on a single FastAPI application does not
register duplicate request middleware; attempting to reconfigure it with a
different mapping raises a descriptive error. Call setup before the ASGI
application begins serving requests.

Request middleware settings are copied into each FastAPI application, but
Python's logging registry and logger/handler graph are process-wide. Separate
FastAPI applications in one process do not receive isolated logging registries.
